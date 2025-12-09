"""
Módulo de utilidades para fornecer listas de tickers e outras informações de apoio.
Refatorado para incluir um universo expandido de ativos globais.
"""
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Tenta importar a configuração, com fallback seguro
try:
    from co_piloto_quant.config import DATA_PATH
except (ModuleNotFoundError, ImportError):
    # Fallback para o caso de o script ser executado de forma isolada
    DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data"

DB_PATH = DATA_PATH / "market_data.db"


def get_b3_tickers() -> list:
    """
    Retorna uma lista de tickers de alta liquidez da B3 (IBOVESPA).
    A lista reflete a composição do IBOVESPA com algumas adições de liquidez.
    """
    return [
        "ABEV3.SA", "ALOS3.SA", "ASAI3.SA", "AURE3.SA", "AZUL4.SA", "B3SA3.SA",
        "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", "BEEF3.SA", "BPAC11.SA",
        "BRAP4.SA", "BRFS3.SA", "BRKM5.SA", "CCRO3.SA", "CIEL3.SA", "CMIG4.SA",
        "CMIN3.SA", "COGN3.SA", "CPFE3.SA", "CPLE6.SA", "CRFB3.SA", "CSAN3.SA",
        "CSNA3.SA", "CVCB3.SA", "CXSE3.SA", "CYRE3.SA", "DIRR3.SA", "ECOR3.SA",
        "EGIE3.SA", "ELET3.SA", "ELET6.SA", "EMBR3.SA", "ENEV3.SA", "ENGI11.SA",
        "EQTL3.SA", "EZTC3.SA", "FLRY3.SA", "GGBR4.SA", "GOAU4.SA", "HAPV3.SA",
        "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ITSA4.SA", "ITUB4.SA", "JBSS3.SA",
        "KLBN11.SA", "LREN3.SA", "LWSA3.SA", "MGLU3.SA", "MRFG3.SA", "MRVE3.SA",
        "MULT3.SA", "NTCO3.SA", "PETR3.SA", "PETR4.SA", "PCAR3.SA", "PRIO3.SA",
        "RADL3.SA", "RAIL3.SA", "RAIZ4.SA", "RDOR3.SA", "RECV3.SA", "RENT3.SA",
        "RRRP3.SA", "SANB11.SA", "SBSP3.SA", "SLCE3.SA", "SMFT3.SA", "SUZB3.SA",
        "TAEE11.SA", "TIMS3.SA", "TOTS3.SA", "UGPA3.SA", "USIM5.SA", "VALE3.SA",
        "VBBR3.SA", "VIVT3.SA", "WEGE3.SA", "YDUQ3.SA"
    ]

def get_us_tech_tickers() -> list:
    """Retorna uma lista das Top 20+ empresas de tecnologia dos EUA."""
    return [
        "AAPL", "MSFT", "GOOG", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "AVGO", "ASML", "ORCL", "ADBE", "CRM", "AMD", "INTC", "QCOM",
        "CSCO", "IBM", "TXN", "SAP", "NFLX", "MU", "PYPL", "SNPS"
    ]

def get_forex_tickers() -> list:
    """Retorna os principais pares de moedas (Majors) e cruzados importantes."""
    return [
        "EURUSD=X", "USDJPY=X", "GBPUSD=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X",
        "NZDUSD=X", "EURJPY=X", "GBPJPY=X", "EURGBP=X", "AUDJPY=X", "USDBRL=X",
        "EURCAD=X", "EURAUD=X"
    ]

def get_crypto_tickers() -> list:
    """Retorna as Top 10+ criptomoedas pareadas com Dólar (USD)."""
    return [
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "ADA-USD",
        "DOGE-USD", "AVAX-USD", "SHIB-USD", "DOT-USD", "LINK-USD", "MATIC-USD"
    ]

def get_global_indices_and_commodities() -> list:
    """Retorna ETFs/Futuros de índices globais e commodities."""
    return [
        "^GSPC",   # S&P 500
        "^IXIC",   # NASDAQ Composite
        "^DJI",    # Dow Jones Industrial Average
        "^FTSE",   # FTSE 100 (Londres)
        "^GDAXI",  # DAX (Alemanha)
        "^FCHI",   # CAC 40 (França)
        "^N225",   # Nikkei 225 (Japão)
        "^HSI",    # Hang Seng (Hong Kong)
        "EWZ",     # iShares MSCI Brazil ETF
        "GC=F",    # Ouro
        "CL=F",    # Petróleo Cru
        "SI=F",    # Prata
        "HG=F",    # Cobre
        "^TNX"     # US 10-Year Treasury Yield
    ]

