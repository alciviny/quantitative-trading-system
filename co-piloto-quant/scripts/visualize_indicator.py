import argparse
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.on_balance_true_range import on_balance_true_range
from co_piloto_quant.indicators.williams_ad import williams_ad

# --- Funções Auxiliares de Plotagem ---

def plot_price(fig, data, params, row):
    """Plota o preço e as Bandas de Bollinger."""
    bb_period = params['bb_period']
    bb_std_dev = params['bb_std_dev']
    
    price_bands_df = bollinger_bands(data, column='close', period=bb_period, std_devs=[bb_std_dev])
    data = data.join(price_bands_df)

    fig.add_trace(go.Candlestick(x=data.index, open=data['open'], high=data['high'], low=data['low'], close=data['close'], name='Preço'), row=row, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Upper_{bb_period}_{bb_std_dev}'], mode='lines', line=dict(width=1, color='gray'), name='BB Superior'), row=row, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Lower_{bb_period}_{bb_std_dev}'], mode='lines', line=dict(width=1, color='gray'), fill='tonexty', fillcolor='rgba(128,128,128,0.1)', name='BB Inferior'), row=row, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'BB_Middle_{bb_period}'], mode='lines', line=dict(dash='dash', color='darkgray', width=1), name='BB Meio'), row=row, col=1)
    
    fig.update_yaxes(title_text="Preço", row=row, col=1)
    return data

def plot_ifr(fig, data, params, row):
    """Plota o IFR."""
    ifr_period = params['ifr_period']
    ifr_df = calculate_ifr_tpm(data, period=ifr_period)
    data = data.join(ifr_df)

    fig.add_trace(go.Scatter(x=data.index, y=data[f'IFR_{ifr_period}'], mode='lines', name=f'IFR {ifr_period}', line=dict(color='purple', width=1.5)), row=row, col=1)
    fig.add_hline(y=50, line_width=1, line_dash="dash", line_color="red", row=row, col=1)
    
    fig.update_yaxes(title_text="IFR", row=row, col=1)
    return data

def plot_system_tpm(fig, data, params, indicator_name, row):
    """Plota um indicador com as bandas do System TPM."""
    system_period = params['system_period']
    system_deviations = sorted([0.45, 1.0, 1.5, 2.0], reverse=True)
    band_colors = ['rgba(0, 255, 0, 0.2)', 'rgba(0, 255, 255, 0.2)', 'rgba(255, 255, 0, 0.2)', 'rgba(255, 0, 0, 0.2)']

    system_df = calculate_system_tpm(data, indicator=indicator_name, period=system_period, deviations=system_deviations)
    data = data.join(system_df)

    # Plota as bandas de fora para dentro
    for i, dev in enumerate(system_deviations):
        dev_str = str(dev).replace('.', '_')
        fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_upper_band_{dev_str}'], mode='lines', line=dict(width=0), showlegend=False), row=row, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_lower_band_{dev_str}'], mode='lines', line=dict(width=0), fill='tonexty', fillcolor=band_colors[i], name=f'Banda {dev}', legendgroup=f'group{row}'), row=row, col=1)
    
    # Plota o indicador e a linha central
    fig.add_trace(go.Scatter(x=data.index, y=data[indicator_name], mode='lines', name=indicator_name.upper(), line=dict(color='black', width=2), legendgroup=f'group{row}'), row=row, col=1)
    fig.add_trace(go.Scatter(x=data.index, y=data[f'{indicator_name}_bb_middle_band'], mode='lines', name='Linha Central', line=dict(color='blue', width=1, dash='dash'), legendgroup=f'group{row}'), row=row, col=1)

    fig.update_yaxes(title_text=indicator_name.upper(), row=row, col=1)
    return data

