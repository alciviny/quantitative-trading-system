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
from co_piloto_quant.strategies.vectorized import generate_signals_vectorized

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

    # O `calculate_indicators` agora serve apenas para pré-cache ou indicadores auxiliares
    # A lógica principal da estratégia não depende mais dele diretamente aqui.
    df = calculate_indicators(df_raw)
    if df is None or df.empty:
        return None

    closes = df['close']

    # ===================== GERAÇÃO DE SINAIS (VETORIZADA) =====================
    # A lógica complexa de sinais foi movida para o "cérebro" da estratégia.
    # Este script apenas consome a função, passando os parâmetros.
    entries_2d, exits_2d = generate_signals_vectorized(
        price=closes,
        bb_dev_range=BB_DEV_RANGE,
        vol_max_range=VOL_MAX_RANGE,
        bb_exit_std_dev=BB_EXIT_STD_DEV
    )

    # O número de combinações é inferido da forma das matrizes de sinais
    n_bb = len(BB_DEV_RANGE)
    n_vol = len(VOL_MAX_RANGE)
    
    # ===================== STOP ADAPTATIVO =====================

    # O stop loss continua sendo uma configuração do backtest, não da estratégia em si.
    ret = closes.pct_change()
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
