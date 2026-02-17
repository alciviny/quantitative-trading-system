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
from src.features import add_features
from src.logging_config import setup_logging

def profile_data(df):
    info = {
        'shape': df.shape,
        'columns': list(df.columns),
        'missing': df.isnull().sum().to_dict(),
        'dtypes': df.dtypes.astype(str).to_dict(),
    }
    return info

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline de features parametrizado')
    parser.add_argument('--asset', required=True, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    setup_logging()
    logging.info(f'Calculando features para {args.asset}')
    df = load_parquet(f'data/processed/{args.asset}.parquet')
    logging.info(f'Perfil antes das features: {profile_data(df)}')
    gdf = ge.from_pandas(df)
    assert gdf.expect_column_values_to_not_be_null('close').success, 'Coluna close contém NaN!'
    # Adicione outros checks conforme necessário
    logging.info('Validação de dados (Great Expectations) passou com sucesso (antes das features).')
    if HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {args.asset} - before features', minimal=True)
        profile.to_file(f'data/features/{args.asset}_profile_before.html')
        logging.info(f'Relatório de qualidade salvo em data/features/{args.asset}_profile_before.html')
    df = add_features(df)
    logging.info(f'Perfil após features: {profile_data(df)}')
    gdf2 = ge.from_pandas(df)
    assert gdf2.expect_column_values_to_not_be_null('realized_volatility').success, 'Feature realized_volatility contém NaN!'
    # Adicione outros checks conforme necessário
    logging.info('Validação de dados (Great Expectations) passou com sucesso (após features).')
    if HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {args.asset} - after features', minimal=True)
        profile2.to_file(f'data/features/{args.asset}_profile_after.html')
        logging.info(f'Relatório de qualidade salvo em data/features/{args.asset}_profile_after.html')
    save_parquet(df, f'data/features/{args.asset}_features.parquet')
    logging.info(f'Arquivo salvo em data/features/{args.asset}_features.parquet')
