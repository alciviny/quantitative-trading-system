"""
Módulo de utilidades para fornecer listas de tickers e outras informações de apoio.
"""
import sqlite3
import pandas as pd
from datetime import datetime
from pathlib import Path

# Tenta importar a configuração, com fallback seguro
try:
    from co_piloto_quant.config import DATA_PATH
except (ModuleNotFoundError, ImportError):
    DATA_PATH = Path(__file__).resolve().parent.parent / "data"

DB_PATH = DATA_PATH / "market_data.db"


def get_ibov_tickers():
    """
    Retorna uma lista completa de tickers que compõem o IBOVESPA (Atualizado Nov/2025).
    A lista reflete as mudanças corporativas recentes (fusões e rebrandings).
    """
    return [
        "ABEV3.SA", "ALOS3.SA", "ASAI3.SA", "AURE3.SA", "AXIA3.SA", "AXIA6.SA", "AZUL4.SA", "AZZA3.SA",
        "B3SA3.SA", "BBAS3.SA", "BBDC3.SA", "BBDC4.SA", "BBSE3.SA", "BEEF3.SA", "BPAC11.SA", "BRAP4.SA",
        "BRAV3.SA", "BRKM5.SA", "CCRO3.SA", "CMIG4.SA", "CMIN3.SA", "COGN3.SA", "CPFE3.SA", "CPLE6.SA",
        "CRFB3.SA", "CSAN3.SA", "CSNA3.SA", "CVCB3.SA", "CXSE3.SA", "CYRE3.SA", "DIRR3.SA", "ECOR3.SA",
        "EGIE3.SA", "EMBJ3.SA", "ENEV3.SA", "ENGI11.SA", "EQTL3.SA", "EZTC3.SA", "FLRY3.SA", "GGBR4.SA",
        "GOAU4.SA", "HAPV3.SA", "HYPE3.SA", "IGTI11.SA", "IRBR3.SA", "ISAE4.SA", "ITSA4.SA", "ITUB4.SA",
        "JBSS3.SA", "KLBN11.SA", "LREN3.SA", "MBRF3.SA", "MGLU3.SA", "MOTV3.SA", "MRVE3.SA", "MULT3.SA",
        "NATU3.SA", "PETR3.SA", "PETR4.SA", "POMO4.SA", "PRIO3.SA", "PSSA3.SA", "RADL3.SA", "RAIL3.SA",
        "RAIZ4.SA", "RDOR3.SA", "RECV3.SA", "RENT3.SA", "SANB11.SA", "SBSP3.SA", "SLCE3.SA", "SMFT3.SA",
        "SMTO3.SA", "STBP3.SA", "SUZB3.SA", "TAEE11.SA", "TIMS3.SA", "TOTS3.SA", "UGPA3.SA", "USIM5.SA",
        "VALE3.SA", "VIVT3.SA", "WEGE3.SA", "YDUQ3.SA"
    ]

def get_top_50_tickers():
    """
    Retorna os 50 primeiros tickers da lista do IBOVESPA.
    Nota: A lista base está em ordem alfabética. Para uma seleção baseada em liquidez,
    seria ideal ordenar por volume médio antes de fatiar.
    """
    return get_ibov_tickers()[:50]

if __name__ == '__main__':
    # Exemplo de uso e verificação
    all_tickers = get_ibov_tickers()
    top_50 = get_top_50_tickers()
    
    print(f"Total de tickers no IBOV: {len(all_tickers)}")
    print(f"Top 50 tickers: {len(top_50)}")
    print("Amostra (top 5):", top_50[:5])
    
    # Verifica se novos tickers importantes estão presentes
    novos_tickers = ['MBRF3.SA', 'BRAV3.SA', 'AZZA3.SA', 'EMBJ3.SA']
    presentes = [t for t in novos_tickers if t in all_tickers]
    print(f"Novos tickers verificados na lista: {presentes}")


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
            # Verifica se a tabela existe antes de fazer a query
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