import sys
from pathlib import Path
import pandas as pd

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from co_piloto_quant.config import PROCESSED_DIR

ml_ready = PROCESSED_DIR
# O nome do arquivo agora é PETR4_SA.parquet, conforme o novo padrão
pq_file = ml_ready / 'PETR4_SA.parquet'

if pq_file.exists():
    df = pd.read_parquet(pq_file)
    print(f'Shape: {df.shape}')
    # O Parquet não tem um índice nomeado por padrão como o CSV
    # print(f'Index: {df.index.name}') 
    print(f'Columns: {list(df.columns)}')
    print(f'\nFirst 5 rows:')
    print(df.head())
    print(f'\nData types:')
    # Mostra os tipos de todas as colunas
    with pd.option_context('display.max_rows', None):
        print(df.dtypes)
else:
    print(f"Arquivo não encontrado em: {pq_file}")
    print("Verifique se o script 'build_ml_dataset.py' foi executado com sucesso.")
