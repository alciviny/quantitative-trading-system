import numpy as np
import pandas as pd
from multiprocessing import cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.indicators.special.fractal_dimension import calculate_rolling_fdi
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.lempel_ziv import calculate_rolling_lzc


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

    # ---------- Indicadores base ----------
    df["FDI_30"] = calculate_rolling_fdi(df["close"], 30)
    df["Entropy_20"] = calculate_rolling_entropy(df["close"], 20)
    df["Hurst_100"] = calculate_rolling_hurst(df["close"], 100)
    df["LZC_50"] = calculate_rolling_lzc(df["close"], 50)

    # ---------- Normalização ----------
    df["FDI_n"]     = 1.0 - rolling_normalize(df["FDI_30"])
    df["Entropy_n"] = 1.0 - rolling_normalize(df["Entropy_20"])
    df["LZC_n"]     = 1.0 - rolling_normalize(df["LZC_50"])
    df["Hurst_n"]   = rolling_normalize(df["Hurst_100"])

    # ---------- Regime Score ----------
    df["regime_score"] = (
        0.30 * df["FDI_n"] +
        0.25 * df["Entropy_n"] +
        0.25 * df["LZC_n"] +
        0.20 * df["Hurst_n"]
    ) * 100.0

    # ---------- Dinâmica ----------
    df["regime_delta"] = df["regime_score"].diff()
    df["regime_accel"] = df["regime_delta"].diff()

    # ---------- Estados discretos ----------
    df["regime_state"] = pd.cut(
        df["regime_score"],
        bins=[0, 20, 40, 60, 80, 100],
        labels=["toxic", "chop", "neutral", "trend", "clean_trend"]
    )

    # ---------- Transições ----------
    df["is_transition"] = (
        (df["regime_delta"].abs() > 5) &
        (df["regime_delta"].rolling(5).mean().abs() > 2)
    )

    df["transition_type"] = np.where(
        df["is_transition"] & (df["regime_delta"] > 0),
        "improving",
        np.where(
            df["is_transition"] & (df["regime_delta"] < 0),
            "deteriorating",
            None
        )
    )

    # ---------- Probabilidades de regime ----------
    probs = compute_regime_probabilities(df["regime_score"])
    df = pd.concat([df, probs], axis=1)

    # Regime mais provável
    df["regime_most_likely"] = (
        probs.idxmax(axis=1)
        .str.replace("prob_", "", regex=False)
    )

    # Confiança do regime (quão dominante ele é)
    df["regime_confidence"] = probs.max(axis=1)

    return df


# ============================================================
# ⚙️ PIPELINE POR ATIVO (PARALELO)
# ============================================================

def process_ticker(ticker: str) -> pd.DataFrame:
    try:
        df = load_price_data(ticker)

        if df is None or df.empty:
            raise ValueError("Dados indisponíveis")

        df = compute_regime_features(df)

        last = df.tail(1).copy()
        last["ticker"] = ticker
        return last

    except Exception as e:
        print(f"⚠️ {ticker}: {e}")
        return pd.DataFrame()


# ============================================================
# 🧬 BUILD MARKET DNA
# ============================================================

def build_market_dna(tickers: list[str]) -> pd.DataFrame:
    results = []
    max_workers = max(1, cpu_count() - 1)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_ticker, t): t for t in tickers}

        for future in as_completed(futures):
            df = future.result()
            if not df.empty:
                results.append(df)

    dna = pd.concat(results, ignore_index=True)
    dna.set_index("ticker", inplace=True)

    dna.to_csv("data/reports/b3_market_dna.csv")
    print("🧬 Market DNA atualizado com sucesso.")

    return dna


# ============================================================
# 🚀 EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    tickers = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "B3SA3.SA"]
    build_market_dna(tickers)
