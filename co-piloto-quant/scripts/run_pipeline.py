import sys
import os
import pandas as pd


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.data.data_fetching import fetch_data
from co_piloto_quant.data.data_processing import process_data

def main():
 
    
    ticker = "VALE3.SA"
    period = "max"
    interval = "1d"

    
    raw_data = fetch_data(ticker=ticker, period=period, interval=interval)

    if raw_data.empty:
        print(f"Não foram encontrados dados para o ticker {ticker}. Encerrando o pipeline.")
        return

    print(f"Colunas dos dados brutos: {raw_data.columns}")

  
    processed_data = process_data(raw_data, ticker)

    
    print("\n### Dados Processados (5 primeiras linhas) ###")
    print(processed_data.head())
    
    print("\n### Informações do DataFrame Processado ###")
    processed_data.info()

   
if __name__ == "__main__":
    main()
