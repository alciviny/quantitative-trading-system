import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
import os
import logging
from tqdm import tqdm
import concurrent.futures
import scipy.ndimage

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.universe import get_expanded_universe
from co_piloto_quant.config import BB_PERIOD, STOCH_K_PERIOD, STOCH_K_SMOOTH
from co_piloto_quant.indicators.names import IndicatorNames

# ===================== CONFIGURAÇÃO DO SWEEP =====================

BB_DEV_RANGE = np.arange(0.20, 0.81, 0.05)
VOL_MAX_RANGE = np.arange(0.8, 2.5, 0.15)  # regime-aware ratio

BB_EXIT_STD_DEV = 2.0
INITIAL_CAPITAL = 100000
FEES_PCT = 0.0006
OUTPUT_DIR = "data/reports"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')


# ===================== CORE FUNCTION =====================

def run_matrix_optimization(ticker: str):

    df_raw = load_price_data(ticker)
    if df_raw is None or len(df_raw) < 400:
        return None

    df = calculate_indicators(df_raw, bb_entry_deviation=0.0)
    if df is None or df.empty:
        return None

    closes = df['close']

    # ===================== BB MATRIX =====================

    bb = vbt.BBANDS.run(closes, window=BB_PERIOD, alpha=BB_DEV_RANGE)
    entry_bb = closes.vbt <= bb.lower  # (rows, BB)

    # ===================== VOL REGIME AWARE =====================

    ret = closes.pct_change()

    vol_fast = ret.rolling(10).std()
    vol_slow = ret.rolling(60).std()

    regime_vol = vol_fast / (vol_slow + 1e-6)
    vol_mask = regime_vol.values[:, None] <= VOL_MAX_RANGE[None, :]

    # ===================== COMBINAÇÃO 3D =====================

    entries_3d = entry_bb.values[:, :, None] & vol_mask[:, None, :]

    # ===================== STOCH SUAVE =====================

    stoch_col = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    stoch_k = df[stoch_col].values

    stoch_weight = np.clip((30 - stoch_k) / 30, 0, 1)
    entries_3d = entries_3d * stoch_weight[:, None, None]

    final_entries = entries_3d > 0.5

    # ===================== RESHAPE =====================

    n_rows, n_bb, n_vol = final_entries.shape
    entries_2d = final_entries.reshape(n_rows, n_bb * n_vol)

    # ===================== EXIT =====================

    bb_exit = vbt.BBANDS.run(closes, window=BB_PERIOD, alpha=BB_EXIT_STD_DEV)
    exits_2d = (closes.vbt >= bb_exit.upper).vbt.tile(n_bb * n_vol)

    # ===================== STOP ADAPTATIVO =====================

    adaptive_sl_series = pd.Series(
        np.clip(
            ret.rolling(20).std().values * 4,
            0.03,
            0.10
        ),
        index=closes.index
    )
    adaptive_sl = adaptive_sl_series.vbt.tile(n_bb * n_vol)

    # ===================== PORTFOLIO =====================

    pf = vbt.Portfolio.from_signals(
        closes,
        entries_2d,
        exits_2d,
        sl_stop=adaptive_sl,
        init_cash=INITIAL_CAPITAL,
        fees=FEES_PCT,
        freq='1D'
    )

    # ===================== MÉTRICAS =====================

    sharpe = pf.sharpe_ratio()
    calmar = pf.calmar_ratio()
    max_dd = pf.max_drawdown()

    robust_score = sharpe * calmar / (1 + abs(max_dd))

    robust_matrix = robust_score.values.reshape(n_bb, n_vol)

    # ===================== CLUSTER DE ESTABILIDADE =====================

    smooth = scipy.ndimage.uniform_filter(robust_matrix, size=3)
    best_idx = np.unravel_index(np.nanargmax(smooth), smooth.shape)

    best_bb = BB_DEV_RANGE[best_idx[0]]
    best_vol = VOL_MAX_RANGE[best_idx[1]]

    best_raw_score = robust_matrix[best_idx]

    # ===================== ANÁLISE DE ROBUSTEZ =====================

    mean_score = np.nanmean(robust_matrix)
    std_score = np.nanstd(robust_matrix)

    stability = mean_score / (std_score + 1e-6)
    overfit_risk = best_raw_score / (mean_score + 1e-6)

    grad_bb, grad_vol = np.gradient(smooth)
    sensitivity = np.mean(np.abs(grad_bb)) + np.mean(np.abs(grad_vol))

    # ===================== REGIME =====================

    regime = "Híbrido"
    if best_vol < 1.1:
        regime = "Conservador (Calmaria)"
    elif best_vol > 2.0:
        regime = "Agressivo (Caos)"

    return {
        'Ticker': ticker,
        'Regime Type': regime,
        'Best BB Dev': best_bb,
        'Max Vol Ratio': best_vol,
        'Robust Score': best_raw_score,
        'Stability Score': stability,
        'Overfit Risk': overfit_risk,
        'Param Sensitivity': sensitivity,
        'Sharpe Opt': sharpe.values.reshape(n_bb, n_vol)[best_idx],
        'Calmar Opt': calmar.values.reshape(n_bb, n_vol)[best_idx],
        'Max DD': max_dd.values.reshape(n_bb, n_vol)[best_idx]
    }


def process_wrapper(ticker):
    try:
        return run_matrix_optimization(ticker)
    except Exception as e:
        logger.error(f"{ticker} erro: {e}")
        return None


# ===================== EXECUÇÃO =====================

if __name__ == "__main__":

    tickers = get_expanded_universe()
    results = []

    print(f"\n🚀 MATRIX OPTIMIZATION (ROBUST + REGIME AWARE)")
    print("=" * 80)

    with concurrent.futures.ProcessPoolExecutor(os.cpu_count()) as executor:
        futures = {executor.submit(process_wrapper, t): t for t in tickers}
        for f in tqdm(concurrent.futures.as_completed(futures), total=len(tickers)):
            if (res := f.result()):
                results.append(res)

    if results:
        df = pd.DataFrame(results)

        df_final = (
            df[df['Robust Score'] > 0]
            .sort_values(['Stability Score', 'Overfit Risk'],
                         ascending=[False, True])
        )

        print("\n🏆 TOP 10 ATIVOS MAIS ROBUSTOS")
        print(df_final.head(10).to_string(index=False))

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        out = os.path.join(OUTPUT_DIR, "matrix_regime_robust_ranking.csv")
        df_final.to_csv(out, index=False, float_format="%.4f")
        print(f"\n💾 Relatório salvo em: {out}")

    else:
        print("❌ Nenhum ativo viável.")
