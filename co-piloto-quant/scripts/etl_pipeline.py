import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import great_expectations as ge
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False

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
    df = load_parquet(f'data/raw/{args.asset}.parquet')
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
        profile.to_file(f'data/processed/{args.asset}_profile_etl.html')
        logging.info(f'Relatório de qualidade salvo em data/processed/{args.asset}_profile_etl.html')
    save_parquet(df, f'data/processed/{args.asset}.parquet')
    logging.info(f'Arquivo salvo em data/processed/{args.asset}.parquet')
