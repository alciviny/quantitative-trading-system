import pandas as pd
import numpy as np
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from multiprocessing import cpu_count
from pathlib import Path

# ============================================================
# 🔧 PATH
# ============================================================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from co_piloto_quant.universe import get_b3_tickers
from co_piloto_quant.indicators.vwap_annual import AnnualVWAPAnalyst

try:
    from scripts.regime_market import compute_regime_features
except ImportError:
    print("❌ Não foi possível importar compute_regime_features")
    sys.exit(1)

# ============================================================
# 📊 CAMINHO DOS DADOS
# ============================================================
ML_READY_PATH = Path(__file__).parent.parent / "src" / "co_piloto_quant" / "data" / "ml_ready"

# ============================================================
# 🔬 BUCKETS
# ============================================================
def get_vwap_bucket(z):
    if z < -2.0: return "1. Muito Barato (<-2)"
    if z < -1.0: return "2. Barato (-2 a -1)"
    if z < 0.0:  return "3. Justo Neg (-1 a 0)"
    if z < 1.0:  return "4. Justo Pos (0 a 1)"
    if z < 2.0:  return "5. Caro (1 a 2)"
    return "6. Muito Caro (>2)"

def get_vol_bucket(vol):
    if vol < 0.015: return "Low Vol"
    if vol < 0.03:  return "Mid Vol"
    return "High Vol"

# ============================================================
# ⚙️ PROCESSAMENTO POR ATIVO
# ============================================================
def process_ticker(ticker):
    try:
        # Corrige o nome do arquivo, trocando '.' por '_' (ex: de 'PETR4.SA' para 'PETR4_SA.parquet')
        file_name = f"{ticker.replace('.', '_')}.parquet"
        parquet_file = ML_READY_PATH / file_name
        
        if not parquet_file.exists():
            # Adiciona um log para sabermos quais arquivos não foram encontrados
            # print(f"Arquivo não encontrado: {parquet_file}")
            return pd.DataFrame()
        
        df = pd.read_parquet(parquet_file)
        if df is None or df.empty or len(df) < 300:
            return pd.DataFrame()

        df = df.reset_index() if df.index.name else df
        
        # --- Padronização ---
        df.columns = df.columns.str.lower()
        required_cols = {'close', 'high', 'low', 'open', 'volume'}
        if not required_cols.issubset(set(df.columns)):
            return pd.DataFrame()

        # ====================================================
        # VWAP ANUAL
        # ====================================================
        vwap_annual = AnnualVWAPAnalyst()
        df = vwap_annual.calculate(df)

        # ====================================================
        # VWAP ROLLING 252
        # ====================================================
        pv = df['close'] * df['volume']
        df['vwap_252'] = pv.rolling(252).sum() / df['volume'].rolling(252).sum()
        df['vwap_252_z'] = (
            (df['close'] - df['vwap_252']) /
            df['close'].rolling(252).std()
        )

        # ====================================================
        # REGIME DE MERCADO
        # ====================================================
        df = compute_regime_features(df)

        # ====================================================
        # VOLATILIDADE (proxy simples)
        # ====================================================
        df['ret'] = df['close'].pct_change()
        df['vol_20'] = df['ret'].rolling(20).std()
        df['Vol_Bucket'] = df['vol_20'].apply(get_vol_bucket)

        # ====================================================
        # FORWARD RETURNS
        # ====================================================
        df['fwd_ret_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['fwd_ret_20d'] = df['close'].shift(-20) / df['close'] - 1

        # ====================================================
        # LIMPEZA FINAL
        # ====================================================
        if 'date' not in df.columns:
            df = df.reset_index()
            if 'date' not in df.columns and df.index.name:
                df.index.name = 'date'
                df = df.reset_index()
        
        cols = [
            'date',
            'vwap_z_score',
            'vwap_252_z',
            'regime_state',
            'regime_score',
            'Entropy_20',
            'Vol_Bucket',
            'fwd_ret_5d',
            'fwd_ret_20d'
        ]

        df = df[cols].dropna()
        df = df.rename(columns={'date': 'Date'})
        if df.empty:
            return pd.DataFrame()

        df['Ticker'] = ticker
        df['VWAP_Region'] = df['vwap_z_score'].apply(get_vwap_bucket)

        return df

    except Exception:
        return pd.DataFrame()

# ============================================================
# 📊 LABORATÓRIO
# ============================================================
def run_laboratory():
    print("🔬 Laboratório VWAP x Regime x Retorno")

    tickers = get_b3_tickers()
    results = []

    max_workers = max(1, cpu_count() - 2)
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_ticker, t): t for t in tickers}

        for future in tqdm(as_completed(futures), total=len(futures)):
            res = future.result()
            if not res.empty:
                results.append(res)

    if not results:
        print("❌ Nenhum dado")
        return

    df = pd.concat(results, ignore_index=True)
    print(f"✔ {len(df)} amostras consolidadas")

    # ========================================================
    # 📊 MATRIZ CONDICIONAL
    # ========================================================
    MIN_SAMPLES = 200

    table = (
        df
        .groupby(['VWAP_Region', 'regime_state'])
        .agg(
            samples=('fwd_ret_20d', 'count'),
            avg_ret_20d=('fwd_ret_20d', 'mean'),
            avg_ret_5d=('fwd_ret_5d', 'mean'),
            entropy=('Entropy_20', 'mean')
        )
        .query('samples >= @MIN_SAMPLES')
        .sort_values('avg_ret_20d', ascending=False)
    )

    print("\n" + "="*90)
    print("📊 VWAP × REGIME → RETORNO FUTURO")
    print("="*90)
    print(table)

    # ========================================================
    # 💾 SALVAR
    # ========================================================
    os.makedirs("src/co_piloto_quant/data/lab_results", exist_ok=True)
    table.to_csv("src/co_piloto_quant/data/lab_results/vwap_regime_forward_returns.csv")

    print("\n💾 Salvo em src/co_piloto_quant/data/lab_results/vwap_regime_forward_returns.csv")

# ============================================================
if __name__ == "__main__":
    run_laboratory()
