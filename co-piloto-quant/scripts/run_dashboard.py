# scripts/run_dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import glob
import vectorbt as vbt
from pathlib import Path

# --- Configuração da Página ---
st.set_page_config(
    layout="wide",
    page_title="Dashboard de Análise Forense",
    initial_sidebar_state="expanded"
)

# --- Estilo ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stMetric { background-color: #262730; border-radius: 8px; padding: 10px; border: 1px solid #444; }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #262730;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #444;
    }
</style>
""", unsafe_allow_html=True)


# --- Funções Auxiliares ---

@st.cache_data
def get_log_files(log_dir):
    """Encontra todos os arquivos de log .parquet."""
    files = glob.glob(os.path.join(log_dir, "*.parquet"))
    if not files:
        return {}
    # Extrai o ticker do nome do arquivo
    return {os.path.basename(f).replace("_best_scenario.parquet", ""): f for f in files}

@st.cache_data
def load_data(file_path):
    """Carrega os dados de um arquivo parquet."""
    df = pd.read_parquet(file_path)
    return df

@st.cache_data
def run_forensic_backtest(_df):
    """Roda um backtest com vectorbt para obter performance e trades."""
    pf = vbt.Portfolio.from_signals(
        _df['close'],
        entries=_df['signal_entry'],
        exits=_df['signal_exit'],
        init_cash=100_000,
        fees=0.001,
        freq='1D'
    )
    return pf

def get_trade_entry_features(_trades_df, _feature_df):
    """Adiciona features do momento da entrada a cada trade."""
    if _trades_df.empty:
        return _trades_df
    
    entry_features = _feature_df.loc[_trades_df['Entry Timestamp'], ['feat_regime_ratio', 'feat_stoch_weight']].reset_index()
    trades_with_features = _trades_df.reset_index(drop=True).join(entry_features.set_index('index'))
    return trades_with_features.set_index('Trade Id')


def plot_forensic_chart(df, pf):
    """Cria o gráfico mestre com 4 painéis."""
    fig = make_subplots(
        rows=4, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Preço, Sinais e Regimes de Volatilidade", "Regime Ratio (Volatilidade)", "Stochastic Weight (Convicção)", "Drawdown Acumulado")
    )

    # --- Painel 1: Preço ---
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="Preço", showlegend=False
    ), row=1, col=1)

    # Bandas de Bollinger (recalculadas com base no parâmetro salvo)
    bb_std = df['param_bb_std'].iloc[0]
    bb_bands = vbt.BBANDS.run(df['close'], window=20, alpha=bb_std)
    fig.add_trace(go.Scatter(x=df.index, y=bb_bands.upper, mode='lines', line=dict(width=0.8, color='rgba(150, 150, 150, 0.8)'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_bands.lower, mode='lines', line=dict(width=0.8, color='rgba(150, 150, 150, 0.8)'), fill='tonexty', fillcolor='rgba(150, 150, 150, 0.1)', name='BB Lower'), row=1, col=1)

    # Sinais de Compra e Venda
    entry_points = df.index[df['signal_entry']]
    exit_points = df.index[df['signal_exit']]
    fig.add_trace(go.Scatter(
        x=entry_points, y=df.loc[entry_points, 'low'] * 0.98,
        mode='markers', marker=dict(symbol='triangle-up', color='#00FF00', size=10),
        name='Compra'
    ), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=exit_points, y=df.loc[exit_points, 'high'] * 1.02,
        mode='markers', marker=dict(symbol='triangle-down', color='#FF0000', size=10),
        name='Venda'
    ), row=1, col=1)

    # Fundo do Gráfico (Regimes)
    vol_threshold = df['param_vol_threshold'].iloc[0]
    in_chaos = df['feat_regime_ratio'] > vol_threshold
    
    # Encontra blocos contínuos de "caos" e "calmaria"
    df['chaos_block'] = (in_chaos.diff(1) != 0).astype('int').cumsum()
    chaos_periods = df.groupby('chaos_block').filter(lambda x: x['feat_regime_ratio'].iloc[0] > vol_threshold)
    
    for _, block in chaos_periods.groupby('chaos_block'):
        fig.add_vrect(x0=block.index[0], x1=block.index[-1], 
                      fillcolor="rgba(255, 0, 0, 0.15)", layer="below", line_width=0, row=1, col=1)

    # --- Painel 2: Regime Ratio ---
    fig.add_trace(go.Scatter(x=df.index, y=df['feat_regime_ratio'], mode='lines', line=dict(color='orange', width=1.5), name='Regime Ratio'), row=2, col=1)
    fig.add_hline(y=vol_threshold, line=dict(color='white', dash='dash', width=1), row=2, col=1)

    # --- Painel 3: Stochastic Weight ---
    fig.add_trace(go.Scatter(x=df.index, y=df['feat_stoch_weight'], mode='lines', fill='tozeroy', line=dict(color='cyan', width=1.5), name='Stoch Weight'), row=3, col=1)
    
    # --- Painel 4: Drawdown ---
    drawdown = pf.drawdowns.drawdown
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, mode='lines', fill='tozeroy', line=dict(color='red', width=1.5), name='Drawdown'), row=4, col=1)

    # Layout
    fig.update_layout(
        height=800,
        template="plotly_dark",
        margin=dict(t=30, b=10, l=10, r=10),
        showlegend=False,
        xaxis_rangeslider_visible=False
    )
    fig.update_yaxes(title_text="Preço (R$)", row=1, col=1)
    fig.update_yaxes(title_text="Ratio", row=2, col=1)
    fig.update_yaxes(title_text="Peso", row=3, col=1)
    fig.update_yaxes(title_text="DD (%)", tickformat=".2%", row=4, col=1)

    return fig

# --- Início do App ---

st.title("🦅 Dashboard de Análise Forense")

log_dir = "data/strategy_logs"
log_files = get_log_files(log_dir)

if not log_files:
    st.warning(f"Nenhum arquivo de log encontrado em '{log_dir}'. Execute o backtest primeiro (`scripts/run_backtest.py`).")
    st.stop()

# --- Sidebar ---
st.sidebar.header("Seleção de Ativo")
selected_ticker = st.sidebar.selectbox("Selecione o Ativo para Análise", options=list(log_files.keys()))

# --- Carregamento e Processamento ---
df = load_data(log_files[selected_ticker])
pf = run_forensic_backtest(df)
stats = pf.stats()
trades_df = get_trade_entry_features(pf.trades.records_readable, df)

best_bb = df['param_bb_std'].iloc[0]
best_vol = df['param_vol_threshold'].iloc[0]

# --- KPIs na Sidebar ---
st.sidebar.header("Métricas de Performance")
kpi1, kpi2 = st.sidebar.columns(2)
kpi1.metric("Retorno Total", f"{stats['Total Return [%]']:.2f}%")
kpi2.metric("Sharpe Ratio", f"{stats['Sharpe Ratio']:.2f}" if not np.isinf(stats['Sharpe Ratio']) else "N/A")

kpi3, kpi4 = st.sidebar.columns(2)
kpi3.metric("Max Drawdown", f"{stats['Max Drawdown [%]']:.2f}%")
kpi4.metric("Taxa de Acerto", f"{stats['Win Rate [%]']:.2f}%")

st.sidebar.header("Parâmetros Otimizados")
kpi5, kpi6 = st.sidebar.columns(2)
kpi5.metric("BB Std Dev", f"{best_bb:.2f}")
kpi6.metric("Vol Threshold", f"{best_vol:.2f}")

# --- Abas Principais ---
tab1, tab2 = st.tabs(["🔎 Análise Forense", "🧬 Personalidade do Ativo"])

with tab1:
    st.subheader(f"Análise Gráfica Detalhada: {selected_ticker}")
    forensic_chart = plot_forensic_chart(df, pf)
    st.plotly_chart(forensic_chart, use_container_width=True)

    st.subheader("Tabela de Trades Realizados")
    st.dataframe(trades_df)

with tab2:
    st.subheader("Análise Estatística dos Trades")
    
    if trades_df.empty:
        st.info("Nenhum trade realizado para este ativo no período analisado.")
    else:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Resultado vs. Regime de Volatilidade**")
            scatter_fig = go.Figure(go.Scatter(
                x=trades_df['feat_regime_ratio'],
                y=trades_df['Return [%]'],
                mode='markers',
                marker=dict(
                    color=trades_df['Return [%]'],
                    colorscale='RdYlGn',
                    showscale=True,
                    cmin=-trades_df['Return [%]'].abs().max(),
                    cmax=trades_df['Return [%]'].abs().max()
                )
            ))
            scatter_fig.add_vline(x=best_vol, line=dict(color='white', dash='dash', width=1))
            scatter_fig.update_layout(template="plotly_dark", title_text="Cada ponto é um trade",
                                      xaxis_title="Regime Ratio (no momento da entrada)",
                                      yaxis_title="Retorno do Trade (%)")
            st.plotly_chart(scatter_fig, use_container_width=True)

        with col2:
            st.write("**Distribuição dos Retornos dos Trades**")
            hist_fig = go.Figure(go.Histogram(
                x=trades_df['Return [%]'],
                marker_color='lightblue',
                nbinsx=30
            ))
            hist_fig.update_layout(template="plotly_dark", title_text="Frequência dos Resultados",
                                     xaxis_title="Retorno do Trade (%)",
                                     yaxis_title="Número de Trades")
            st.plotly_chart(hist_fig, use_container_width=True)
