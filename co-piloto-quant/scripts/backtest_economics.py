import sys
import os
import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt
from sklearn.utils import resample

# =========================
# Configuração
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Economics")

DATA_DIR = 'data/ml_ready'
MODEL_DIR = 'models'
OUT_DIR = 'reports'
os.makedirs(OUT_DIR, exist_ok=True)

# Execução: custos (ajuste para seu mercado)
COMMISSION_PER_TRADE = 0.001   # 0.1% por trade (both sides counted separately below)
SLIPPAGE_PCT = 0.001          # 0.1% slippage per side

MIN_TRADES_TO_CONSIDER = 10
RANDOM_STATE = 42

def load_data_and_model():
    # 1. Carregar Dados
    try:
        df = pd.read_parquet(DATA_DIR)
        df = df.dropna().sort_values(by='data_pregao')
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return None, None, None

    # 2. Carregar Modelo e Features (tenta vários nomes)
    model = None
    possible_models = ['market_brain_gb.joblib', 'market_brain_rf.joblib', 'market_brain.joblib']
    model_path = None
    for fname in possible_models:
        p = os.path.join(MODEL_DIR, fname)
        if os.path.exists(p):
            model_path = p
            break

    if model_path is None:
        logger.error(f"Nenhum modelo encontrado em {MODEL_DIR}. Procure por {possible_models}")
        return df, None, None

    try:
        model = joblib.load(model_path)
        features = joblib.load(os.path.join(MODEL_DIR, 'features_list.joblib'))
        logger.info(f"Modelo carregado: {model_path}")
    except Exception as e:
        logger.error(f"Erro ao carregar modelo/features: {e}")
        return df, None, None
        
    return df, model, features

def calculate_expectancy(win_rate, avg_win, avg_loss):
    loss_rate = 1.0 - win_rate
    expectancy = (win_rate * avg_win) - (loss_rate * abs(avg_loss))
    return expectancy

def apply_execution_costs(raw_ret):
    """
    Aplica slippage e comissões a um retorno bruto (ex: 0.02 = 2%).
    Assumimos slippage + commission em entrada e saída.
    """
    net = raw_ret - 2*SLIPPAGE_PCT - 2*COMMISSION_PER_TRADE
    return net

def bootstrap_ci(trades_returns, n_iter=2000, alpha=0.05):
    if len(trades_returns) == 0:
        return np.nan, (np.nan, np.nan)
    means = []
    for _ in range(n_iter):
        sample = resample(trades_returns, replace=True, n_samples=len(trades_returns), random_state=None)
        means.append(np.mean(sample))
    lower = np.percentile(means, 100*alpha/2)
    upper = np.percentile(means, 100*(1-alpha/2))
    return np.mean(means), (lower, upper)

