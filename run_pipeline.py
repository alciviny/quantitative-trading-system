import pandas as pd
from regime_engine.pipeline.main import run_pipeline

# Caminho do arquivo de dados reais
csv_path = r'c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant\src\co_piloto_quant\data\processed\PETR4.SA_processed.csv'

df = pd.read_csv(csv_path)
import re
def normalize_col(col):
	col = col.lower()
	col = col.replace('halflife_60', 'half_life_60')
	col = col.replace('choppiness_14', 'choppiness_14')
	return col
df.columns = [normalize_col(col) for col in df.columns]
resultados = run_pipeline(df)
print(resultados)
