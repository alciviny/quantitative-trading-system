import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging
from datetime import datetime
import warnings
from typing import Optional, Dict

# =============================================================================
# Ambiente & Logging
# =============================================================================
from pathlib import Path
warnings.filterwarnings("ignore")

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("market_snapshot")

# =============================================================================
# Importações do Projeto
# =============================================================================

try:
    from co_piloto_quant.data.data_fetching import fetch_data
    from co_piloto_quant.analysis import calculate_indicators
    from co_piloto_quant.universe import get_b3_tickers
    from co_piloto_quant.config import RESULTS_DIR
except ImportError as e:
    logger.error(f"Erro de importação: {e}")
    logger.error("Execute o script a partir da raiz do projeto.")
    sys.exit(1)

# =============================================================================
# Configurações Globais
# =============================================================================

LOOKBACK_PERIOD = "2y"
MIN_DATA_POINTS = 252
MAX_FETCH_RETRIES = 2

OUTPUT_DIR = RESULTS_DIR / "reports"

# =============================================================================
# Core Logic
# =============================================================================

def process_asset(ticker: str) -> Optional[Dict]:
    """
    Baixa dados históricos, calcula TODOS os indicadores
    e retorna um snapshot quantitativo (última observação).
    """

    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            df = fetch_data(ticker, period=LOOKBACK_PERIOD, interval="1d")

            if df is None or df.empty or len(df) < MIN_DATA_POINTS:
                return None

            # --- Higienização ---
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            df.columns = [c.lower().strip() for c in df.columns]

            if "adj close" in df.columns and "close" not in df.columns:
                df.rename(columns={"adj close": "close"}, inplace=True)

            if "close" not in df.columns:
                return None

            # --- Indicadores ---
            df_full = calculate_indicators(df)
            if df_full.empty:
                return None

            # --- Snapshot ---
            last = df_full.iloc[-1]

            snapshot = last.to_dict()
            snapshot.update({
                "ticker": ticker,
                "data_ref": df_full.index[-1].strftime("%Y-%m-%d"),
                "preco_atual": float(last.get("close", np.nan)),
                "n_obs": int(len(df_full)),
                "missing_ratio": float(last.isna().mean())
            })

            # Remove dados crus antigos
            for col in ("open", "high", "low", "volume", "dividends", "stock splits"):
                snapshot.pop(col, None)

            return snapshot

        except Exception as e:
            logger.debug(f"[{ticker}] tentativa {attempt} falhou: {e}")

    return None


def build_database() -> None:
    print("\n🚀 INICIANDO EXTRAÇÃO MASSIVA — B3")
    print("🎯 Snapshot quantitativo completo de indicadores técnicos e estatísticos\n")

    tickers = get_b3_tickers()
    print(f"📊 Ativos na fila: {len(tickers)}\n")

    rows, success, fail = [], 0, 0

    with tqdm(total=len(tickers), desc="Processando Ativos") as pbar:
        for ticker in tickers:
            result = process_asset(ticker)
            if result:
                rows.append(result)
                success += 1
            else:
                fail += 1
            pbar.update(1)

    if not rows:
        logger.error("Nenhum ativo processado com sucesso.")
        return

    # =============================================================================
    # Consolidação Final
    # =============================================================================

    df = pd.DataFrame(rows)

    priority = ["ticker", "data_ref", "preco_atual", "n_obs", "missing_ratio"]
    remaining = sorted([c for c in df.columns if c not in priority])
    df = df[priority + remaining]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_path = os.path.join(OUTPUT_DIR, "market_snapshot_full.csv")
    parquet_path = os.path.join(OUTPUT_DIR, "market_snapshot_full.parquet")

    df.to_csv(csv_path, index=False)

    try:
        df.to_parquet(parquet_path, index=False)
        parquet_ok = True
    except Exception:
        parquet_ok = False

    # =============================================================================
    # Relatório Final
    # =============================================================================

    print("\n" + "=" * 65)
    print("✅ EXTRAÇÃO CONCLUÍDA COM SUCESSO")
    print(f"📈 Ativos válidos: {success}")
    print(f"📉 Falhas / dados insuficientes: {fail}")
    print(f"🧠 Total de indicadores: {len(df.columns)}")
    print(f"📁 CSV: {csv_path}")
    if parquet_ok:
        print(f"📁 Parquet: {parquet_path}")
    print("=" * 65)

    exemplos = [c for c in df.columns if any(k in c.lower() for k in ("hurst", "half", "entropy", "lambda", "zscore"))]
    print("\n🔍 Indicadores detectados (amostra):")
    print(exemplos[:12], "...")

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    build_database()
