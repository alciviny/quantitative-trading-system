import sqlite3
import pandas as pd
from pathlib import Path

from co_piloto_quant.config import DATABASE_PATH


# Não cria diretórios automaticamente aqui, apenas usa o caminho do config

DB_PATH = DATABASE_PATH


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

    import logging
    logger = logging.getLogger("DataSave")
    if df.empty:
        logger.critical(f"[CRITICAL] DataFrame vazio para {ticker}. Nada será salvo!")
        return


    # 1. Garante índice Datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError("O índice deve ser DatetimeIndex ou conversível para ele.")

    # 2. Normalização robusta de colunas OHLCV
    import re
    ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
    new_df = pd.DataFrame(index=df.index)
    for col in ohlcv_cols:
        # Busca coluna exata (case insensitive)
        found = [c for c in df.columns if (isinstance(c, str) and c.lower() == col)]
        if found:
            new_df[col] = df[found[0]]
            continue
        # Busca MultiIndex (ex: ('close', 'vale3.sa'))
        found = [c for c in df.columns if (isinstance(c, tuple) and c[0].lower() == col)]
        if found:
            new_df[col] = df[found[0]]
            continue
        # Busca coluna que termina com .<ticker> (ex: close.vale3.sa)
        found = [c for c in df.columns if isinstance(c, str) and c.lower().endswith('.' + ticker.lower()) and c.lower().startswith(col)]
        if found:
            new_df[col] = df[found[0]]
        else:
            new_df[col] = float('nan')
    df = new_df
    # Converte todas as colunas para lowercase
    df.columns = [c.lower() for c in df.columns]

    # 3. Remove colunas duplicadas (mantém a última, que geralmente tem os dados corretos)
    df = df.loc[:, ~df.columns.duplicated(keep='last')]

    # LOG: Mostra as primeiras linhas após normalização
    logger.info(f"[DEBUG SAVE] {ticker} após normalização OHLCV:\n{df.head(3)}")

    # 4. Padroniza colunas (Case insensitive)
    curr_cols = {c.lower(): c for c in df.columns}
    required_map = {
        'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'
    }
    df_clean = pd.DataFrame(index=df.index)
    for req_lower, req_final in required_map.items():
        if req_lower in curr_cols:
            df_clean[req_final] = df[curr_cols[req_lower]].copy()
        else:
            df_clean[req_final] = float('nan')

    # Blindagem institucional: só salva datas reais da fonte
    mask_valid = (~df_clean[ohlcv_cols].isna()).all(axis=1) & (df_clean[ohlcv_cols] != 0).all(axis=1)
    n_before = len(df_clean)
    df_clean = df_clean[mask_valid]
    n_after = len(df_clean)
    if n_after < n_before:
        logger.critical(f"[CRITICAL] {n_before-n_after} linhas removidas por conterem zero/NaN em OHLCV para {ticker}. Verifique expansão de datas no pipeline!")

    if df_clean.empty:
        logger.critical(f"[CRITICAL] Nenhuma linha válida para {ticker} após blindagem. Nada será salvo!")
        return

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