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
from src.etl import load_parquet
from src.validation import validate_regimes
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
    parser = argparse.ArgumentParser(description='Validação quantitativa parametrizada')
    parser.add_argument('--asset', required=True, help='Nome do ativo (ex: ITUB4_SA)')
    args = parser.parse_args()
    formatter = json_log_formatter.JSONFormatter()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger = logging.getLogger("ValidatePipeline")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.info(json.dumps({"event": "start_validation", "asset": args.asset}))
    df = load_parquet(f'src/co_piloto_quant/data/results_regimes/{args.asset}_regimes_hmm.parquet')
    logger.info(json.dumps({"event": "profile_validation", "asset": args.asset, "profile": profile_data(df)}))
    # Profiling validação
    if HAS_PROFILING:
        profiling_dir = Path("src/co_piloto_quant/data/profiling")
        profiling_dir.mkdir(parents=True, exist_ok=True)
        profile = ProfileReport(df, title=f'Profile {args.asset} - validation', minimal=True)
        profile_path = profiling_dir / f"{args.asset}_profile_validation.html"
        profile.to_file(str(profile_path))
        logger.info(json.dumps({"event": "profiling_saved", "asset": args.asset, "path": str(profile_path)}))
    # Validação profissional: checagem robusta de NaN
    if df["regime"].isnull().any():
        logging.error("Coluna regime contém valores nulos! Abortando.")
        raise ValueError("Coluna regime contém valores nulos!")
    logger.info(json.dumps({"event": "validation_passed", "asset": args.asset, "stage": "validation"}))
    if HAS_PROFILING:
        profile = ProfileReport(df, title=f'Profile {args.asset} - validation', minimal=True)
        profile.to_file(f'src/co_piloto_quant/data/results_validation/{args.asset}_profile_validation.html')
        logging.info(f'Relatório de qualidade salvo em src/co_piloto_quant/data/results_validation/{args.asset}_profile_validation.html')
    stress_periods = [
        ('2020-02-15', '2020-04-15'),
        ('2022-03-01', '2022-07-01'),
    ]
    metrics = validate_regimes(df, stress_periods)
    logger.info(json.dumps({"event": "metrics", "asset": args.asset, "metrics": metrics}))
    print(metrics)
