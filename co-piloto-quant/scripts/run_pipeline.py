import sys
import argparse
import pandas as pd
from pathlib import Path

# Adiciona o diretório src ao path para garantir importações corretas
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

from co_piloto_quant.config import PROCESSED_DATA_PATH
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

    # 1. Busca Dados
    raw_data = fetch_data(ticker=ticker, period=period, interval=interval)

    if raw_data.empty:
        print(f"Não foram encontrados dados para o ticker {ticker}. Encerrando o pipeline.")
        return

    # 2. Processa Indicadores
    processed_data = process_data(raw_data, ticker)

    # 3. SALVA OS DADOS (A parte que faltava!)
    if not processed_data.empty:
        file_name = f"{ticker}_processed.csv"
        file_path = PROCESSED_DATA_PATH / file_name
        
        processed_data.to_csv(file_path)
        print(f"\n[SUCESSO] Arquivo salvo em: {file_path}")
        
        print("\n### Dados Processados (5 primeiras linhas) ###")
        print(processed_data.head())
    else:
        print("[ERRO] O processamento resultou em um DataFrame vazio.")

    print(f"--- PIPELINE CONCLUÍDO PARA O TICKER: {ticker} ---")

if __name__ == "__main__":
    main()