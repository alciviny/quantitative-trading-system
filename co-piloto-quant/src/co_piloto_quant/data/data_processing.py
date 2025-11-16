
import os
import pandas as pd
from .data_fetching import fetch_data_from_csv


PROCESSED_DATA_PATH = os.path.join(os.path.dirname(__file__), 'processed')
os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)

def process_data(raw_data: pd.DataFrame,ticker: str) -> pd.DataFrame:
    
    processed_data = raw_data.copy()

    
    if isinstance(processed_data.columns, pd.MultiIndex):
        print("Removendo MultiIndex das colunas...")
        processed_data.columns = processed_data.columns.droplevel(1)
        

    processed_data.columns = processed_data.columns.str.lower()
    print(f"Colunas convertidas para minúsculo: {processed_data.columns.to_list()}")
    
   

    
    processed_data.dropna(inplace=True)
    print("Valores ausentes (pré-processamento) removidos.")

    
    
    try:
        processed_data['daily_return'] = processed_data['close'].pct_change()
        print("Retorno diário calculado.")
    except KeyError as e:
        
        print(f"ERRO: A coluna 'close' não foi encontrada após a limpeza.")
        print(f"Colunas disponíveis: {processed_data.columns}")
        raise e 

    
    
    processed_data.dropna(inplace=True)
    print("Valores ausentes (pós-processamento) removidos.")

    print("Processamento de dados concluído.")
    
    processed_data['ticker'] = ticker
    print(f"Ticker '{ticker}' adicionado aos dados.")
   
    
    filename = f"{ticker}_processed.csv"
    save_processed_data_to_csv(processed_data, filename)
    
    return processed_data

def save_processed_data_to_csv(processed_data: pd.DataFrame, filename: str):
    """
    Salva os dados processados em um arquivo CSV.
    Se o arquivo já existir, os novos dados serão concatenados aos dados existentes,
    removendo duplicatas e mantendo o arquivo atualizado.
    """
    file_path = os.path.join(PROCESSED_DATA_PATH, filename)
    print(f"Verificando o arquivo em {file_path}...")

    try:
        if os.path.exists(file_path):
            print("Arquivo existente encontrado. Carregando dados antigos...")
            existing_data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            
            print("Concatenando dados novos e antigos...")
            combined_data = pd.concat([existing_data, processed_data])
            
            
            if combined_data.index.name is None:
                combined_data.index.name = 'Date'

            index_name = combined_data.index.name
            combined_data.reset_index(inplace=True)

            print("Removendo e tratando duplicatas...")
            # Remove duplicatas com base na data e no ticker
            subset_cols = [index_name]
            if 'ticker' in combined_data.columns:
                subset_cols.append('ticker')
            
            combined_data.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
            
            combined_data.set_index(index_name, inplace=True)
            combined_data.sort_index(inplace=True) # Ordena os dados pela data
            
            print("Salvando dados combinados e atualizados...")
            combined_data.to_csv(file_path, index=True)
            print("Dados combinados salvos com sucesso.")
        else:
            print("Nenhum arquivo existente encontrado. Salvando novos dados...")
            processed_data.to_csv(file_path, index=True)
            print("Novos dados processados salvos com sucesso.")
            
    except Exception as e:
        print(f"Erro ao salvar ou processar o arquivo CSV: {e}")