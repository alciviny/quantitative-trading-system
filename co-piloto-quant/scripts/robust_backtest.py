"""
Robust Walk-Forward Backtest + Stress Tests + Drawdown + Kelly Sizing
Save as: scripts/robust_backtest.py

O que faz:
- Carrega dataset (data/ml_ready) e features_list.joblib
- Executa Walk-Forward (expanding window) treinando um RandomForest em cada fold
- Calcula retornos brutos e líquidos (aplica custos, slippage)
- Gera métricas por fold: expectancy, win-rate, avg win/loss, total PnL, max drawdown, approx Sharpe
- Realiza stress tests: aumento de slippage, remoção dos top trades, adição de ruído nas retornos
- Calcula Kelly fracionado sugerido por fold
- Salva relatórios CSV e gráficos em reports/wfa

Notas:
- Ajuste os parâmetros de mercado (COMMISSION_PER_TRADE, SLIPPAGE_PCT) conforme seu ativo/mercado.
- O script treina modelos RF por fold para simular o pipeline de produção (retrain regular).

"""

import os
import sys
import joblib
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils import resample

# --------------------------
# Config
# --------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('WFA')

DATA_DIR = Path('data/ml_ready')
MODEL_DIR = Path('models')
OUT_DIR = Path('reports/wfa')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Market/costs assumptions (adjust)
COMMISSION_PER_TRADE = 0.001   # 0.1% per side
SLIPPAGE_PCT = 0.001           # 0.1% per side

# Walk-forward params
N_FOLDS = 5                    # number of test folds
MIN_TRADE_COUNT = 10
RANDOM_STATE = 42

# Stress test configs
STRESS_CONFIGS = [
    {'name': 'base', 'extra_slippage': 0.0, 'remove_top_pct': 0.0, 'noise_std': 0.0},
    {'name': 'high_slippage', 'extra_slippage': 0.002, 'remove_top_pct': 0.0, 'noise_std': 0.0},
    {'name': 'remove_top10pct', 'extra_slippage': 0.0, 'remove_top_pct': 0.10, 'noise_std': 0.0},
    {'name': 'noisy_returns', 'extra_slippage': 0.0, 'remove_top_pct': 0.0, 'noise_std': 0.01},
]

# --------------------------
# Utilities
# --------------------------

def apply_execution_costs_array(raw_returns, slippage=SLIPPAGE_PCT, commission=COMMISSION_PER_TRADE, extra_slippage=0.0):
    total_slippage = 2 * (slippage + extra_slippage)
    total_comm = 2 * commission
    net = raw_returns - total_slippage - total_comm
    return net


def bootstrap_mean_ci(arr, n_iter=2000, alpha=0.05):
    if len(arr) == 0:
        return np.nan, (np.nan, np.nan)
    means = []
    for _ in range(n_iter):
        sample = resample(arr, replace=True, n_samples=len(arr))
        means.append(np.mean(sample))
    lower = np.percentile(means, 100 * alpha / 2)
    upper = np.percentile(means, 100 * (1 - alpha / 2))
    return np.mean(means), (lower, upper)


def max_drawdown(cum_returns):
    # cum_returns: series of cumulative returns (e.g. (1+ret).cumprod()-1)
    peak = np.maximum.accumulate(cum_returns)
    dd = (cum_returns - peak) / (peak + 1e-12)
    return abs(dd.min())


def kelly_fraction(win_rate, payoff_ratio):
    # payoff_ratio = avg_win / avg_loss
    if payoff_ratio == 0:
        return 0.0
    try:
        k = (win_rate - (1 - win_rate) / payoff_ratio)
        return max(k, 0.0)
    except Exception:
        return 0.0

# --------------------------
# Main WFA routine
# --------------------------