def visualize(args):
    """
    Gera e exibe um gráfico com uma seleção dinâmica de indicadores técnicos.
    """
    processed_filename = f"{args.ticker}_processed.csv"
    processed_filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src', 'co_piloto_quant', 'data', 'processed', processed_filename))

    print(f"Carregando dados processados de: {processed_filepath}")
    if not os.path.exists(processed_filepath):
        print(f"ERRO: Arquivo de dados processados não encontrado em '{processed_filepath}'.")
        print(f"Execute o pipeline primeiro com: python scripts/run_pipeline.py --ticker {args.ticker}")
        return

    data = pd.read_csv(processed_filepath, index_col=0, parse_dates=True)
    if data.empty:
        print(f"O arquivo de dados para o ticker {args.ticker} está vazio.")
        return
    data.columns = [col.lower() for col in data.columns]

    # --- Cálculos de Indicadores ---
    # Garante que os dados base para os indicadores do System TPM existam
    if 'obtr' in args.indicators:
        obtr_df = on_balance_true_range(data)
        data = data.join(obtr_df)

    if 'wad' in args.indicators:
        wad_df = williams_ad(data)
        data = data.join(wad_df)

    # --- Setup de Plotagem Dinâmica ---
    
    # Mapeia nomes de indicadores para suas funções de plotagem e títulos
    plotter_map = {
        'price': (plot_price, 'Preço & Bandas de Bollinger'),
        'ifr': (plot_ifr, 'IFR'),
        'obtr': (lambda fig, data, params, row: plot_system_tpm(fig, data, params, 'obtr', row), 'System TPM sobre OBTR'),
        'wad': (lambda fig, data, params, row: plot_system_tpm(fig, data, params, 'wad', row), 'System TPM sobre WAD'),
    }

    # Filtra apenas os indicadores solicitados
    indicators_to_plot = [ind for ind in args.indicators if ind in plotter_map]
    if not indicators_to_plot:
        print("Nenhum indicador válido selecionado para plotagem. Escolha de:", list(plotter_map.keys()))
        return

    # Cria subplots dinamicamente
    fig = make_subplots(
        rows=len(indicators_to_plot),
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=[plotter_map[ind][1] for ind in indicators_to_plot]
    )

    # Armazena todos os parâmetros em um dicionário
    params = vars(args)

    # --- Loop de Plotagem ---
    print(f"Calculando e plotando: {', '.join(indicators_to_plot)}")
    for i, indicator_name in enumerate(indicators_to_plot):
        plot_function = plotter_map[indicator_name][0]
        # Os dados são passados e retornados para carregar as colunas calculadas
        data = plot_function(fig, data, params, row=i + 1)

    # --- Layout e Finalização ---
    fig.update_layout(
        title_text=f"Análise Técnica para: {args.ticker}",
        xaxis_rangeslider_visible=False,
        legend_tracegroupgap=20,
        height=350 * len(indicators_to_plot) # Ajusta a altura com base no número de plots
    )
    fig.update_xaxes(title_text="Data", row=len(indicators_to_plot), col=1)
    fig.update_yaxes(fixedrange=False)

    print("Exibindo gráfico. Feche a janela do gráfico para finalizar.")
    fig.show()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Visualizador Flexível de Indicadores Técnicos.")
    
    # Argumentos gerais
    parser.add_argument("--ticker", type=str, default="PETR4.SA", help="O ticker do ativo a ser analisado (ex: PETR4.SA).")
    
    # Seleção de indicadores
    parser.add_argument(
        "indicators", 
        nargs='+', 
        choices=['price', 'ifr', 'obtr', 'wad'], 
        help="Uma lista de indicadores para exibir (ex: 'price obtr wad')."
    )

    # Parâmetros para os indicadores
    parser.add_argument("--bb_period", type=int, default=200, help="Período para as Bandas de Bollinger do preço.")
    parser.add_argument("--bb_std_dev", type=float, default=2.0, help="Desvio padrão para as Bandas de Bollinger do preço.")
    parser.add_argument("--ifr_period", type=int, default=120, help="Período para o IFR.")
    parser.add_argument("--system_period", type=int, default=200, help="Período para o cálculo do System TPM.")
    
    args = parser.parse_args()

    visualize(args)


    """ python scripts/visualize_indicator.py --ticker PETR4.SA price obtr wad ifr """
