import sys
import os
import json
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging
import warnings
from datetime import datetime

# -------------------------------------------------------
# Configuração de Ambiente
# -------------------------------------------------------
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_ROOT)

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ML_Builder")

# -------------------------------------------------------
# Importações do Sistema
# -------------------------------------------------------
from src.co_piloto_quant.data.data_fetching import fetch_data
from src.co_piloto_quant.analysis import calculate_indicators
from src.co_piloto_quant.universe import get_b3_tickers

# -------------------------------------------------------
# Configurações de ML
# -------------------------------------------------------
LOOKBACK_YEARS = "4y"
TARGET_HORIZON = 5
MIN_HISTORY = 300

OUTPUT_DIR = "data/ml_ready"

# -------------------------------------------------------
# Target Engineering
# -------------------------------------------------------
def create_targets(df: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """
    Cria targets contínuos e discretos para ML.
    Evita data leakage usando shift negativo.
    """
    future_close = df['close'].shift(-horizon)

    # Retorno simples
    df[f'target_ret_{horizon}d'] = (future_close - df['close']) / df['close']

    # Log-retorno (mais estável estatisticamente)
    df[f'target_logret_{horizon}d'] = np.log(future_close / df['close'])

    # Classificação direcional (movimento relevante)
    df[f'target_class_{horizon}d'] = (
        df[f'target_ret_{horizon}d'] > 0.01
    ).astype(int)

    return df

# -------------------------------------------------------
# Processamento por Ativo
# -------------------------------------------------------
def process_asset_history(ticker: str) -> pd.DataFrame | None:
    try:
        df = fetch_data(ticker, period=LOOKBACK_YEARS, interval="1d")

        if df is None or len(df) < MIN_HISTORY:
            return None

        # Normalização estrutural
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df.columns = [c.lower() for c in df.columns]

        if 'adj close' in df.columns:
            df.rename(columns={'adj close': 'close'}, inplace=True)

        # Features quantitativas
        df_feat = calculate_indicators(df)

        if df_feat is None or df_feat.empty:
            return None

        # Targets
        df_final = create_targets(df_feat, TARGET_HORIZON)

        # Remove linhas sem futuro
        target_col = f'target_ret_{TARGET_HORIZON}d'
        df_final = df_final.dropna(subset=[target_col])

        # Metadados
        df_final['ticker'] = ticker
        df_final['data_pregao'] = df_final.index

        # Mantém apenas colunas numéricas + identificadores
        numeric_cols = [
            c for c in df_final.columns
            if df_final[c].dtype.kind in ('i', 'f')
        ]

        cols_final = ['ticker', 'data_pregao'] + numeric_cols

        return df_final[cols_final]

    except Exception as e:
        logger.error(f"Erro ao processar {ticker}: {e}", exc_info=True)
        return None

# -------------------------------------------------------
# Builder Principal
# -------------------------------------------------------
def build_ml_dataset():
    print("\n🧠 INICIANDO CONSTRUÇÃO DO DATASET QUANTITATIVO")
    print(f"📆 Histórico: {LOOKBACK_YEARS}")
    print(f"🎯 Horizonte: {TARGET_HORIZON} dias\n")

    tickers = get_b3_tickers()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    success_count = 0
    total_rows = 0

    with tqdm(total=len(tickers)) as pbar:
        for ticker in tickers:
            df_asset = process_asset_history(ticker)

            if df_asset is not None and not df_asset.empty:
                safe_ticker = ticker.replace('.', '_')
                file_path = f"{OUTPUT_DIR}/{safe_ticker}.parquet"
                df_asset.to_parquet(file_path, index=False)

                total_rows += len(df_asset)
                success_count += 1

            pbar.update(1)

    # Salva metadados do experimento
    metadata = {
        "generated_at": datetime.utcnow().isoformat(),
        "lookback_years": LOOKBACK_YEARS,
        "target_horizon_days": TARGET_HORIZON,
        "assets_processed": success_count,
        "total_rows": total_rows
    }

    with open(f"{OUTPUT_DIR}/_metadata.json", "w") as f:
        json.dump(metadata, f, indent=4)

    print("\n" + "=" * 60)
    print("✅ DATASET PRONTO PARA ML QUANTITATIVO")
    print(f"📂 Pasta: {OUTPUT_DIR}/")
    print(f"📊 Ativos: {success_count}")
    print(f"🧠 Linhas totais: {total_rows}")
    print("=" * 60)

    print("\n💡 Uso futuro:")
    print(f"df = pd.read_parquet('{OUTPUT_DIR}')")
    print("X = df.drop(columns=[c for c in df.columns if c.startswith('target_')] + ['ticker','data_pregao'])")
    print("y = df['target_class_5d']")

if __name__ == "__main__":
    build_ml_dataset()
