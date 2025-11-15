import sys
import os
import argparse
import pandas as pd


sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.data.data_fetching import fetch_data
from co_piloto_quant.data.data_processing import process_data

def main():
   
 
    parser = argparse.ArgumentParser(description="Pipeline de dados para buscar e processar dados de ativos financeiros.")
    parser.add_argument('--ticker', type=str, required=True, help='O ticker do ativo a ser processado (ex: PETR4.SA).')
    args = parser.parse_args()


    ticker = args.ticker
    print(f"--- INICIANDO PIPELINE PARA O TICKER: {ticker} ---") 

    period = "max"
    interval = "1d"

   
    raw_data = fetch_data(ticker=ticker, period=period, interval=interval)

    if raw_data.empty:
        print(f"Não foram encontrados dados para o ticker {ticker}. Encerrando o pipeline.")
        return

   
    processed_data = process_data(raw_data, ticker)

    
    print("\n### Dados Processados (5 primeiras linhas) ###")
    print(processed_data.head())
    
    print("\n### Informações do DataFrame Processado ###")
    processed_data.info()

    print(f"--- PIPELINE CONCLUÍDO PARA O TICKER: {ticker} ---")

if __name__ == "__main__":
    main()