def walk_forward_analysis(df, features, target_col='target_class_5d', return_col='target_ret_5d', n_folds=N_FOLDS):
    df = df.sort_values('data_pregao').reset_index(drop=True)
    n = len(df)
    fold_size = n // (n_folds + 1)  # leaving final chunk as last test

    folds = []
    for k in range(1, n_folds + 1):
        train_end = fold_size * k
        test_start = train_end
        test_end = min(train_end + fold_size, n)
        train_df = df.iloc[:train_end]
        test_df = df.iloc[test_start:test_end]
        folds.append((train_df.reset_index(drop=True), test_df.reset_index(drop=True)))

    fold_results = []

    for i, (train_df, test_df) in enumerate(folds, start=1):
        logger.info(f"Fold {i}: train {train_df['data_pregao'].iloc[0]} -> {train_df['data_pregao'].iloc[-1]} | test {test_df['data_pregao'].iloc[0]} -> {test_df['data_pregao'].iloc[-1]}")

        X_train = train_df[features]
        y_train = train_df[target_col]
        X_test = test_df[features]
        y_test = test_df[target_col]

        # Train model fresh on each fold to emulate production retrain
        model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=RANDOM_STATE, n_jobs=-1)
        model.fit(X_train, y_train)

        probs = model.predict_proba(X_test)[:, 1]
        test_df = test_df.copy()
        test_df['prob'] = probs

        # Evaluate across a standard threshold set
        thresholds = np.arange(0.50, 0.81, 0.01)
        results = []

        for th in thresholds:
            sel = test_df[test_df['prob'] >= th].copy()
            n_trades = len(sel)
            if n_trades < MIN_TRADE_COUNT:
                results.append({'threshold': th, 'trades': n_trades})
                continue

            raw_returns = sel[return_col].values
            net_returns = apply_execution_costs_array(raw_returns)

            win_rate = (net_returns > 0).mean()
            avg_win = net_returns[net_returns > 0].mean() if (net_returns > 0).sum() > 0 else 0.0
            avg_loss = abs(net_returns[net_returns <= 0].mean()) if (net_returns <= 0).sum() > 0 else 0.0
            payoff = (avg_win / avg_loss) if avg_loss > 0 else np.inf
            expectancy = (win_rate * avg_win) - ((1 - win_rate) * avg_loss)
            total_pnl = net_returns.sum()

            # Cumulative and drawdown
            cum = (1 + pd.Series(net_returns)).cumprod() - 1
            mdd = max_drawdown(cum.values)

            mean_boot, (l_boot, u_boot) = bootstrap_mean_ci(net_returns)

            kelly = kelly_fraction(win_rate, payoff)

            results.append({
                'threshold': th,
                'trades': n_trades,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'payoff': payoff,
                'expectancy': expectancy,
                'total_pnl': total_pnl,
                'mean_net': net_returns.mean(),
                'std_net': net_returns.std(),
                'mdd': mdd,
                'mean_boot': mean_boot,
                'boot_lower': l_boot,
                'boot_upper': u_boot,
                'kelly': kelly
            })

        fold_results.append({'fold': i, 'train_end': train_df['data_pregao'].iloc[-1], 'test_start': test_df['data_pregao'].iloc[0], 'results': pd.DataFrame(results)})

    return fold_results

# --------------------------
# Stress tests wrapper
# --------------------------

def stress_test_on_fold(original_test_df, config, return_col='target_ret_5d'):
    df = original_test_df.copy()
    # add noise
    if config['noise_std'] > 0:
        noise = np.random.normal(0, config['noise_std'], size=len(df))
        df[return_col] = df[return_col] + noise
    # remove top pct
    if config['remove_top_pct'] > 0:
        cutoff = df[return_col].quantile(1 - config['remove_top_pct'])
        df = df[df[return_col] <= cutoff].copy()
    return df

# --------------------------
# Aggregate and reporting
# --------------------------

