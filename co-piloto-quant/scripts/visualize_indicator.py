import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np


import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.indicators.williams_ad import williams_ad
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.on_balance_true_range import on_balance_true_range


def visualize(ticker: str, smooth_period: int, ifr_period: int):

   
    processed_filename = f"{ticker}_processed.csv"
    processed_filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'co_piloto_quant', 'data', 'processed', processed_filename))

    print(f"Carregando dados processados de: {processed_filepath}")

    if not os.path.exists(processed_filepath):
        print(f"ERRO: Arquivo de dados processados não encontrado em '{processed_filepath}'.")
        print(f"Execute o pipeline primeiro com: python scripts/run_pipeline.py --ticker {ticker}")
        return

   
    data = pd.read_csv(processed_filepath, index_col=0, parse_dates=True)


    if data.empty:
        print(f"O arquivo de dados para o ticker {ticker} está vazio.")
        return

    
    data.columns = [col.lower() for col in data.columns]
    
    print("Calculando o indicador Williams A/D...")

    data['wad'] = williams_ad(data)

    print("Calculando Bandas de Bollinger...")
   
    bb_period = 200
    bb_std_dev = 2.0
    bands_df = bollinger_bands(data, column='close', period=bb_period, std_devs=[bb_std_dev])
    
    data = data.join(bands_df)

    print("Calculando IFR...")
    ifr_df = calculate_ifr_tpm(data, period=ifr_period)
    data['ifr'] = ifr_df[f'IFR_{ifr_period}']

    print("Calculando On-Balance True Range...")
    obtr_df = on_balance_true_range(data)
    data['obtr'] = obtr_df['OBTR']
    
    


    print("Montando o gráfico...")
   
    fig = make_subplots(
        rows=4, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        subplot_titles=(f'Preço de {ticker}', f'Williams A/D ({smooth_period} períodos)', f'IFR ({ifr_period} períodos)', 'On-Balance True Range (OBTR)'),
        row_heights=[0.6, 0.15, 0.15, 0.15]
    )

    
    fig.add_trace(
        go.Candlestick(
            x=data.index,
            open=data['open'],
            high=data['high'],
            low=data['low'],
            close=data['close'],
            name='Preço'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data[f'BB_Upper_{bb_period}_{bb_std_dev}'],
            mode='lines',
            line=dict(width=1, color='lightgray'),
            name=f'BB Superior {bb_period}'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data[f'BB_Lower_{bb_period}_{bb_std_dev}'],
            mode='lines',
            line=dict(width=1, color='lightgray'),
            fill='tonexty', 
            fillcolor='rgba(128,128,128,0.2)',
            name=f'BB Inferior {bb_period}'
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data[f'BB_Middle_{bb_period}'],
            mode='lines',
            line=dict(dash='dash', color='blue', width=1.5),
            name=f'BB Meio {bb_period}'
        ),
        row=1, col=1
    )

   
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data['wad'],
            mode='lines',
            name='Williams A/D (Bruto)',
            line=dict(color='blue', width=1)
        ),
        row=2, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data['ifr'],
            mode='lines',
            name=f'IFR {ifr_period}',
            line=dict(color='purple', width=1)
        ),
        row=3, col=1
    )
    
    fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="red", row=3, col=1)

    # Adiciona o traço para o OBTR
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data['obtr'],
            mode='lines',
            name='OBTR',
            line=dict(color='green', width=1)
        ),
        row=4, col=1
    )

    fig.update_layout(
        title_text=f"Análise Técnica: {ticker}",
        xaxis_rangeslider_visible=False,
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1
    )
    fig.update_xaxes(title_text="Data", row=4, col=1)
    fig.update_yaxes(title_text="Preço", row=1, col=1)
    fig.update_yaxes(title_text="Williams A/D", row=2, col=1)
    fig.update_yaxes(title_text="IFR", row=3, col=1)
    fig.update_yaxes(title_text="OBTR", row=4, col=1)

    # Permite que o eixo Y de todos os subplots seja expandido/reduzido
    fig.update_yaxes(fixedrange=False)

    print("Exibindo gráfico. Feche a janela do gráfico para finalizar.")
    fig.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualizador de Indicadores Técnicos.")
    parser.add_argument("--ticker", type=str, default="PETR4.SA", help="O ticker do ativo a ser analisado (ex: PETR4.SA).")
    parser.add_argument("--smooth", type=int, default=200, help="Período da média móvel de Welles Wilder.")
    parser.add_argument("--bb_period", type=int, default=200, help="Período das Bandas de Bollinger.")
    parser.add_argument("--bb_std_dev", type=float, default=2.0, help="Desvio padrão das Bandas de Bollinger.")
    parser.add_argument("--ifr_period", type=int, default=120, help="Período do IFR.")
    parser.add_argument("--output", type=str, default=None, help="Caminho para salvar o gráfico como arquivo HTML.")
    
    args = parser.parse_args()

    visualize(
        ticker=args.ticker,
        smooth_period=args.smooth,
        ifr_period=args.ifr_period
    )
