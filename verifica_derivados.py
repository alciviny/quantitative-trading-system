import pandas as pd

parquet_path = r'c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant\src\co_piloto_quant\data\features\PETR4.SA_features.parquet'

df = pd.read_parquet(parquet_path)
for col in ['vol_z', 'vol_of_vol_z']:
    if col in df.columns:
        print(f"Coluna '{col}' existe.")
        print(f"Valores não nulos: {df[col].notnull().sum()} de {len(df)} linhas.")
        print(f"Primeiros valores:")
        print(df[col].head(10))
    else:
        print(f"Coluna '{col}' não existe no arquivo.")
