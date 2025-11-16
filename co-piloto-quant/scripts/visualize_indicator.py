import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd


import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.indicators.williams_ad import williams_ad

def visualize(ticker: str, smooth_period: int):
    """
    Carrega dados processados de um ativo, calcula o Williams A/D e exibe um gráfico.
    """
   
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
    
    data['wad_smooth'] = williams_ad(data, smooth_period=smooth_period)

    print("Montando o gráfico...")
   
    fig = make_subplots(
        rows=2, 
        cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05,
        subplot_titles=(f'Preço de {ticker}', f'Williams A/D ({smooth_period} períodos)'),
        row_heights=[0.7, 0.3]
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
            y=data['wad_smooth'],
            mode='lines',
            name=f'W. A/D Suavizado ({smooth_period})',
            line=dict(color='orange', width=2)
        ),
        row=2, col=1
    )


    fig.update_layout(
        title_text=f"Análise Técnica: {ticker}",
        xaxis_rangeslider_visible=False, # Oculta o "mini-gráfico" de range do subplot de preço
        legend_orientation="h",
        legend_yanchor="bottom",
        legend_y=1.02,
        legend_xanchor="right",
        legend_x=1
    )
    fig.update_xaxes(title_text="Data", row=2, col=1)
    fig.update_yaxes(title_text="Preço", row=1, col=1)
    fig.update_yaxes(title_text="Williams A/D", row=2, col=1)

    print("Exibindo gráfico. Feche a janela do gráfico para finalizar.")
    fig.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualizador de Indicadores Técnicos.")
    parser.add_argument("--ticker", type=str, default="PETR4.SA", help="O ticker do ativo a ser analisado (ex: PETR4.SA).")
    parser.add_argument("--smooth", type=int, default=200, help="Período da média móvel de Welles Wilder.")
    
    args = parser.parse_args()

    visualize(
        ticker=args.ticker,
        smooth_period=args.smooth
    )