def get_expanded_universe() -> list:
    """
    Combina todas as categorias de ativos em uma lista única e limpa.
    Remove duplicatas e ordena alfabeticamente.
    """
    all_tickers = (
        get_b3_tickers() +
        get_us_tech_tickers() +
        get_forex_tickers() +
        get_crypto_tickers() +
        get_global_indices_and_commodities()
    )
    # Remove duplicatas e ordena
    unique_tickers = sorted(list(set(all_tickers)))
    return unique_tickers

# --- Funções Legadas (acesso ao DB) ---

def get_scanner_tickers(date: str = 'today') -> list:
    """
    Busca no banco de dados os tickers que tiveram um sinal na data especificada.

    Args:
        date (str, optional): A data para buscar os sinais.
                              Pode ser 'today' (padrão) ou uma data no formato 'YYYY-MM-DD'.

    Returns:
        list: Uma lista de tickers únicos que tiveram sinais na data.
    """
    if date == 'today':
        query_date = datetime.now().strftime("%Y-%m-%d")
    else:
        query_date = date

    if not DB_PATH.exists():
        print(f"Erro: O arquivo de banco de dados não foi encontrado em: {DB_PATH}")
        return []

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='signals_history';")
            if cursor.fetchone() is None:
                print(f"Erro: A tabela 'signals_history' não existe no banco de dados.")
                return []

            query = "SELECT DISTINCT ticker FROM signals_history WHERE date = ?"
            df = pd.read_sql_query(query, conn, params=(query_date,))

        if df.empty:
            print(f"Nenhum ticker com sinal encontrado no banco de dados para a data: {query_date}")
            return []

        return df['ticker'].tolist()
    except Exception as e:
        print(f"Erro ao acessar o banco de dados de sinais: {e}")
        return []


def get_all_available_tickers() -> list:
    """
    Busca no banco de dados todos os tickers distintos que possuem dados de preço (OHLCV).

    Returns:
        list: Uma lista ordenada de todos os tickers disponíveis.
    """
    if not DB_PATH.exists():
        print(f"Erro: O arquivo de banco de dados não foi encontrado em: {DB_PATH}")
        return []
    try:
        with sqlite3.connect(DB_PATH) as conn:
            query = "SELECT DISTINCT ticker FROM ohlcv ORDER BY ticker ASC"
            df = pd.read_sql_query(query, conn)
        return df['ticker'].tolist()
    except Exception as e:
        print(f"Erro ao buscar todos os tickers do banco de dados: {e}")
        return []


if __name__ == '__main__':
    # --- Teste de Validação do Universo Expandido ---
    print("--- 🔬 VALIDANDO UNIVERSO DE DADOS EXPANDIDO ---")

    b3 = get_b3_tickers()
    us_tech = get_us_tech_tickers()
    forex = get_forex_tickers()
    crypto = get_crypto_tickers()
    indices = get_global_indices_and_commodities()
    
    print(f"\nCategorias de Ativos:")
    print(f"  - B3 (Ações BR): {len(b3)} ativos")
    print(f"  - US Tech (Ações EUA): {len(us_tech)} ativos")
    print(f"  - Forex (Pares de Moedas): {len(forex)} ativos")
    print(f"  - Cripto (Pares com USD): {len(crypto)} ativos")
    print(f"  - Índices & Commodities Globais: {len(indices)} ativos")

    total_bruto = len(b3) + len(us_tech) + len(forex) + len(crypto) + len(indices)
    print(f"\nSoma Bruta de Ativos: {total_bruto}")

    universo_expandido = get_expanded_universe()
    total_liquido = len(universo_expandido)
    
    print(f"Total de Ativos Únicos no Universo Expandido: {total_liquido}")

    # Verificação de qualidade
    if total_liquido > 120:
        print(f"\n✅ SUCESSO: O universo expandido contém {total_liquido} ativos (meta > 120).")
    else:
        print(f"\n⚠️ ALERTA: O universo expandido contém apenas {total_liquido} ativos. Verifique as listas.")
        
    print("\nAmostra do Universo Expandido (10 primeiros):")
    print(universo_expandido[:10])

    print("\n--- Teste das funções de banco de dados (legadas) ---")
    # Nota: Essas funções dependem do estado atual do seu banco de dados local.
    scanner_today = get_scanner_tickers()
    print(f"\nTickers do Scanner para hoje ({datetime.now().strftime('%Y-%m-%d')}): {len(scanner_today)}")
    if scanner_today:
        print(f"  Amostra: {scanner_today[:5]}")

    all_db_tickers = get_all_available_tickers()
    print(f"\nTotal de tickers disponíveis no DB: {len(all_db_tickers)}")
    if all_db_tickers:
        print(f"  Amostra: {all_db_tickers[:5]}")
