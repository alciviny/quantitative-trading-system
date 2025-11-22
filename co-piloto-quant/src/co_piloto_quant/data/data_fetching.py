import pandas as pd
import yfinance as yf
import logging
from co_piloto_quant.config import RAW_DATA_PATH

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    """Exceção customizada para erros durante a busca ou leitura de dados."""
    pass



def save_raw_data(df: pd.DataFrame, filename: str):
    file_path = RAW_DATA_PATH / filename
    df.to_csv(file_path, index=False)
    logger.info(f"Dados brutos salvos em: {file_path}")

def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    logger.info(f"Buscando dados para {ticker}...")

   
    data = yf.download(tickers=ticker, period=period, interval=interval)
    logger.info("Dados brutos recebidos.")
    
   
    filename = f"{ticker}_raw.csv"
    save_raw_data(data, filename)
    
    return data

def fetch_data_from_csv(file_path: str) -> pd.DataFrame:
    logger.info(f"Lendo dados do arquivo CSV: {file_path}...")
    try:
        data = pd.read_csv(file_path)
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