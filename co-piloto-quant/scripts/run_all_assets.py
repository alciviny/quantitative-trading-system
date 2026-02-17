import subprocess
import logging
from src.logging_config import setup_logging

ASSETS = [
    'ITUB4_SA',
    'PETR4_SA',
    # Adicione outros ativos conforme necessário
]

setup_logging('pipeline_multiasset.log')

for asset in ASSETS:
    logging.info(f'Iniciando pipeline completo para {asset}')
    subprocess.run(['python', 'scripts/etl_pipeline.py', '--asset', asset], check=True)
    subprocess.run(['python', 'scripts/features_pipeline.py', '--asset', asset], check=True)
    subprocess.run(['python', 'scripts/regimes_pipeline.py', '--asset', asset], check=True)
    subprocess.run(['python', 'scripts/validate_pipeline.py', '--asset', asset], check=True)
    logging.info(f'Pipeline finalizado para {asset}')
