import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_BASE = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'src', 'co_piloto_quant', 'data'))
import great_expectations as ge
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False

import argparse
import logging
import json
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False
from etl import load_parquet, save_parquet
from regimes import detect_regimes
from logging_config import setup_logging
from pathlib import Path

def profile_data(df):
    info = {
        'shape': df.shape,
        'columns': list(df.columns),
        'missing': df.isnull().sum().to_dict(),
        'dtypes': df.dtypes.astype(str).to_dict(),
    }
    return info

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Pipeline de regimes parametrizado')
    parser.add_argument('--asset', required=True, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger("RegimesPipeline")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info(json.dumps({"event": "start_regimes", "asset": args.asset}))
    df = load_parquet(os.path.join(DATA_BASE, 'features', f'{args.asset}_features.parquet'))
    logger.info(json.dumps({"event": "profile_before_regimes", "asset": args.asset, "profile": profile_data(df)}))
    # Profiling antes dos regimes
    if HAS_PROFILING:
        profiling_dir = Path(os.path.join(DATA_BASE, "profiling"))
        profiling_dir.mkdir(parents=True, exist_ok=True)
        profile = ProfileReport(df, title=f'Profile {args.asset} - before regimes', minimal=True)
        profile_path = os.path.join(DATA_BASE, 'results_regimes', f'{args.asset}_profile_before_regimes.html')
        profile.to_file(profile_path)
        logging.info(f'Relatório de qualidade salvo em {profile_path}')
    # Remoção automática das linhas com NaN em volatility_21
    n_nan = df["volatility_21"].isnull().sum()
    if n_nan > 0:
        logging.warning(f"Removendo {n_nan} linhas com NaN em volatility_21.")
        df = df.dropna(subset=["volatility_21"])
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "before_regimes"}))
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "before_regimes"}))
    if HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {args.asset} - before regimes', minimal=True)
        profile_path = os.path.join(DATA_BASE, 'results_regimes', f'{args.asset}_profile_before_regimes.html')
        profile.to_file(profile_path)
        logging.info(f'Relatório de qualidade salvo em {profile_path}')
    features = [
        'volatility_21',
        # adicione outras features relevantes
    ]
    df = detect_regimes(df, features=features, n_states=2)
    logger.info(json.dumps({"event": "profile_after_regimes", "asset": args.asset, "profile": profile_data(df)}))
    # Profiling após regimes
    if HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {args.asset} - after regimes', minimal=True)
        profile_path2 = os.path.join(DATA_BASE, 'results_regimes', f'{args.asset}_profile_after_regimes.html')
        profile2.to_file(profile_path2)
        logging.info(f'Relatório de qualidade salvo em {profile_path2}')
    if df["regime"].isnull().any():
        logging.error("Coluna regime contém valores nulos! Abortando.")
        raise ValueError("Coluna regime contém valores nulos!")
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "after_regimes"}))

    # Garante que o diretório existe
    results_dir = os.path.join(DATA_BASE, 'results_regimes')
    os.makedirs(results_dir, exist_ok=True)
    save_path = os.path.join(results_dir, f'{args.asset}_regimes_hmm.parquet')
    save_parquet(df, save_path)
    logger.info(json.dumps({"event": "regimes_saved", "asset": args.asset, "path": save_path}))
