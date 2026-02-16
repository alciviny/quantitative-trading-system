import pandas as pd
import sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Uso: python export_parquet_to_csv.py <arquivo_parquet>')
    sys.exit(1)

parquet_path = Path(sys.argv[1])
csv_path = parquet_path.with_suffix('.csv')

df = pd.read_parquet(parquet_path)
df.to_csv(csv_path, index=False)
print(f'Arquivo CSV salvo em: {csv_path}')
