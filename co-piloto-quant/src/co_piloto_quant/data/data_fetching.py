import pandas as pd
import yfinance as yf
import logging
import pathlib
from co_piloto_quant.config import RAW_DATA_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    """Exceção customizada para erros durante a busca ou leitura de dados."""
    pass



def save_raw_data(df: pd.DataFrame, filename: str):
    """Salva o DataFrame em um arquivo CSV no diretório de dados brutos."""
    # Garante que o diretório de dados brutos exista
    RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)
    file_path = RAW_DATA_PATH / filename
    
    # yfinance retorna o 'Date' como índice, então o salvamos na planilha
    df.to_csv(file_path, index=True)
    logger.info(f"Dados brutos salvos em: {file_path}")

def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    """Busca dados para um único ticker e salva em CSV."""
    logger.info(f"Buscando dados para {ticker}...")
    
    # O yfinance já formata o índice como Datetime
    data = yf.download(tickers=ticker, period=period, interval=interval)
    
    if data.empty:
        logger.warning(f"Nenhum dado retornado para {ticker}.")
        return pd.DataFrame()

    logger.info(f"Dados brutos recebidos para {ticker}.")
    
    filename = f"{ticker}_raw.csv"
    save_raw_data(data, filename)
    
    return data

def fetch_batch_data(tickers: list, period: str, interval: str) -> dict:
    """
    Busca dados para uma lista de tickers em lote para otimizar a performance.
    
    Args:
        tickers (list): A lista de tickers a serem buscados (ex: ["PETR4.SA", "VALE3.SA"]).
        period (str): O período a ser buscado (ex: "1y", "6mo").
        interval (str): O intervalo dos candles (ex: "1d", "1h").
        
    Returns:
        dict: Um dicionário onde as chaves são os tickers e os valores são os DataFrames.
    """
    logger.info(f"Iniciando download em lote para {len(tickers)} tickers...")
    
    # Baixa todos os dados de uma vez com threads para máxima performance
    # group_by='ticker' organiza o resultado em um formato fácil de iterar
    all_data = yf.download(
        tickers=tickers,
        period=period,
        interval=interval,
        group_by='ticker',
        threads=True
    )
    
    if all_data.empty:
        logger.error("O download em lote falhou. Nenhum dado foi retornado.")
        raise DataFetchError("Falha no download em lote do yfinance.")

    logger.info("Download em lote concluído. Salvando arquivos individuais...")
    
    saved_data = {}
    for ticker in tickers:
        # O DataFrame de cada ticker fica acessível como uma chave do dict-like object
        ticker_data = all_data.get(ticker)
        
        # Verifica se há dados e se não estão todos vazios
        if ticker_data is not None and not ticker_data.dropna(how='all').empty:
            filename = f"{ticker}_raw.csv"
            save_raw_data(ticker_data, filename)
            saved_data[ticker] = ticker_data
        else:
            logger.warning(f"Nenhum dado válido retornado para {ticker} no lote.")
            
    logger.info(f"{len(saved_data)} arquivos de tickers salvos com sucesso.")
    return saved_data


def fetch_data_from_csv(file_path: str) -> pd.DataFrame:
    """Lê dados de um arquivo CSV, tratando o índice de data."""
    logger.info(f"Lendo dados do arquivo CSV: {file_path}...")
    try:
        # 'Date' foi salvo como a primeira coluna, então o usamos como índice
        data = pd.read_csv(file_path, index_col='Date', parse_dates=True)
        if data.empty:
            raise DataFetchError(f"O arquivo de dados está vazio: {file_path}")
        logger.info("Dados do CSV lidos com sucesso.")
        return data
    except FileNotFoundError as e:
        logger.error(f"Erro: O arquivo CSV não foi encontrado em {file_path}")
        raise DataFetchError(f"Arquivo não encontrado: {file_path}") from e
    except pd.errors.EmptyDataError as e:
        logger.error(f"Erro: O arquivo de dados está vazio ou mal formatado em {file_path}")
        raise DataFetchError(f"Arquivo vazio ou mal formatado: {file_path}") from e
    except Exception as e:
        logger.error(f"Erro inesperado ao ler o arquivo CSV: {e}")
        raise DataFetchError(f"Erro inesperado ao ler o arquivo: {file_path}") from e