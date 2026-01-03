import pandas as pd
from pathlib import Path

ml_ready = Path('src/co_piloto_quant/data/ml_ready')
pq_file = ml_ready / 'PETR4.SA.parquet'

if pq_file.exists():
    df = pd.read_parquet(pq_file)
    print(f'Shape: {df.shape}')
    print(f'Index: {df.index.name}')
    print(f'Columns: {list(df.columns)}')
    print(f'\nFirst 5 rows:')
    print(df.head())
    print(f'\nData types:')
    print(df.dtypes)
else:
    print('File not found')
