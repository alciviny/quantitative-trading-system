import os
import pandas as pd
import yfinance as yf

RAW_DATA_PATH = os.path.join(os.path.dirname(__file__), 'raw')
os.makedirs(RAW_DATA_PATH, exist_ok=True)

def save_raw_data(df: pd.DataFrame, filename: str):
    file_path = os.path.join(RAW_DATA_PATH, filename)
    df.to_csv(file_path, index=False)
    print(f"Dados brutos salvos em: {file_path}")

def fetch_data(ticker: str, period: str, interval: str) -> pd.DataFrame:
    print(f"Buscando dados para {ticker}...")

   
    data = yf.download(tickers=ticker, period=period, interval=interval)
    print("Dados brutos recebidos.")
    
    # Salvar os dados brutos
    filename = f"{ticker}_raw.csv"
    save_raw_data(data, filename)
    
    return data

def fetch_data_from_csv(file_path: str) -> pd.DataFrame:
    print(f"Lendo dados do arquivo CSV: {file_path}...")
    try:
        data = pd.read_csv(file_path)
        print("Dados do CSV lidos com sucesso.")
        return data
    except FileNotFoundError:
        print(f"Erro: O arquivo CSV não foi encontrado em {file_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"Erro ao ler o arquivo CSV: {e}")
        return pd.DataFrame()