def analyze_economics():
    df, model, features = load_data_and_model()
    if df is None:
        return
    if model is None:
        logger.error("Modelo não disponível. Rode o treino primeiro.")
        return

    # Split temporal
    split_point = int(len(df) * 0.80)
    test_df = df.iloc[split_point:].copy()
    X_test = test_df[features]
    probs = model.predict_proba(X_test)[:, 1]
    test_df = test_df.reset_index(drop=True)
    test_df['probabilidade'] = probs

    thresholds = np.arange(0.45, 0.86, 0.01)  # busca mais granular
    rows = []
    stats_for_plot = []

    for threshold in thresholds:
        selected = test_df[test_df['probabilidade'] >= threshold].copy()
        n_trades = len(selected)
        if n_trades < MIN_TRADES_TO_CONSIDER:
            rows.append({
                'threshold': threshold,
                'trades': n_trades,
                'win_rate': np.nan,
                'avg_win': np.nan,
                'avg_loss': np.nan,
                'payoff': np.nan,
                'expectancy': np.nan,
                'net_mean_return': np.nan
            })
            continue

        # Retornos brutos
        raw_returns = selected['target_ret_5d'].values  # assumir percentual, ex: 0.03 = 3%
        # aplicar custos por trade
        net_returns = np.array([apply_execution_costs(r) for r in raw_returns])

        winners = net_returns[net_returns > 0]
        losers = net_returns[net_returns <= 0]

        win_rate = (net_returns > 0).mean()
        avg_win = winners.mean() if len(winners) > 0 else 0.0
        avg_loss = abs(losers.mean()) if len(losers) > 0 else 0.0
        payoff = (avg_win / avg_loss) if avg_loss > 0 else np.inf
        expectancy = calculate_expectancy(win_rate, avg_win, avg_loss)
        net_mean_return = net_returns.mean()

        # bootstrap CI para o retorno médio por trade
        mean_boot, (l_boot, u_boot) = bootstrap_ci(net_returns, n_iter=2000, alpha=0.05)

        rows.append({
            'threshold': threshold,
            'trades': n_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'payoff': payoff,
            'expectancy': expectancy,
            'net_mean_return': net_mean_return,
            'mean_boot': mean_boot,
            'boot_lower': l_boot,
            'boot_upper': u_boot
        })
        stats_for_plot.append((threshold, n_trades, net_mean_return))

    report = pd.DataFrame(rows).set_index('threshold')
    report.to_csv(os.path.join(OUT_DIR, 'economics_threshold_scan.csv'))
    print("\n" + "="*110)
    print("💰 ANÁLISE ECONÔMICA DO SISTEMA (PAYOFF & EXPECTATIVA) — RESULTADO AGREGADO")
    print("="*110)
    display_cols = ['trades', 'win_rate', 'avg_win', 'avg_loss', 'payoff', 'expectancy', 'net_mean_return']
    print(report[display_cols].dropna().round({
        'win_rate': 3, 'avg_win': 3, 'avg_loss': 3, 'payoff': 2, 'expectancy': 4, 'net_mean_return': 4
    }).to_string())

    # Seleciona o melhor threshold por EXPECTANCY e por NET PNL (mean return * trades)
    valid = report.dropna()
    if len(valid) == 0:
        logger.warning("Nenhuma configuração com trades suficientes.")
        return

    # maximizar expectancy per trade
    best_by_expectancy = valid['expectancy'].idxmax()
    best_by_expectancy_row = valid.loc[best_by_expectancy].to_dict()

    # maximizar total net pnl = mean_return * trades
    valid['total_net_pnl'] = valid['net_mean_return'] * valid['trades']
    best_by_total = valid['total_net_pnl'].idxmax()
    best_by_total_row = valid.loc[best_by_total].to_dict()

    print("\n🏆 MELHOR POR EXPECTANCY:")
    print(best_by_expectancy_row)
    print("\n🏆 MELHOR POR PNL TOTAL:")
    print(best_by_total_row)

    # Plots
    # 1) Expectancy vs Threshold (com ponto melhor)
    plt.figure(figsize=(10, 5))
    plt.plot(valid.index, valid['expectancy'], marker='o')
    plt.axvline(best_by_expectancy, color='red', linestyle='--', label=f'Best expectancy {best_by_expectancy:.2f}')
    plt.title('Expectancy por trade vs Threshold')
    plt.xlabel('Threshold')
    plt.ylabel('Expectancy (net ret per trade)')
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, 'expectancy_vs_threshold.png'), dpi=150)
    plt.close()

    # 2) Cumulative PnL usando melhor threshold by total_pnl
    best_th = float(best_by_total)
    selected_best = test_df[test_df['probabilidade'] >= best_th].copy()
    if len(selected_best) > 0:
        selected_best['net_ret'] = selected_best['target_ret_5d'].apply(apply_execution_costs)
        selected_best = selected_best.sort_values('data_pregao').reset_index(drop=True)
        selected_best['cumulative_pnl'] = (1 + selected_best['net_ret']).cumprod() - 1

        plt.figure(figsize=(10, 5))
        plt.plot(selected_best['data_pregao'], selected_best['cumulative_pnl'])
        plt.title(f'Cumulative PnL (best threshold {best_th:.2f})')
        plt.xlabel('Date')
        plt.ylabel('Cumulative Return')
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(os.path.join(OUT_DIR, 'cumulative_pnl_best_threshold.png'), dpi=150)
        plt.close()

        # imprime resumo estatístico do melhor conjunto
        net_returns = selected_best['net_ret'].values
        mean_ret = net_returns.mean()
        std_ret = net_returns.std()
        sharpe_approx = (mean_ret / std_ret) * np.sqrt(252/5) if std_ret > 0 else np.nan  # aprox, 5-day horizon
        print("\nResumo do melhor threshold (por PnL total):")
        print(f"Threshold: {best_th:.2f}")
        print(f"Trades: {len(selected_best)}")
        print(f"Avg Net Return per trade: {mean_ret:.2%}")
        print(f"Std: {std_ret:.2%}")
        print(f"Approx Sharpe (ann, usando janela 5d): {sharpe_approx:.2f}")
    else:
        print("Nenhum trade para o melhor threshold por PnL total.")

    print(f"\nRelatórios e gráficos salvos em: {OUT_DIR}")
    print("="*110)

if __name__ == "__main__":
    analyze_economics()
