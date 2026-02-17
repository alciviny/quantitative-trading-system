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
import json
import json_log_formatter
try:
    from pandas_profiling import ProfileReport
    HAS_PROFILING = True
except ImportError:
    HAS_PROFILING = False
from src.etl import load_parquet, save_parquet
from src.regimes import detect_regimes
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
    parser = argparse.ArgumentParser(description='Pipeline de regimes parametrizado')
    parser.add_argument('--asset', required=True, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    formatter = json_log_formatter.JSONFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger("RegimesPipeline")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info(json.dumps({"event": "start_regimes", "asset": args.asset}))
    df = load_parquet(f'data/features/{args.asset}_features.parquet')
    logger.info(json.dumps({"event": "profile_before_regimes", "asset": args.asset, "profile": profile_data(df)}))
    # Profiling antes dos regimes
    if HAS_PROFILING:
        profiling_dir = Path("data/profiling")
        profiling_dir.mkdir(parents=True, exist_ok=True)
        profile = ProfileReport(df, title=f'Profile {args.asset} - before regimes', minimal=True)
        profile_path = profiling_dir / f"{args.asset}_profile_before_regimes.html"
        profile.to_file(str(profile_path))
        logger.info(json.dumps({"event": "profiling_saved", "asset": args.asset, "path": str(profile_path)}))
    # Validação profissional: checagem robusta de NaN
    if df["realized_volatility"].isnull().any():
        logging.error("Feature realized_volatility contém valores nulos! Abortando.")
        raise ValueError("Feature realized_volatility contém valores nulos!")
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "before_regimes"}))
    if HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {args.asset} - before regimes', minimal=True)
        profile.to_file(f'data/results_regimes/{args.asset}_profile_before_regimes.html')
        logging.info(f'Relatório de qualidade salvo em data/results_regimes/{args.asset}_profile_before_regimes.html')
    features = [
        'realized_volatility',
        # adicione outras features relevantes
    ]
    df = detect_regimes(df, features=features, n_states=2)
    logger.info(json.dumps({"event": "profile_after_regimes", "asset": args.asset, "profile": profile_data(df)}))
    # Profiling após regimes
    if HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {args.asset} - after regimes', minimal=True)
        profile_path2 = profiling_dir / f"{args.asset}_profile_after_regimes.html"
        profile2.to_file(str(profile_path2))
        logger.info(json.dumps({"event": "profiling_saved", "asset": args.asset, "path": str(profile_path2)}))
    if df["regime"].isnull().any():
        logging.error("Coluna regime contém valores nulos! Abortando.")
        raise ValueError("Coluna regime contém valores nulos!")
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "after_regimes"}))
    if HAS_PROFILING:
        profile2 = ProfileReport(df, title=f'Profile {args.asset} - after regimes', minimal=True)
        profile2.to_file(f'data/results_regimes/{args.asset}_profile_after_regimes.html')
        logging.info(f'Relatório de qualidade salvo em data/results_regimes/{args.asset}_profile_after_regimes.html')
    save_parquet(df, f'data/results_regimes/{args.asset}_regimes_hmm.parquet')
    logger.info(json.dumps({"event": "regimes_saved", "asset": args.asset, "path": f"data/results_regimes/{args.asset}_regimes_hmm.parquet"}))
