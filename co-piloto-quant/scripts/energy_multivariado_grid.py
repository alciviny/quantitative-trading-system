
import os
import glob
import pandas as pd
import numpy as np
import itertools
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, roc_curve

# Caminhos
results_path = 'co-piloto-quant/src/co_piloto_quant/data/results/'
output_dir = 'co-piloto-quant/docs/validacao_energy/multivariado/'
os.makedirs(output_dir, exist_ok=True)

# Parâmetros do grid
quantis = [0.7, 0.8, 0.9]
horizontes = [1, 5, 10, 20]
janelas = [21, 42]
versoes = ['v0.3']  # Foco na versão mais robusta

# Detectar todos os ativos disponíveis automaticamente
result_files = glob.glob(os.path.join(results_path, 'structural_energy_*.csv'))
ativos = [os.path.basename(f).replace('structural_energy_', '').replace('.csv', '') for f in result_files]

# Funções auxiliares para sinais

def calc_momentum(close, window=10):
    return close.pct_change(window)

def calc_volatility(close, window=10):
    return close.pct_change().rolling(window).std()

def calc_volume(df, window=10):
    if 'volume' in df.columns:
        return df['volume'].rolling(window).mean()
    return pd.Series(np.nan, index=df.index)

def filtro_composto(df, energy_col, momentum_col, vol_col, quantil, momentum_thresh=0, vol_thresh=None):
    # Filtro energy
    q = df[energy_col].quantile(quantil)
    filtro_energy = (df[energy_col] >= q)
# Caminhos
    # Filtro momentum positivo
    filtro_mom = df[momentum_col] > momentum_thresh
    # Filtro volatilidade baixa (se definido)
    if vol_thresh is not None:
        filtro_vol = df[vol_col] < vol_thresh
    else:
        filtro_vol = pd.Series(True, index=df.index)
    return filtro_energy & filtro_mom & filtro_vol

def calc_metrics(df, energy_col, regime_col, ret_col, sinal):
    # Troca de regime no horizonte desejado
    regime = df[regime_col].diff().ne(0).astype(int)
    regime = regime.shift(-horizonte).fillna(0).astype(int)
    # Métricas de classificação
    try:
        auc = roc_auc_score(regime, df[energy_col].fillna(0))
    except Exception:
        auc = np.nan
    precision = precision_score(regime, sinal, zero_division=0)
    recall = recall_score(regime, sinal, zero_division=0)
    f1 = f1_score(regime, sinal, zero_division=0)
    # Alpha futuro
    alpha_top = df.loc[sinal, ret_col].mean()
    alpha_geral = df[ret_col].mean()
    return auc, precision, recall, f1, alpha_top, alpha_geral

resultados = []

for ativo, versao, quantil, horizonte, janela in itertools.product(ativos, versoes, quantis, horizontes, janelas):
    path = os.path.join(results_path, f'structural_energy_{ativo}.csv')
    if not os.path.exists(path):
        continue
    df = pd.read_csv(path)
    # Calcular sinais auxiliares
    df['momentum'] = calc_momentum(df['close'], window=janela)
    df['volatility'] = calc_volatility(df['close'], window=janela)
    # Foco em energy v0.3
    energy_col = 'energia_v3_roll' if 'energia_v3_roll' in df.columns else 'energia_v3'
    # Filtros compostos
    for filtro_nome, filtro_args in [
        ("energy", {}),
        ("energy+momentum", {"momentum_thresh": 0}),
        ("energy+momentum+vol_baixa", {"momentum_thresh": 0, "vol_thresh": df['volatility'].quantile(0.5)})
    ]:
        sinal = filtro_composto(df, energy_col, 'momentum', 'volatility', quantil, **filtro_args)
        if energy_col not in df.columns or 'ret_futuro_10' not in df.columns or 'regime_rolling' not in df.columns:
            continue
        auc, precision, recall, f1, alpha_top, alpha_geral = calc_metrics(df, energy_col, 'regime_rolling', 'ret_futuro_10', sinal)
        resultados.append({
            'ativo': ativo,
            'versao': versao,
            'quantil': quantil,
            'horizonte': horizonte,
            'janela': janela,
            'filtro': filtro_nome,
            'auc': auc,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'alpha_top': alpha_top,
            'alpha_geral': alpha_geral
        })

# Salvar resultados
pd.DataFrame(resultados).to_csv(os.path.join(output_dir, 'metricas_multivariado.csv'), index=False)
print('Grid multivariado finalizado! Resultados em metricas_multivariado.csv')
