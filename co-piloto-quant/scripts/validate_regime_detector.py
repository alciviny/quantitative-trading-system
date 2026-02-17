import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix, roc_auc_score
from scipy.stats import ttest_ind, mannwhitneyu, wasserstein_distance, entropy
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')
import os

# CONFIGURAÇÕES
DATA_PATH = Path(__file__).parent.parent / 'data' / 'results'
PRICE_PATH = Path(__file__).parent.parent / 'data' / 'processed'

# Definição dos períodos de stress
STRESS_PERIODS = [
    ('2020-02-15', '2020-04-15'),  # COVID Crash
    ('2022-03-01', '2022-07-01'),  # Fed Tightening
]

# Função para carregar dados
def load_regime_data(asset_name):
    # Corrige para não duplicar _SA se já estiver no nome
    if asset_name.endswith('_SA'):
        regime_file = DATA_PATH / f'{asset_name}_regimes_hmm.parquet'
    else:
        regime_file = DATA_PATH / f'{asset_name}_SA_regimes_hmm.parquet'
    df = pd.read_parquet(regime_file)
    return df
# Função para identificar regime de stress real
def get_real_stress_regime_rolling(df, window=252):
    stress = []
    for i in range(len(df)):
        if i < window:
            stress.append(0)
            continue
        sub = df.iloc[:i]
        vol_threshold = sub['realized_volatility'].quantile(0.90)
        ret_threshold = sub['returns'].quantile(0.05)
        s = int((df.iloc[i]['realized_volatility'] >= vol_threshold) or (df.iloc[i]['returns'] <= ret_threshold))
        stress.append(s)
    return pd.Series(stress, index=df.index)

# Walk-forward expanding window para evitar lookahead bias
# Para cada t, usar dados até t para prever regime em t+1
# Aqui, assume-se que a coluna 'regime' já foi gerada sem lookahead

# Métricas de antecipação de crise
def antecipacao_crise(df, stress_periods):
    results = []
    regime_stats = df.groupby('regime')['realized_volatility'].mean()
    stress_regime = regime_stats.idxmax()
    for start, end in stress_periods:
        pre_period = df.loc[df.index < start]
        prob_col = f'regime_prob_{stress_regime}'
        if prob_col in pre_period.columns:
            sinais = pre_period[pre_period[prob_col] > 0.6]
            # Filtra sinais próximos ao stress (ex: últimos 60 dias)
            sinais_validos = sinais.loc[sinais.index > pd.to_datetime(start) - pd.Timedelta(days=60)]
            if len(sinais_validos) > 0:
                ultimo_sinal = sinais_validos.index[-1]
                antecipacao = (pd.to_datetime(start) - pd.to_datetime(ultimo_sinal)).days
            else:
                antecipacao = np.nan
        else:
            antecipacao = np.nan
        results.append({'period': f'{start} to {end}', 'regime': stress_regime, 'antecipacao_dias': antecipacao})
    return results

# Precisão, recall, F1-score para regime de stress
def regime_metrics(df):
    real_stress = get_real_stress_regime_rolling(df)
    regime_wf_valid = df['regime_wf'].copy()
    regime_stats = df.loc[regime_wf_valid.notna()].groupby(regime_wf_valid[regime_wf_valid.notna()])['realized_volatility'].mean()
    if len(regime_stats) == 0:
        return np.nan, np.nan, np.nan, real_stress, np.zeros_like(real_stress), np.nan
    stress_regime = regime_stats.idxmax()
    prob_col = f'regime_prob_wf_{stress_regime}'
    if prob_col in df.columns:
        best_thr = calibrar_threshold_roc(real_stress, df[prob_col])
        pred_stress = (df[prob_col] > best_thr).astype(int)
    else:
        pred_stress = np.where(df['regime_wf'] == stress_regime, 1, 0)
    precision = precision_score(real_stress, pred_stress)
    recall = recall_score(real_stress, pred_stress)
    f1 = f1_score(real_stress, pred_stress)
    return precision, recall, f1, real_stress, pred_stress, stress_regime

