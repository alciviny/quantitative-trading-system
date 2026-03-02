import pandas as pd
from regime_engine.pipeline.main import run_pipeline

# Caminho do arquivo de features atualizado
parquet_path = r'c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant\src\co_piloto_quant\data\features\PETR4.SA_features.parquet'

df = pd.read_parquet(parquet_path)
df.columns = [col.lower() for col in df.columns]  # Normaliza nomes para o pipeline
resultados = run_pipeline(df)
print(resultados)
# Exporta resultados para CSV na pasta results_regimes
resultados.to_csv(r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes.csv', index=True)
print('Arquivo resultados_regimes.csv salvo em results_regimes.')
