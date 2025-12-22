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
    """Inicializa as tabelas e configura o modo WAL para concorrência."""
    with sqlite3.connect(DB_PATH) as conn:
        # ATIVA O WAL: Permite leitura e escrita simultâneas sem travar
        conn.execute("PRAGMA journal_mode=WAL;") 
        conn.execute("PRAGMA synchronous=NORMAL;") # Mais performance, seguro o suficiente
        
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
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trades_execution (
                ticket_id INTEGER PRIMARY KEY, -- Ticket do MT5
                ticker TEXT,
                entry_time TIMESTAMP,
                exit_time TIMESTAMP,
                entry_price REAL,
                exit_price REAL,
                size REAL,
                profit REAL,
                strategy_name TEXT,
                magic_number INTEGER
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS signals_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                signal_type TEXT NOT NULL,       -- Ex: 'COMPRA_TENDENCIA', 'VENDA_SNIPER'
                price_at_signal REAL,            -- Preço na hora do sinal
                
                -- Features (Os dados que a IA vai aprender a ler)
                hurst_val REAL,
                entropy_val REAL,
                hilbert_cycle TEXT,
                hilbert_period REAL,
                half_life REAL,
                ou_r2 REAL,
                
                -- Targets (O resultado futuro - preenchido depois)
                price_5d_later REAL,
                price_10d_later REAL,
                result_5d_pct REAL,
                success_5d BOOLEAN
            )
        """)
        conn.commit()

def save_price_data(df: pd.DataFrame, ticker: str):
    """
    Salva dados OHLCV no SQLite usando uma abordagem vetorizada robusta.
    """
    if df.empty:
        return

    # 1. Garante índice Datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError("O índice deve ser DatetimeIndex ou conversível para ele.")

    # 2. Achata MultiIndex (comum em algumas fontes de dados)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2.1 CORREÇÃO DE SEGURANÇA: Remove tuplas residuais nas colunas
    # Se o pandas.concat criou colunas como ('close', 'PETR4'), transformamos em 'close'
    new_cols = []
    for c in df.columns:
        if isinstance(c, tuple):
            new_cols.append(str(c[0])) # Pega o primeiro elemento da tupla
        else:
            new_cols.append(str(c))
    df.columns = new_cols

    # 3. Remove colunas duplicadas
    df = df.loc[:, ~df.columns.duplicated()]

    # 4. Padroniza colunas (Case insensitive)
    # Cria um mapa reverso para encontrar 'Open', 'open', 'OPEN', etc.
    curr_cols = {c.lower(): c for c in df.columns}
    
    required_map = {
        'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'
    }
    
    df_clean = pd.DataFrame(index=df.index)
    
    # Preenche as colunas necessárias, usando 0.0 se não existirem
    for req_lower, req_final in required_map.items():
        if req_lower in curr_cols:
            df_clean[req_final] = df[curr_cols[req_lower]].copy()
        else:
            df_clean[req_final] = 0.0

    # 5. Prepara dados para inserção
    # Preenche NaN com 0.0
    df_clean = df_clean.fillna(0.0)

    # Extrai datas diretamente do índice (independente do nome ser 'Date', 'index' ou None)
    dates = df_clean.index.strftime('%Y-%m-%d %H:%M:%S').tolist()
    
    # Cria lista de tickers
    tickers = [ticker] * len(dates)
    
    # Cria a lista de tuplas para o executemany
    records = list(zip(
        tickers,
        dates,
        df_clean['open'].tolist(),
        df_clean['high'].tolist(),
        df_clean['low'].tolist(),
        df_clean['close'].tolist(),
        df_clean['volume'].tolist()
    ))

    if not records:
        return

    # 6. Executa Upsert em Lote
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.executemany("""
                INSERT OR REPLACE INTO ohlcv (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, records)

            cursor.execute("INSERT OR REPLACE INTO assets (ticker, last_update) VALUES (?, CURRENT_TIMESTAMP)", (ticker,))
            conn.commit()
    except Exception as e:
        print(f"ERRO CRÍTICO ao salvar {ticker} no banco: {e}")

def load_price_data(ticker: str) -> pd.DataFrame:
    """Lê dados do banco e retorna com Index Datetime e colunas minúsculas."""
    with sqlite3.connect(DB_PATH) as conn:
        query = "SELECT date, open, high, low, close, volume FROM ohlcv WHERE ticker = ? ORDER BY date ASC"
        df = pd.read_sql_query(query, conn, params=(ticker,), index_col='date', parse_dates=['date'])
    
    return df

def load_ml_dataset() -> pd.DataFrame:
    """Carrega todo o dataset de ML (features e targets) da tabela signals_history."""
    with sqlite3.connect(DB_PATH) as conn:
        # O PRAGMA WAL ainda é uma boa ideia para leituras concorrentes
        conn.execute("PRAGMA journal_mode=WAL;")
        query = "SELECT * FROM signals_history"
        df = pd.read_sql_query(query, conn, parse_dates=['date'])
    return df