# Persistência real vs prevista
def persistencia(df):
    persist_by_regime = {}
    for r in pd.Series(df['regime_wf']).dropna().unique():
        mask = df['regime_wf'] == r
        durations = mask.groupby((mask != mask.shift()).cumsum()).count()
        persist_by_regime[r] = durations.mean()
    return persist_by_regime

# Persistência por walk-forward
def persistencia_walkforward(df, n_states, window_train=756, window_test=63, features=None):
    from hmmlearn.hmm import GaussianHMM
    from sklearn.preprocessing import StandardScaler
    transmat_list = []
    for start in range(0, len(df) - window_train - window_test + 1, window_test):
        end_train = start + window_train
        end_test = end_train + window_test
        if end_test > len(df):
            break
        X_train = df[features].iloc[start:end_train]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        model = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model.fit(X_train_scaled)
        transmat_list.append(model.transmat_)
    # Persistência média por regime
    transmat_mean = np.mean(transmat_list, axis=0)
    pred_persist = 1 / (1 - np.diag(transmat_mean))
    return pred_persist

# Sharpe condicional por regime
def sharpe_por_regime(df):
    sharpes = {}
    for r in pd.Series(df['regime_wf']).dropna().unique():
        ret = df.loc[df['regime_wf'] == r, 'returns']
        if ret.std() > 0:
            sharpe = ret.mean() / ret.std() * np.sqrt(252)
        else:
            sharpe = 0
        sharpes[r] = sharpe
    return sharpes

# Matriz de confusão
def matriz_confusao(real_stress, pred_stress):
    return confusion_matrix(real_stress, pred_stress)

# Visualizações
def plot_regimes(df, asset_name):
    plt.figure(figsize=(14,6))
    plt.plot(df['close'], label='Preço')
    for r in df['regime_wf'].unique():
        plt.scatter(df.index[df['regime_wf']==r], df['close'][df['regime_wf']==r], label=f'Regime {r}', s=10)
    plt.title(f'Preço com regimes - {asset_name}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join('co-piloto-quant', 'data', 'results', f'{asset_name}_regimes_price.png'))
    plt.close()

    # Probabilidade do regime de stress
    regime_stats = df.groupby('regime_wf')['realized_volatility'].mean()
    stress_regime = regime_stats.idxmax()
    prob_col = f'regime_prob_wf_{stress_regime}'
    plt.figure(figsize=(14,4))
    if prob_col in df.columns:
        plt.plot(df[prob_col], label='Probabilidade regime stress')
    plt.title(f'Probabilidade regime stress - {asset_name}')
    plt.tight_layout()
    plt.savefig(os.path.join('co-piloto-quant', 'data', 'results', f'{asset_name}_regime_prob.png'))
    plt.close()

    # Drawdown
    dd = (df['close'] / df['close'].cummax()) - 1
    plt.figure(figsize=(14,4))
    plt.plot(dd, label='Drawdown')
    plt.scatter(df.index[df['regime_wf']==stress_regime], dd[df['regime_wf']==stress_regime], color='red', s=10, label='Regime stress')
    plt.title(f'Drawdown com regime stress - {asset_name}')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join('co-piloto-quant', 'data', 'results', f'{asset_name}_drawdown_regime.png'))
    plt.close()

    # Visualização: histogramas dos retornos por regime
    reg0 = df[df['regime_wf']==0]['returns'].dropna()
    reg1 = df[df['regime_wf']==1]['returns'].dropna()
    plt.figure(figsize=(10,5))
    plt.hist(reg0, bins=50, alpha=0.6, label='Regime 0', color='blue', density=True)
    plt.hist(reg1, bins=50, alpha=0.6, label='Regime 1', color='orange', density=True)
    plt.title('Distribuição dos retornos por regime')
    plt.xlabel('Retorno')
    plt.ylabel('Densidade')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join('co-piloto-quant', 'data', 'results', 'regime_histogram.png'))
    plt.close()
    print('\nHistograma salvo como regime_histogram.png')

