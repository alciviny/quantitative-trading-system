import sys
from pathlib import Path
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
# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

warnings.filterwarnings('ignore')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger("ML_Builder")

# -------------------------------------------------------
# Importações do Sistema
# -------------------------------------------------------
from co_piloto_quant.data.data_fetching import fetch_data
from co_piloto_quant.universe import get_b3_tickers
from co_piloto_quant.config import PROCESSED_DIR # <- Importa o caminho correto

# --- CORREÇÃO: Usar process_data em vez de calculate_indicators ---
from co_piloto_quant.data.data_processing import process_data

# --- NOVAS IMPORTAÇÕES (Cérebro Quantitativo) ---
# Certifique-se de que os arquivos abaixo existem conforme o Passo 1
from co_piloto_quant.indicators.special.frac_diff import fractional_diff_fixed_window
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
# Se tiver half_life:
# from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params

# -------------------------------------------------------
# Configurações de ML
# -------------------------------------------------------
LOOKBACK_YEARS = "4y"
TARGET_HORIZON = 5
MIN_HISTORY = 300

OUTPUT_DIR = PROCESSED_DIR # <- Usa o caminho do config
# Cria o diretório se não existir, usando pathlib
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

        # =========================================================
        # ENGENHARIA DE FEATURES (O Cérebro da IA)
        # =========================================================
        
        # 1. Preço Fracionado (A Verdade Estacionária)
        # Importante para o modelo aprender padrões que duram anos
        df['close_frac'] = fractional_diff_fixed_window(df['close'], d=0.4, window=50)
        
        # 2. Indicadores Especiais (Regime de Mercado)
        # Hurst (Tendência vs Reversão)
        hurst_series = calculate_rolling_hurst(df['close'], window=72)
        if isinstance(hurst_series, pd.DataFrame):
            df['hurst_val'] = hurst_series.iloc[:, 0] # Pega a primeira coluna se for DF
        else:
            df['hurst_val'] = hurst_series
            
        # Entropia (Caos vs Ordem)
        entropy_series = calculate_rolling_entropy(df['close'], window=20)
        if isinstance(entropy_series, pd.DataFrame):
            df['entropy_val'] = entropy_series.iloc[:, 0]
        else:
            df['entropy_val'] = entropy_series

        # 3. Features Técnicas Clássicas (Bandas, RSI, etc.)
        # Substituímos calculate_indicators por process_data
        df_tech = process_data(df)
        
        # Junta tudo no DataFrame principal
        # Apenas colunas novas para evitar duplicidade
        cols_to_use = df_tech.columns.difference(df.columns)
        df = df.join(df_tech[cols_to_use])

        if df is None or df.empty:
            return None

        # =========================================================
        # PREPARAÇÃO FINAL
        # =========================================================

        # Targets
        df_final = create_targets(df, TARGET_HORIZON)

        # Remove linhas sem futuro (targets NaN) e sem passado (indicadores NaN)
        target_col = f'target_ret_{TARGET_HORIZON}d'
        df_final = df_final.dropna(subset=[target_col, 'close_frac', 'hurst_val'])

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
    # A criação do diretório já foi movida para o topo do script.

    success_count = 0
    total_rows = 0

    with tqdm(total=len(tickers)) as pbar:
        for ticker in tickers:
            df_asset = process_asset_history(ticker)

            if df_asset is not None and not df_asset.empty:
                safe_ticker = ticker.replace('.', '_')
                file_path = OUTPUT_DIR / f"{safe_ticker}.parquet" # <- Uso de pathlib
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
    
    metadata_path = OUTPUT_DIR / "_metadata.json" # <- Uso de pathlib
    with open(metadata_path, "w") as f:
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