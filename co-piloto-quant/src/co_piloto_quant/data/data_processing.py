
import os
import pandas as pd
from .data_fetching import fetch_data_from_csv
from ..indicators.on_balance_true_range import calculate_obtr
from ..indicators.williams_ad import calculate_wad
from ..indicators.ifr_tpm import calculate_ifr
from ..indicators.bollinger_bands import calculate_bollinger_bands
from ..indicators.multi_bollinger_bands import calculate_multi_bollinger_bands


PROCESSED_DATA_PATH = os.path.join(os.path.dirname(__file__), 'processed')
os.makedirs(PROCESSED_DATA_PATH, exist_ok=True)

INDICATOR_FUNCTIONS = {
    'obtr': calculate_obtr,
    'wad': calculate_wad,
    'ifr': calculate_ifr,
    'bbands': calculate_bollinger_bands,
    'multi_bbands': calculate_multi_bollinger_bands,
}

def process_data(raw_data: pd.DataFrame, ticker: str, indicators: list = None) -> pd.DataFrame:
    
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

    if indicators:
        print(f"Calculando indicadores: {indicators}")
        for indicator in indicators:
            if indicator in INDICATOR_FUNCTIONS:
                try:
                    # A função do indicador pode retornar um ou mais Series
                    indicator_output = INDICATOR_FUNCTIONS[indicator](processed_data)
                    if isinstance(indicator_output, pd.DataFrame):
                        processed_data = processed_data.join(indicator_output)
                    else: # Se for uma Series
                        processed_data[indicator] = indicator_output
                    print(f"Indicador '{indicator}' calculado e adicionado.")
                except Exception as e:
                    print(f"ERRO ao calcular o indicador '{indicator}': {e}")
            else:
                print(f"AVISO: Indicador '{indicator}' não reconhecido.")

    
    processed_data.dropna(inplace=True)
    print("Valores ausentes (pós-processamento) removidos.")

    print("Processamento de dados concluído.")
    
    processed_data['ticker'] = ticker
    print(f"Ticker '{ticker}' adicionado aos dados.")
   
    
    filename = f"{ticker}_processed.csv"
    save_processed_data_to_csv(processed_data, filename)
    
    return processed_data

def save_processed_data_to_csv(processed_data: pd.DataFrame, filename: str):
   
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
            
            subset_cols = [index_name]
            if 'ticker' in combined_data.columns:
                subset_cols.append('ticker')
            
            combined_data.drop_duplicates(subset=subset_cols, keep='last', inplace=True)
            
            combined_data.set_index(index_name, inplace=True)
            combined_data.sort_index(inplace=True)  
            
            print("Salvando dados combinados e atualizados...")
            combined_data.to_csv(file_path, index=True)
            print("Dados combinados salvos com sucesso.")
        else:
            print("Nenhum arquivo existente encontrado. Salvando novos dados...")
            processed_data.to_csv(file_path, index=True)
            print("Novos dados processados salvos com sucesso.")
            
    except Exception as e:
        print(f"Erro ao salvar ou processar o arquivo CSV: {e}")