import pandas as pd

parquet_path = r'c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant\src\co_piloto_quant\data\features\PETR4.SA_features.parquet'

df = pd.read_parquet(parquet_path)
print('Colunas do arquivo:')
for col in df.columns:
    print(col)
