def process_asset(asset_path):
    import os
    import logging
    from src.etl import load_parquet, save_parquet
    from src.features import add_features
    from src.logging_config import setup_logging
    from pandera import Column, DataFrameSchema, Check
    asset_filename = os.path.basename(asset_path)
    asset_name = asset_filename.replace('_processed.parquet', '')
    logging.info(f'Calculando features para {asset_name} (arquivo: {asset_path})')
    df = load_parquet(asset_path)
    logging.info(f'Perfil antes das features: {profile_data(df)}')
    schema = DataFrameSchema({
        "open":   Column(float, Check(lambda x: x > 0), nullable=False),
        "high":   Column(float, Check(lambda x: x > 0), nullable=False),
        "low":    Column(float, Check(lambda x: x > 0), nullable=False),
        "close":  Column(float, Check(lambda x: x > 0), nullable=False),
        "volume": Column(float, Check(lambda x: x >= 0), nullable=False),
    })
    schema.validate(df)
    logging.info('Validação de dados (Pandera) passou com sucesso (antes das features).')
    # Profiling antes das features
    if 'HAS_PROFILING' in globals() and HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {asset_name} - before features', minimal=True)
        profile_path = os.path.join(DATA_BASE, 'features', f'{asset_name}_profile_before.html')
        profile.to_file(profile_path)
        logging.info(f'Relatório de qualidade salvo em {profile_path}')
    df = add_features(df)
    logging.info(f'Perfil após features: {profile_data(df)}')
    # Remover colunas duplicadas (mantém a primeira ocorrência)
    if df.columns.duplicated().any():
        duplicated_cols = df.columns[df.columns.duplicated()].tolist()
        logging.warning(f'Colunas duplicadas detectadas: {duplicated_cols}. Removendo duplicatas.')
        df = df.loc[:, ~df.columns.duplicated()]
    # Profiling após as features
    if 'HAS_PROFILING' in globals() and HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {asset_name} - after features', minimal=True)
        profile2_path = os.path.join(DATA_BASE, 'features', f'{asset_name}_profile_after.html')
        profile2.to_file(profile2_path)
        logging.info(f'Relatório de qualidade salvo em {profile2_path}')
    save_parquet(df, os.path.join(DATA_BASE, 'features', f'{asset_name}_features.parquet'))
    logging.info(f'Arquivo salvo em {os.path.join(DATA_BASE, "features", f"{asset_name}_features.parquet")}')
def safe_process(file):
    try:
        process_asset(file)
        return (file, None)
    except Exception as e:
        return (file, str(e))

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pandera as pa
from pandera import Column, DataFrameSchema, Check
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False

# Base de dados centralizada (corrigido para buscar sempre dentro do projeto co-piloto-quant)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'src', 'co_piloto_quant', 'data'))

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
    import glob
    parser = argparse.ArgumentParser(description='Pipeline de features parametrizado')
    parser.add_argument('--asset', required=False, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    setup_logging()


    if args.asset:
        # Mantém compatibilidade: aceita nome do ativo, monta caminho
        asset_path = os.path.join(DATA_BASE, 'processed', f'{args.asset}_processed.parquet')
        process_asset(asset_path)
    else:
        # Roda para todos os arquivos *_processed.parquet em paralelo
        processed_dir = os.path.join(DATA_BASE, 'processed')
        abs_processed_dir = os.path.abspath(processed_dir)
        logging.info(f'Buscando arquivos em: {abs_processed_dir}')
        files = glob.glob(os.path.join(processed_dir, '*_processed.parquet'))
        logging.info(f'Arquivos encontrados: {files}')
        if not files:
            logging.warning('Nenhum arquivo *_processed.parquet encontrado para processar.')
        else:
            from concurrent.futures import ProcessPoolExecutor, as_completed
            import multiprocessing
            max_workers = min(multiprocessing.cpu_count(), len(files))
            logging.info(f'Processando em paralelo com {max_workers} processos.')
            with ProcessPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(safe_process, file) for file in files]
                for future in as_completed(futures):
                    file, error = future.result()
                    if error:
                        logging.error(f'Erro ao processar {file}: {error}')
                    else:
                        logging.info(f'Processamento concluído para {file}')
