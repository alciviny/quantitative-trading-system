import sqlite3
import pandas as pd
from pathlib import Path

# Tenta importar a configuração, com fallback seguro
try:
    from co_piloto_quant.config import DATA_PATH
except (ModuleNotFoundError, ImportError):
    DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data"

DATA_PATH.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_PATH / "market_data.db"

def init_db():
    """Inicializa as tabelas do banco de dados."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                ticker TEXT PRIMARY KEY,
                sector TEXT,
                last_update TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                ticker TEXT,
                date TIMESTAMP,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                PRIMARY KEY (ticker, date),
                FOREIGN KEY (ticker) REFERENCES assets(ticker)
            )
        """)
        conn.commit()

def save_price_data(df: pd.DataFrame, ticker: str):
    """
    Salva dados OHLCV no SQLite usando Upsert.
    """
    if df.empty:
        return

    # 1. Garante índice Datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError("O índice deve ser DatetimeIndex.")

    # 2. Achata MultiIndex (comum no yfinance novo)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    # 3. Remove colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()]

    # 4. Seleciona e ordena colunas existentes
    # Nota: Usamos Capitalize (Open, High) porque é o padrão do yfinance
    cols_map = {'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'}
    
    # Prepara lista de tuplas para inserção rápida
    records = []
    
    # Itera de forma eficiente
    for idx, row in df.iterrows():
        # Captura valores com segurança (get) e fallback para 0.0
        r_open = float(row.get('Open', 0.0))
        r_high = float(row.get('High', 0.0))
        r_low = float(row.get('Low', 0.0))
        r_close = float(row.get('Close', 0.0))
        r_vol = float(row.get('Volume', 0.0))
        
        date_str = idx.strftime('%Y-%m-%d %H:%M:%S')
        
        records.append((ticker, date_str, r_open, r_high, r_low, r_close, r_vol))

    # 5. Executa Upsert em Lote
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, records)
        
        cursor.execute("INSERT OR REPLACE INTO assets (ticker, last_update) VALUES (?, CURRENT_TIMESTAMP)", (ticker,))
        conn.commit()
        # print(f"Salvo: {len(records)} registros para {ticker}.")

def load_price_data(ticker: str) -> pd.DataFrame:
    """Lê dados do banco e retorna com Index Datetime e colunas minúsculas."""
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker = ? ORDER BY date ASC"
        df = pd.read_sql_query(query, conn, params=(ticker,), index_col='date', parse_dates=['date'])
    
    return df