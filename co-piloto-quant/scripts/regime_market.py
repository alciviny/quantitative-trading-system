import numpy as np
import pandas as pd
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import sys
from tqdm import tqdm

# --- Adicionando o path do projeto para garantir que as importações funcionem ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- Novas Importações ---
from src.co_piloto_quant.data.data_manager import data_manager
from src.co_piloto_quant.universe import get_b3_tickers

# --- Indicadores (mantidos) ---
from src.co_piloto_quant.indicators.special.fractal_dimension import calculate_rolling_fdi
from src.co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from src.co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from src.co_piloto_quant.indicators.special.lempel_ziv import calculate_rolling_lzc


# ============================================================
# 🔧 NORMALIZAÇÃO ROBUSTA (rolling percentile)
# ============================================================

def rolling_normalize(series: pd.Series, window: int = 252) -> pd.Series:
    def _norm(x):
        xmin, xmax = np.min(x), np.max(x)
        if xmax == xmin:
            return 0.5
        return (x.iloc[-1] - xmin) / (xmax - xmin + 1e-9)

    return series.rolling(window, min_periods=window).apply(_norm, raw=False)


# ============================================================
# 🧠 PROBABILIDADE DE REGIME (Gaussian Softmax)
# ============================================================

def compute_regime_probabilities(
    score: pd.Series,
    sigma: float = 10.0
) -> pd.DataFrame:
    regime_centers = {
        "toxic": 10,
        "chop": 30,
        "neutral": 50,
        "trend": 70,
        "clean_trend": 90,
    }

    probs = {}
    for name, center in regime_centers.items():
        probs[f"prob_{name}"] = np.exp(
            -((score - center) ** 2) / (2 * sigma ** 2)
        )

    probs_df = pd.DataFrame(probs, index=score.index)
    probs_df = probs_df.div(probs_df.sum(axis=1), axis=0)

    return probs_df


# ============================================================
# 🧠 REGIME ENGINE
# ============================================================

def compute_regime_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula indicadores, score contínuo, transições
    e probabilidades de regime.
    """
    df["FDI_30"] = calculate_rolling_fdi(df["close"], 30)
    df["Entropy_20"] = calculate_rolling_entropy(df["close"], 20)
    df["Hurst_100"] = calculate_rolling_hurst(df["close"], 100)
    df["LZC_50"] = calculate_rolling_lzc(df["close"], 50)

    df["FDI_n"]     = 1.0 - rolling_normalize(df["FDI_30"])
    df["Entropy_n"] = 1.0 - rolling_normalize(df["Entropy_20"])
    df["LZC_n"]     = 1.0 - rolling_normalize(df["LZC_50"])
    df["Hurst_n"]   = rolling_normalize(df["Hurst_100"])

    df["regime_score"] = (
        0.30 * df["FDI_n"] +
        0.25 * df["Entropy_n"] +
        0.25 * df["LZC_n"] +
        0.20 * df["Hurst_n"]
    ).fillna(0) * 100.0

    df["regime_delta"] = df["regime_score"].diff()
    df["regime_accel"] = df["regime_delta"].diff()

    df["regime_state"] = pd.cut(
        df["regime_score"],
        bins=[0, 20, 40, 60, 80, 101],
        labels=["toxic", "chop", "neutral", "trend", "clean_trend"],
        right=True
    )

    df["is_transition"] = (df["regime_delta"].abs() > 5) & (df["regime_delta"].rolling(5).mean().abs() > 2)
    df["transition_type"] = np.where(
        df["is_transition"] & (df["regime_delta"] > 0), "improving",
        np.where(df["is_transition"] & (df["regime_delta"] < 0), "deteriorating", "stable")
    )

    probs = compute_regime_probabilities(df["regime_score"])
    df = pd.concat([df, probs], axis=1)

    df["regime_most_likely"] = probs.idxmax(axis=1).str.replace("prob_", "", regex=False)
    df["regime_confidence"] = probs.max(axis=1)

    return df


# ============================================================
# ⚙️ PIPELINE POR ATIVO (PARALELO)
# ============================================================

def process_ticker(ticker: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Worker para o processamento em paralelo. Agora recebe um DataFrame.
    """
    try:
        if df is None or df.empty or len(df) < 252:
            raise ValueError("Dados insuficientes para análise de regime (mínimo 252 períodos).")

        df_processed = compute_regime_features(df.copy())
        last = df_processed.tail(1).copy()
        last["ticker"] = ticker
        return last

    except Exception:
        # Silencioso na falha para não poluir o log, mas poderia logar
        return pd.DataFrame()


# ============================================================
# 🧬 BUILD REGIME REPORT (Nome alterado para clareza)
# ============================================================

def build_regime_report(tickers: list[str]) -> pd.DataFrame:
    """
    Orquestra a análise de regime, agora usando o DataManager.
    """
    print(f"Buscando dados para {len(tickers)} ativos via DataManager...")
    all_data = data_manager.get_data_batch(tickers, force_update=False)
    
    valid_data = {t: df for t, df in all_data.items() if df is not None and not df.empty}
    print(f"Dados válidos para {len(valid_data)} ativos. Iniciando análise de regime em paralelo...")

    results = []
    max_workers = max(1, cpu_count() - 1)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_ticker, ticker, df): ticker for ticker, df in valid_data.items()}

        for future in tqdm(as_completed(futures), total=len(valid_data), desc="Analisando Regimes"):
            df_result = future.result()
            if not df_result.empty:
                results.append(df_result)

    if not results:
        print("❌ Nenhum dado de regime foi processado.")
        return pd.DataFrame()

    report_df = pd.concat(results, ignore_index=True)
    report_df.set_index("ticker", inplace=True)
    
    os.makedirs('src/co_piloto_quant/data/reports', exist_ok=True)
    report_path = "src/co_piloto_quant/data/reports/market_regime_report.csv"
    report_df.to_csv(report_path)
    
    print(f"\n✅ Relatório de regime de mercado salvo em: {report_path}")

    print("\n--- Resumo do Regime de Mercado ---")
    cols_to_show = ['close', 'regime_score', 'regime_state', 'regime_most_likely', 'regime_confidence', 'transition_type']
    existing_cols = [c for c in cols_to_show if c in report_df.columns]
    
    with pd.option_context('display.max_rows', 20, 'display.width', 120):
        print(report_df[existing_cols].sort_values(by='regime_score', ascending=False))

    return report_df


# ============================================================
# 🚀 EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    print("Iniciando análise de regime de mercado...")
    b3_tickers = get_b3_tickers()
    if not b3_tickers:
        print("Nenhum ticker encontrado. Verifique a função get_b3_tickers.")
    else:
        build_regime_report(b3_tickers)
