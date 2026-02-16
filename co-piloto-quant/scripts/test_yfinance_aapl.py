import yfinance as yf
import pandas as pd

ticker = 'AAPL'
start = '2023-01-01'
end = '2023-12-31'

print(f'Baixando dados de {ticker} de {start} até {end}...')
df = yf.download(ticker, start=start, end=end, progress=False)

print(df.head())
print(f'Linhas baixadas: {len(df)}')
if df.empty:
    print('❌ Nenhum dado retornado!')
else:
    print('✅ Dados baixados com sucesso!')
