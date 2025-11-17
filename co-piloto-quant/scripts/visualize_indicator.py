import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import sys
import os

# Adiciona o diretório 'src' ao path para importação dos módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm

def visualize(
    ticker: str,
    bb_period: int,
    bb_std_dev: float,
    ifr_period: int,
    system_period: int
):
    """
    Gera e exibe um gráfico com múltiplos indicadores técnicos, incluindo o System TPM
    para OBTR e WAD.
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

    # --- 1. Cálculo dos Indicadores ---
    print("Calculando indicadores...")
    price_bands_df = bollinger_bands(data, column='close', period=bb_period, std_devs=[bb_std_dev])
    ifr_df = calculate_ifr_tpm(data, period=ifr_period)
    data = data.join([price_bands_df, ifr_df])

    # Define os desvios e cores para as bandas do sistema
    system_deviations = sorted([0.45, 1.0, 1.5, 2.0], reverse=True)
    band_colors = ['rgba(0, 255, 0, 0.2)', 'rgba(0, 255, 255, 0.2)', 'rgba(255, 255, 0, 0.2)', 'rgba(255, 0, 0, 0.2)']

    # Calcula System TPM para OBTR
    print("Calculando System TPM para OBTR...")
    obtr_system_df = calculate_system_tpm(data, indicator='obtr', period=system_period, deviations=system_deviations)
    data = data.join(obtr_system_df)

    # Calcula System TPM para WAD
    print("Calculando System TPM para WAD...")
    wad_system_df = calculate_system_tpm(data, indicator='wad', period=system_period, deviations=system_deviations)
    data = data.join(wad_system_df)

    # --- 2. Montagem do Gráfico ---
    print("Montando o gráfico...")
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            f'Preço de {ticker} com Bandas de Bollinger ({bb_period}p)',
            f'IFR ({ifr_period}p)',
            f'System TPM sobre OBTR ({system_period}p)',
            f'System TPM sobre WAD ({system_period}p)'
        ),
        row_heights=[0.55, 0.15, 0.15, 0.15]
    )

    # Subplot 1: Preço e Bandas de Bollinger
    fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], low=data['low'], close=data['close'], name='Preço'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Upper_{bb_period}_{bb_std_dev}'], mode='lines', line=dict(width=1, color='gray'), name='BB Superior'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Lower_{bb_period}_{bb_std_dev}'], mode='lines', line=dict(width=1, color='gray'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)', name='BB Inferior'), row=1, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Middle_{bb_period}'], mode='lines', line=dict(dash='dash', color='darkgray', width=1), name='BB Meio'), row=1, col=1)

    # Subplot 2: IFR
    fig.add_trace(go.Scatter(x=data.index, y=data[f'IFR_{ifr_period}'], mode='lines', name=f'IFR {ifr_period}', line=dict(color='purple', width=1.5)), row=2, col=1)
    fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="red", row=2, col=1)

    # Função auxiliar para plotar um System TPM
    def plot_system_tpm(fig, row, indicator_name):
        # Plota as bandas de fora para dentro
        for i, dev in enumerate(system_deviations):
            dev_str = str(dev).replace('.', '_')
            fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_upper_band_{dev_str}'], mode='lines', line=dict(width=0), showlegend=False), row=row, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_lower_band_{dev_str}'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor=band_colors[i], name=f'Banda {dev}', legendgroup=f'group{row}'), row=row, col=1)
        # Plota o indicador e a média
        fig.add_trace(go.Scatter(x=data.index, y=data[indicator_name], mode='lines', name=indicator_name.upper(), line=dict(color='black', width=2), legendgroup=f'group{row}'), row=row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_middle_band'], mode='lines', name='Média Central', line=dict(color='blue', width=1, dash='dash'), legendgroup=f'group{row}'), row=row, col=1)

    # Subplot 3: System TPM para OBTR
    plot_system_tpm(fig, 3, 'obtr')
    
    # Subplot 4: System TPM para WAD
    plot_system_tpm(fig, 4, 'wad')

    # --- 3. Layout e Finalização ---
    fig.update_layout(
        title_text=f"Análise Técnica Completa: {ticker}",
        xaxis_rangeslider_visible=False,
        legend_tracegroupgap=20,
    )
    fig.update_xaxes(title_text="Data", row=4, col=1)
    fig.update_yaxes(title_text="Preço", row=1, col=1)
    fig.update_yaxes(title_text="IFR", row=2, col=1)
    fig.update_yaxes(title_text="OBTR", row=3, col=1)
    fig.update_yaxes(title_text="WAD", row=4, col=1)
    fig.update_yaxes(fixedrange=False) # Permite zoom no eixo Y

    print("Exibindo gráfico. Feche a janela do gráfico para finalizar.")
    fig.show()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualizador de Indicadores Técnicos com System TPM.")
    parser.add_argument("--ticker", type=str, default="PETR4.SA", help="O ticker do ativo a ser analisado (ex: PETR4.SA).")
    parser.add_argument("--bb_period", type=int, default=200, help="Período das Bandas de Bollinger do preço.")
    parser.add_argument("--bb_std_dev", type=float, default=2.0, help="Desvio padrão das Bandas de Bollinger do preço.")
    parser.add_argument("--ifr_period", type=int, default=120, help="Período do IFR.")
    parser.add_argument("--system_period", type=int, default=200, help="Período para o cálculo do System TPM.")
    
    args = parser.parse_args()

    visualize(
        ticker=args.ticker,
        bb_period=args.bb_period,
        bb_std_dev=args.bb_std_dev,
        ifr_period=args.ifr_period,
        system_period=args.system_period
    )