def run_all(df, features):
    # Perform baseline walk-forward
    wfa = walk_forward_analysis(df, features)

    # Save per-fold CSVs and aggregate
    all_fold_summaries = []
    for fr in wfa:
        fold = fr['fold']
        res = fr['results']
        res.to_csv(OUT_DIR / f'fold_{fold}_threshold_scan.csv', index=False)
        # pick best by total_pnl
        if 'total_pnl' in res.columns:
            valid = res.dropna(subset=['total_pnl'])
            if len(valid):
                best = valid.loc[valid['total_pnl'].idxmax()]
                summary = best.to_dict()
                summary['fold'] = fold
                all_fold_summaries.append(summary)

    summary_df = pd.DataFrame(all_fold_summaries)
    if not summary_df.empty:
        summary_df.to_csv(OUT_DIR / 'fold_best_by_pnl.csv', index=False)

    # Stress tests across folds: for each fold retrain and evaluate stress configs on test set
    stress_records = []
    for i, fr in enumerate(wfa):
        # retrain model for this fold (same as inside walk_forward_analysis)
        train_end = fr['train_end']
        test_start = fr['test_start']
        train_df = df[df['data_pregao'] <= train_end].reset_index(drop=True)
        test_df = df[df['data_pregao'] >= test_start].reset_index(drop=True)

        X_train = train_df[features]
        y_train = train_df['target_class_5d']
        X_test = test_df[features]

        model = RandomForestClassifier(n_estimators=200, max_depth=6, random_state=RANDOM_STATE, n_jobs=-1)
        model.fit(X_train, y_train)

        probs = model.predict_proba(X_test)[:, 1]
        test_df['prob'] = probs

        # pick a reasonable threshold: best by total_pnl from precomputed fr['results']
        results_df = fr['results']
        if 'total_pnl' in results_df.columns and not results_df['total_pnl'].dropna().empty:
            best_th = results_df.dropna(subset=['total_pnl']).loc[results_df['total_pnl'].idxmax(), 'threshold']
        else:
            best_th = 0.58

        for cfg in STRESS_CONFIGS:
            stressed = stress_test_on_fold(test_df[test_df['prob'] >= best_th], cfg)
            # apply extra slippage/costs
            raw = stressed['target_ret_5d'].values
            net = apply_execution_costs_array(raw, extra_slippage=cfg['extra_slippage'])
            n_trades = len(net)
            if n_trades < MIN_TRADE_COUNT:
                continue
            win = (net > 0).mean()
            mean_net = net.mean()
            total_pnl = net.sum()
            cum = (1 + pd.Series(net)).cumprod() - 1
            mdd = max_drawdown(cum.values)
            mean_boot, (l, u) = bootstrap_mean_ci(net)
            stress_records.append({
                'fold': i+1,
                'config': cfg['name'],
                'threshold': best_th,
                'n_trades': n_trades,
                'win_rate': win,
                'mean_net': mean_net,
                'total_pnl': total_pnl,
                'mdd': mdd,
                'boot_mean': mean_boot,
                'boot_lower': l,
                'boot_upper': u
            })

    stress_df = pd.DataFrame(stress_records)
    stress_df.to_csv(OUT_DIR / 'stress_test_summary.csv', index=False)

    logger.info(f"WFA and stress reports saved in {OUT_DIR}")
    return wfa, summary_df, stress_df

# --------------------------
# Entrypoint
# --------------------------

def main():
    # load data and features
    try:
        df = pd.read_parquet(DATA_DIR)
        df = df.dropna().sort_values('data_pregao')
    except Exception as e:
        logger.error(f"Erro ao carregar dados: {e}")
        return

    try:
        features = joblib.load(MODEL_DIR / 'features_list.joblib')
    except Exception as e:
        logger.error(f"Erro ao carregar features_list.joblib: {e}")
        return

    # Sanity check
    if 'target_ret_5d' not in df.columns or 'target_class_5d' not in df.columns:
        logger.error('Colunas target_ret_5d ou target_class_5d ausentes do dataset. Ajuste e rode novamente.')
        return

    wfa, summary_df, stress_df = run_all(df, features)

    # Small visualization: aggregate expectancy per fold best threshold
    agg = []
    for fr in wfa:
        fold = fr['fold']
        res = fr['results']
        if 'expectancy' in res.columns:
            best = res.loc[res['expectancy'].idxmax()] if res['expectancy'].dropna().size else None
            if best is not None:
                agg.append({'fold': fold, 'best_expectancy': best['expectancy'], 'threshold': best['threshold'], 'trades': best['trades']})

    if len(agg):
        pv = pd.DataFrame(agg)
        pv.to_csv(OUT_DIR / 'fold_best_expectancy_summary.csv', index=False)
        plt.figure(figsize=(8,4))
        plt.bar(pv['fold'], pv['best_expectancy'])
        plt.xlabel('Fold')
        plt.ylabel('Best Expectancy')
        plt.title('Best Expectancy per Fold')
        plt.tight_layout()
        plt.savefig(OUT_DIR / 'best_expectancy_per_fold.png', dpi=150)
        plt.close()

    logger.info('Finished WFA pipeline.')

if __name__ == '__main__':
    main()