# Função block bootstrap para diferença de médias
def block_bootstrap_diff_means(grupo1, grupo2, n_boot=1000, block_size=10):
    rng = np.random.default_rng(42)
    diffs = []
    n1 = len(grupo1)
    n2 = len(grupo2)
    for _ in range(n_boot):
        idx1 = np.concatenate([rng.integers(0, n1 - block_size + 1, n1 // block_size)[:, None] + np.arange(block_size) for _ in range(n1 // block_size)]).flatten()
        idx2 = np.concatenate([rng.integers(0, n2 - block_size + 1, n2 // block_size)[:, None] + np.arange(block_size) for _ in range(n2 // block_size)]).flatten()
        sample1 = grupo1[idx1[:n1]]
        sample2 = grupo2[idx2[:n2]]
        diffs.append(np.mean(sample1) - np.mean(sample2))
    return np.array(diffs)

# Teste estatístico de retorno futuro
def teste_retorno_futuro(df):
    df['ret_futuro'] = df['close'].shift(-5) / df['close'] - 1
    df = df.iloc[::5]  # Amostra não-overlapping
    regime_stats = df.groupby('regime_wf')['realized_volatility'].mean()
    stress_regime = regime_stats.idxmax()
    grupo_stress = df.loc[df['regime_wf']==stress_regime, 'ret_futuro'].dropna().values
    grupo_nonstress = df.loc[df['regime_wf']!=stress_regime, 'ret_futuro'].dropna().values
    if len(grupo_stress) > 0 and len(grupo_nonstress) > 0:
        diffs = block_bootstrap_diff_means(grupo_stress, grupo_nonstress)
        stat = np.mean(grupo_stress) - np.mean(grupo_nonstress)
        p = np.mean(np.abs(diffs) >= np.abs(stat))
    else:
        stat, p = np.nan, np.nan
    return stat, p

# Função para walk-forward regime detection
def walk_forward_regime_detection(df, features, n_states, window_train=756, window_test=63):
    from hmmlearn.hmm import GaussianHMM
    from sklearn.preprocessing import StandardScaler
    regimes_full = np.full(len(df), np.nan)
    probs_full = np.full((len(df), n_states), np.nan)
    for start in range(0, len(df) - window_train - window_test + 1, window_test):
        end_train = start + window_train
        end_test = end_train + window_test
        if end_test > len(df):
            break
        X_train = df[features].iloc[start:end_train]
        X_test = df[features].iloc[end_train:end_test]
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        model = GaussianHMM(n_components=n_states, covariance_type='diag', n_iter=1000, random_state=42)
        model.fit(X_train_scaled)
        regimes = model.predict(X_test_scaled)
        regimes_full[end_train:end_test] = regimes
        probs = model.predict_proba(X_test_scaled)
        probs_full[end_train:end_test, :] = probs
    return regimes_full, probs_full

# Métricas adicionais
def calcular_lag(df, stress_regime, stress_periods):
    lags = []
    for start, end in stress_periods:
        regime_stats = df.groupby('regime_wf')['realized_volatility'].mean()
        pre_period = df.loc[df.index < start]
        prob_col = f'regime_prob_wf_{stress_regime}'
        if prob_col in pre_period.columns:
            sinais = pre_period[pre_period[prob_col] > 0.6]
            sinais_validos = sinais.loc[sinais.index > pd.to_datetime(start) - pd.Timedelta(days=60)]
            if len(sinais_validos) > 0:
                ultimo_sinal = sinais_validos.index[-1]
                lag = (pd.to_datetime(start) - pd.to_datetime(ultimo_sinal)).days
            else:
                lag = np.nan
        else:
            lag = np.nan
        lags.append(lag)
    return lags

def calcular_falsos_alarmes(df, stress_regime, stress_periods):
    prob_col = f'regime_prob_wf_{stress_regime}'
    falsos = 0
    for start, end in stress_periods:
        pre_period = df.loc[df.index < start]
        if prob_col in pre_period.columns:
            sinais = pre_period[pre_period[prob_col] > 0.6]
            falsos += len(sinais)
    return falsos

def calcular_roc_auc(df, stress_regime):
    prob_col = f'regime_prob_wf_{stress_regime}'
    if prob_col in df.columns:
        real_stress = get_real_stress_regime_rolling(df)
        probas = df[prob_col]
        mask = (~real_stress.isna()) & (~probas.isna())
        # Só calcula se houver pelo menos um caso positivo e negativo
        y = real_stress[mask]
        scores = probas[mask]
        if y.sum() == 0 or (len(y) - y.sum()) == 0:
            return np.nan
        auc = roc_auc_score(y, scores)
        return auc
    return np.nan

# Função para calibrar threshold via Youden's J
def calibrar_threshold_roc(real_stress, probas):
    # Remove NaNs
    mask = (~real_stress.isna()) & (~probas.isna())
    y = real_stress[mask]
    scores = probas[mask]
    thresholds = np.linspace(0, 1, 101)
    best_j = -np.inf
    best_thr = 0.5
    for thr in thresholds:
        preds = (scores > thr).astype(int)
        tp = np.sum((preds == 1) & (y == 1))
        fn = np.sum((preds == 0) & (y == 1))
        tn = np.sum((preds == 0) & (y == 0))
        fp = np.sum((preds == 1) & (y == 0))
        sens = tp / (tp + fn) if (tp + fn) > 0 else 0
        spec = tn / (tn + fp) if (tn + fp) > 0 else 0
        j = sens + spec - 1
        if j > best_j:
            best_j = j
            best_thr = thr
    return best_thr

# Relatório final
def gerar_relatorio(asset_name, antecipacao, precision, recall, f1, emp_persist, pred_persist, sharpes, conf_matrix, stat, p, lag, falsos_alarmes, roc_auc):
    results_dir = os.path.join('co-piloto-quant', 'data', 'results')
    os.makedirs(results_dir, exist_ok=True)
    with open(os.path.join(results_dir, f'{asset_name}_regime_validation_report.txt'), 'w') as f:
        f.write('==== Validação Quantitativa do Detector de Regimes (' + str(asset_name) + ') ====' + '\n')
        f.write('\n1. Antecipação de Crise:\n')
        for res in antecipacao:
            f.write(f"Período: {res['period']} | Regime: {res['regime']} | Dias de antecipação: {res['antecipacao_dias']}\n")
        f.write(f'Lag médio: {np.nanmean(lag):.2f} dias\n')
        f.write(f'Falsos alarmes: {falsos_alarmes}\n')
        f.write(f'ROC-AUC: {roc_auc:.3f}\n')
        f.write('\n2. Precisão de Regime de Stress:\n')
        f.write(f'Precision: {precision:.3f}\nRecall: {recall:.3f}\nF1-score: {f1:.3f}\n')
        f.write('\n3. Persistência Real vs Prevista (por regime):\n')
        for r, v in emp_persist.items():
            f.write(f'Regime {r}: Empírica: {v:.2f} dias\n')
        f.write(f'Prevista: {pred_persist}\n')
        f.write('\n4. Sharpe condicional por regime:\n')
        for r, s in sharpes.items():
            f.write(f'Regime {r}: Sharpe {s:.3f}\n')
        f.write(f'\n5. Matriz de confusão:\n{conf_matrix}\n')
        f.write('\n6. Teste estatístico de retorno futuro (5 dias):\n')
        f.write(f'Estatística: {stat:.3f} | p-valor: {p:.3f}\n')
        f.write('\n7. Conclusão:\n')
        antecipacao_valid = True
        for a in antecipacao:
            if a['antecipacao_dias'] is None or a['antecipacao_dias'] <= 0:
                antecipacao_valid = False
        if precision > 0.5 and recall > 0.5 and antecipacao_valid:
            f.write('O modelo é útil e antecipa crises.\n')
        else:
            f.write('O modelo NÃO é útil ou reage atrasado.\n')
        f.write('==============================================\n')

# Experimento: separabilidade entre regimes
def experimento_separabilidade(df, features, n_states):
    print('\n=== Médias das features por regime_wf ===')
    for feat in features:
        medias = df.groupby('regime_wf')[feat].mean()
        print(f'{feat}: {medias.to_dict()}')

    # Divergência Wasserstein entre retornos dos regimes
    from scipy.stats import wasserstein_distance
    reg0 = df[df['regime_wf']==0]['returns'].dropna()
    reg1 = df[df['regime_wf']==1]['returns'].dropna()
    if len(reg0) > 0 and len(reg1) > 0:
        w_dist = wasserstein_distance(reg0, reg1)
        print(f'\nWasserstein entre retornos regime 0 e 1: {w_dist:.4f}')
    else:
        print('\nWasserstein não pôde ser calculado (regimes vazios)')

    # Experimento: divergência KL entre retornos dos regimes
    from scipy.stats import entropy
    reg0 = df[df['regime_wf']==0]['returns'].dropna()
    reg1 = df[df['regime_wf']==1]['returns'].dropna()
    bins = 50
    if len(reg0) > 0 and len(reg1) > 0:
        hist0, bin_edges = np.histogram(reg0, bins=bins, density=True)
        hist1, _ = np.histogram(reg1, bins=bin_edges, density=True)
        hist0 += 1e-8
        hist1 += 1e-8
        kl_01 = entropy(hist0, hist1)
        kl_10 = entropy(hist1, hist0)
        print(f'\nKL(regime 0 || regime 1): {kl_01:.4f}')
        print(f'KL(regime 1 || regime 0): {kl_10:.4f}')
    else:
        print('\nKL não pôde ser calculado (regimes vazios)')

# MAIN
if __name__ == '__main__':
    asset_name = 'ITUB4_SA'  # Troque para o nome do arquivo desejado
    df = load_regime_data(asset_name)
    df.index = pd.to_datetime(df['date']) if 'date' in df.columns else pd.to_datetime(df.index)
    df.name = asset_name

    features = [
        'realized_volatility',
        'volatility_of_volatility',
        'rolling_trend_strength',
        'drift_t_stat',
        'efficiency_ratio',
        'hurst',
        'market_entropy',
        'returns',
    ]
    n_states = 2  # Fixar ex-ante
    regimes_full, probs_full = walk_forward_regime_detection(df, features, n_states)
    # Usar float para regime_wf, evitando Int64 com NaN
    # Isso previne valores inválidos como -9223372036854775808
    # Todas as funções devem tratar NaN explicitamente
    # Regimes não atribuídos ficam como np.nan
    df['regime_wf'] = pd.Series(regimes_full, index=df.index, dtype=float)
    for i in range(n_states):
        df[f'regime_prob_wf_{i}'] = probs_full[:, i]

    # Usar rolling para stress real
    real_stress = get_real_stress_regime_rolling(df)

    antecipacao = antecipacao_crise(df, STRESS_PERIODS)
    precision, recall, f1, _, pred_stress, stress_regime = regime_metrics(df)
    emp_persist = persistencia(df)
    pred_persist = persistencia_walkforward(df, n_states, features=features)
    sharpes = sharpe_por_regime(df)
    conf_matrix = matriz_confusao(real_stress, pred_stress)
    plot_regimes(df, asset_name)
    stat, p = teste_retorno_futuro(df)
    lag = calcular_lag(df, stress_regime, STRESS_PERIODS)
    falsos_alarmes = calcular_falsos_alarmes(df, stress_regime, STRESS_PERIODS)
    roc_auc = calcular_roc_auc(df, stress_regime)
    gerar_relatorio(asset_name, antecipacao, precision, recall, f1, emp_persist, pred_persist, sharpes, conf_matrix, stat, p, lag, falsos_alarmes, roc_auc)
    print(f'Relatório gerado: {asset_name}_regime_validation_report.txt')
    experimento_separabilidade(df, features, n_states)
