def process_asset(asset_path):
    import os
    import logging
    from src.etl import load_parquet, save_parquet
    from src.features import add_features
    from src.logging_config import setup_logging
    from pandera import Column, DataFrameSchema, Check
    asset_filename = os.path.basename(asset_path)
    asset_name = asset_filename.replace('_processed.parquet', '')
    logging.info(f'Iniciando cálculo de features para {asset_name} (arquivo: {asset_path})')
    logging.debug(f'Carregando arquivo: {asset_path}')
    try:
        df = load_parquet(asset_path)
        logging.info('Arquivo carregado com sucesso.')
    except Exception as e:
        logging.error(f'Erro ao carregar arquivo {asset_path}: {e}')
        raise
    logging.info(f'Perfil antes das features: {profile_data(df)}')
    schema = DataFrameSchema({
        "open":   Column(float, Check(lambda x: x > 0), nullable=False),
        "high":   Column(float, Check(lambda x: x > 0), nullable=False),
        "low":    Column(float, Check(lambda x: x > 0), nullable=False),
        "close":  Column(float, Check(lambda x: x > 0), nullable=False),
        "volume": Column(float, Check(lambda x: x >= 0), nullable=False),
    })
    try:
        schema.validate(df)
        logging.info('Validação de dados (Pandera) passou com sucesso (antes das features).')
    except Exception as e:
        logging.error(f'Falha na validação de dados (Pandera): {e}')
        raise
    # Profiling antes das features
    if 'HAS_PROFILING' in globals() and HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {asset_name} - before features', minimal=True)
        profile_path = os.path.join(DATA_BASE, 'features', f'{asset_name}_profile_before.html')
        profile.to_file(profile_path)
        logging.info(f'Relatório de qualidade salvo em {profile_path}')
    try:
        df = add_features(df)
        logging.info('Features adicionadas com sucesso.')
    except Exception as e:
        logging.error(f'Erro ao adicionar features: {e}')
        raise
    logging.info(f'Perfil após features: {profile_data(df)}')
    # Remover colunas duplicadas (mantém a primeira ocorrência)
    if df.columns.duplicated().any():
        duplicated_cols = df.columns[df.columns.duplicated()].tolist()
        logging.warning(f'Colunas duplicadas detectadas: {duplicated_cols}. Removendo duplicatas.')
        df = df.loc[:, ~df.columns.duplicated()]
    else:
        logging.info('Nenhuma coluna duplicada detectada.')

    # Remover apenas linhas onde falta preço (close, open, high, low, volume)
    required_price_cols = ['close', 'open', 'high', 'low', 'volume']
    missing_price_cols = [col for col in required_price_cols if col not in df.columns]
    if missing_price_cols:
        logging.error(f'Colunas essenciais de preço ausentes: {missing_price_cols}. Nada será salvo!')
        return
    n_before = len(df)
    df = df.dropna(subset=required_price_cols)
    n_after = len(df)
    if n_after < n_before:
        logging.warning(f'{n_before-n_after} linhas removidas por falta de preço (close, open, high, low, volume).')
    if df.empty:
        logging.error('Nenhuma linha válida após remoção de linhas sem preço. Nada será salvo!')
        return

    # Profiling após as features
    if 'HAS_PROFILING' in globals() and HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {asset_name} - after features', minimal=True)
        profile2_path = os.path.join(DATA_BASE, 'features', f'{asset_name}_profile_after.html')
        profile2.to_file(profile2_path)
        logging.info(f'Relatório de qualidade salvo em {profile2_path}')
    try:
        save_parquet(df, os.path.join(DATA_BASE, 'features', f'{asset_name}_features.parquet'))
        logging.info(f'Arquivo salvo em {os.path.join(DATA_BASE, "features", f"{asset_name}_features.parquet")}')
    except Exception as e:
        logging.error(f'Erro ao salvar arquivo de features: {e}')
        raise
def safe_process(file):
    try:
        logging.info(f'Iniciando processamento seguro para {file}')
        process_asset(file)
        logging.info(f'Processamento seguro concluído para {file}')
        return (file, None)
    except Exception as e:
        logging.error(f'Erro no processamento seguro de {file}: {e}')
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
        asset_path = os.path.join(DATA_BASE, 'features', f'{args.asset}_enriched.parquet')
        if not os.path.exists(asset_path):
            asset_path = os.path.join(DATA_BASE, 'processed', f'{args.asset}_processed.parquet')
        logging.info(f'Processando ativo individual: {args.asset}')
        process_asset(asset_path)
    else:
        # Busca arquivos *_enriched.parquet em features e *_processed.parquet em processed
        features_dir = os.path.join(DATA_BASE, 'features')
        processed_dir = os.path.join(DATA_BASE, 'processed')
        abs_features_dir = os.path.abspath(features_dir)
        abs_processed_dir = os.path.abspath(processed_dir)
        files_enriched = glob.glob(os.path.join(features_dir, '*_enriched.parquet'))
        files_processed = glob.glob(os.path.join(processed_dir, '*_processed.parquet'))
        files = files_enriched + files_processed
        logging.info(f'Buscando arquivos em: {abs_features_dir} e {abs_processed_dir}')
        logging.info(f'Arquivos encontrados: {files}')
        if not files:
            logging.warning('Nenhum arquivo *_enriched.parquet ou *_processed.parquet encontrado para processar.')
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
        logging.info('Processamento em lote finalizado.')
