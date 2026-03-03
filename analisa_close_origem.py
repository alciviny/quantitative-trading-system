import pandas as pd
import sys

# Caminho do arquivo processado (ajuste se necessário)
ARQUIVO = r'co-piloto-quant/src/co_piloto_quant/data/processed/VALE3.SA_processed.csv'

if len(sys.argv) > 1:
    ARQUIVO = sys.argv[1]

print(f'Analisando arquivo: {ARQUIVO}')

df = pd.read_csv(ARQUIVO)

print('\nColunas disponíveis:', df.columns.tolist())

if 'close' in df.columns:
    print('\nResumo estatístico do campo close:')
    print(df['close'].describe())
    print('\nPrimeiros 10 valores:', df['close'].head(10).values)
    print('Últimos 10 valores:', df['close'].tail(10).values)
    print('Existem valores nulos?', df['close'].isnull().any())
    print('Existem valores <= 0?', (df['close'] <= 0).any())
    print('Valores únicos (amostra):', df['close'].unique()[:10])
else:
    print("Coluna 'close' não encontrada no arquivo.")
