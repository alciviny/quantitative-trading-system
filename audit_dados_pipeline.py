import os
import pandas as pd
import sqlite3
from glob import glob

# Auditoria de arquivos Parquet
def audit_parquet_files(parquet_dir):
    print(f"\n--- Auditoria de arquivos Parquet em: {parquet_dir} ---")
    files = glob(os.path.join(parquet_dir, '*.parquet'))
    for file in files:
        try:
            df = pd.read_parquet(file)
            if df.empty:
                print(f"[EMPTY] {file}")
                continue
            # Verifica linhas zeradas ou NaN nas colunas principais
            cols = [c for c in df.columns if c.lower() in ['open','high','low','close','volume']]
            if cols:
                mask_zero = (df[cols].fillna(0.0) == 0.0).all(axis=1)
                mask_nan = df[cols].isna().any(axis=1)
                n_zero = mask_zero.sum()
                n_nan = mask_nan.sum()
                if n_zero > 0 or n_nan > 0:
                    print(f"[PROBLEMA] {file}: {n_zero} linhas zeradas, {n_nan} linhas com NaN")
            else:
                print(f"[AVISO] {file}: não encontrou colunas OHLCV")
        except Exception as e:
            print(f"[ERRO] {file}: {e}")

# Auditoria do banco SQLite
def audit_sqlite_ohlcv(db_path):
    print(f"\n--- Auditoria do banco SQLite: {db_path} ---")
    conn = sqlite3.connect(db_path)
    query = "SELECT ticker, date, open, high, low, close, volume FROM ohlcv"
    df = pd.read_sql_query(query, conn, parse_dates=['date'])
    conn.close()
    if df.empty:
        print("[EMPTY] Banco de dados sem dados OHLCV.")
        return
    mask_zero = (df[['open','high','low','close','volume']].fillna(0.0) == 0.0).all(axis=1)
    mask_nan = df[['open','high','low','close','volume']].isna().any(axis=1)
    n_zero = mask_zero.sum()
    n_nan = mask_nan.sum()
    if n_zero > 0 or n_nan > 0:
        print(f"[PROBLEMA] OHLCV: {n_zero} linhas zeradas, {n_nan} linhas com NaN")
        print(df.loc[mask_zero | mask_nan, ['ticker','date','open','high','low','close','volume']].head(10))
    else:
        print("[OK] Nenhuma linha zerada ou com NaN no banco.")

if __name__ == "__main__":
    # Ajuste os caminhos conforme necessário
    parquet_dirs = [
        "co-piloto-quant/data/features",
        "co-piloto-quant/data/processed",
        "co-piloto-quant/data/raw"
    ]
    db_path = "co-piloto-quant/data/raw/market_data.db"
    for d in parquet_dirs:
        if os.path.exists(d):
            audit_parquet_files(d)
    if os.path.exists(db_path):
        audit_sqlite_ohlcv(db_path)
