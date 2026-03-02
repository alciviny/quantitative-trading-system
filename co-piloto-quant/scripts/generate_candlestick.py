import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt
import os
import sys

# Caminho do arquivo de dados (exemplo com AAPL)
data_path = os.path.join(
    os.path.dirname(__file__), '..', 'src', 'co_piloto_quant', 'data', 'processed', 'CMIG4.SA_processed.csv'
)
docs_dir = os.path.join(os.path.dirname(__file__), '..', 'docs')
output_path = os.path.join(docs_dir, 'candlestick.png')
output_ifr_path = os.path.join(docs_dir, 'ifr_50.png')

def main():
    # Garante que o diretório docs existe
    try:
        os.makedirs(docs_dir, exist_ok=True)
    except Exception as e:
        print(f"[ERRO] Não foi possível criar o diretório docs: {e}")
        sys.exit(1)

    try:
        df = pd.read_csv(data_path, parse_dates=['date'])
        df.set_index('date', inplace=True)
        # Extrai o nome do ativo do arquivo
        ativo_nome = os.path.basename(data_path).split('_')[0]
    except Exception as e:
        print(f"[ERRO] Falha ao ler o arquivo de dados: {e}")
        sys.exit(1)

    # Seleciona apenas os últimos 100 candles para visualização profissional
    df_candle = df.tail(100)

    # Candlestick + Bandas de Bollinger + IFR 50 como subgráfico
    bollinger = [
        mpf.make_addplot(df_candle['BB_Lower_200_2.0'], color='blue', width=1.2, panel=0),
        mpf.make_addplot(df_candle['BB_Middle_200'], color='orange', width=1.2, panel=0),
        mpf.make_addplot(df_candle['BB_Upper_200_2.0'], color='red', width=1.2, panel=0)
    ]
    # Adiciona IFR 120 como subgráfico e linha horizontal em 50
    if 'IFR_120' in df_candle.columns:
        bollinger.append(mpf.make_addplot(df_candle['IFR_120'], color='green', width=2, panel=1, ylabel='IFR 120'))
        bollinger.append(mpf.make_addplot([50]*len(df_candle), color='gray', width=1, panel=1, linestyle='--', secondary_y=False))
    try:
        mpf.plot(
            df_candle,
            type='candle',
            style=mpf.make_mpf_style(base_mpf_style='yahoo', gridstyle='-', facecolor='white', edgecolor='black'),
            addplot=bollinger,
            title=f'Candlestick + Bandas de Bollinger + IFR 120 ({ativo_nome})',
            ylabel='Preço',
            figscale=1.2,
            figratio=(16,9),
            tight_layout=True,
            savefig={"fname": output_path, "dpi": 150}
        )
        print(f"[SUCESSO] Gráfico candlestick + IFR 120 salvo em {output_path}")
    except Exception as e:
        print(f"[ERRO] Falha ao salvar gráfico candlestick: {e}")

    # Diagnóstico do IFR 120
    if 'IFR_120' in df_candle.columns:
        if df_candle['IFR_120'].isnull().all():
            print('[DIAGNÓSTICO] IFR 120 está totalmente vazio (NaN).')
        elif df_candle['IFR_120'].nunique() == 1:
            print(f'[DIAGNÓSTICO] IFR 120 está constante: {df_candle["IFR_120"].iloc[0]}')
        else:
            print('[DIAGNÓSTICO] IFR 120 possui variação.')
    else:
        print('[DIAGNÓSTICO] Coluna IFR_120 não encontrada nos dados.')

if __name__ == '__main__':
    main()
