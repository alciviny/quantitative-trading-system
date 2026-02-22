
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import great_expectations as ge
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False

# Base de dados centralizada
DATA_BASE = os.path.join('src', 'co_piloto_quant', 'data')

import argparse
import logging
from src.etl import load_parquet, save_parquet
from src.logging_config import setup_logging
import pandas as pd

def profile_data(df):
    info = {
        'shape': df.shape,
        'columns': list(df.columns),
        'missing': df.isnull().sum().to_dict(),
        'dtypes': df.dtypes.astype(str).to_dict(),
    }
    return info

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline ETL parametrizado')
    parser.add_argument('--asset', required=True, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    setup_logging()
    logging.info(f'Iniciando ETL para {args.asset}')
    df = load_parquet(os.path.join(DATA_BASE, 'raw', f'{args.asset}.parquet'))
    logging.info(f'Perfil dos dados: {profile_data(df)}')
    # Validação automática com Great Expectations
    gdf = ge.from_pandas(df)
    # Exemplo de checks: sem NaN em colunas críticas, tipos corretos
    assert gdf.expect_column_values_to_not_be_null('close').success, 'Coluna close contém NaN!'
    assert gdf.expect_column_values_to_be_of_type('close', 'float64').success, 'Coluna close não é float!'
    # Adicione outros checks conforme necessário
    logging.info('Validação de dados (Great Expectations) passou com sucesso.')
    if HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {args.asset} - ETL', minimal=True)
        profile_path = os.path.join(DATA_BASE, 'processed', f'{args.asset}_profile_etl.html')
        profile.to_file(profile_path)
        logging.info(f'Relatório de qualidade salvo em {profile_path}')
    save_parquet(df, os.path.join(DATA_BASE, 'processed', f'{args.asset}.parquet'))
    logging.info(f'Arquivo salvo em {os.path.join(DATA_BASE, 'processed', f'{args.asset}.parquet')}')
