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

# --- NOVAS IMPORTAÇÕES ---
from src.co_piloto_quant.data.data_manager import data_manager
from src.co_piloto_quant.indicators.names import IndicatorNames


# --- Configuração da Página ---
st.set_page_config(
    layout="wide",
    page_title="Dashboard de Análise Quant",
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


# --- FUNÇÕES DE CARGA DE DADOS ---

@st.cache_data
def get_log_files(log_dir):
    """Encontra todos os arquivos de log .parquet de backtest."""
    files = glob.glob(os.path.join(log_dir, "*.parquet"))
    if not files:
        return {}
    return {os.path.basename(f).replace("_best_scenario.parquet", ""): f for f in files}

@st.cache_data
def load_backtest_data(file_path):
    """Carrega os dados de um arquivo de log de backtest."""
    return pd.read_parquet(file_path)

@st.cache_data
def load_dna_data_from_manager(ticker):
    """Carrega dados de preço e indicadores (DNA) usando o DataManager."""
    # O DataManager utiliza seu próprio cache (LRU), mas o cache do Streamlit
    # previne re-execuções desnecessárias dentro do mesmo script run.
    return data_manager.get_data(ticker)


# --- FUNÇÕES DE ANÁLISE E PLOT (BACKTEST) ---

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
    """Cria o gráfico mestre de análise forense com 4 painéis."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Preço, Sinais e Regimes de Volatilidade", "Regime Ratio (Volatilidade)", "Stochastic Weight (Convicção)", "Drawdown Acumulado")
    )
    # ... (código do gráfico forense mantido igual)
    # --- Painel 1: Preço ---
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço", showlegend=False), row=1, col=1)
    bb_std = df['param_bb_std'].iloc[0]
    bb_bands = vbt.BBANDS.run(df['close'], window=20, alpha=bb_std)
    fig.add_trace(go.Scatter(x=df.index, y=bb_bands.upper, mode='lines', line=dict(width=0.8, color='rgba(150, 150, 150, 0.8)'), name='BB Upper'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=bb_bands.lower, mode='lines', line=dict(width=0.8, color='rgba(150, 150, 150, 0.8)'), fill='tonexty', fillcolor='rgba(150, 150, 150, 0.1)', name='BB Lower'), row=1, col=1)
    entry_points = df.index[df['signal_entry']]
    exit_points = df.index[df['signal_exit']]
    fig.add_trace(go.Scatter(x=entry_points, y=df.loc[entry_points, 'low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', color='#00FF00', size=10), name='Compra'), row=1, col=1)
    fig.add_trace(go.Scatter(x=exit_points, y=df.loc[exit_points, 'high'] * 1.02, mode='markers', marker=dict(symbol='triangle-down', color='#FF0000', size=10), name='Venda'), row=1, col=1)
    vol_threshold = df['param_vol_threshold'].iloc[0]
    in_chaos = df['feat_regime_ratio'] > vol_threshold
    df['chaos_block'] = (in_chaos.diff(1) != 0).astype('int').cumsum()
    chaos_periods = df.groupby('chaos_block').filter(lambda x: x['feat_regime_ratio'].iloc[0] > vol_threshold)
    for _, block in chaos_periods.groupby('chaos_block'):
        fig.add_vrect(x0=block.index[0], x1=block.index[-1], fillcolor="rgba(255, 0, 0, 0.15)", layer="below", line_width=0, row=1, col=1)
    # --- Painel 2: Regime Ratio ---
    fig.add_trace(go.Scatter(x=df.index, y=df['feat_regime_ratio'], mode='lines', line=dict(color='orange', width=1.5), name='Regime Ratio'), row=2, col=1)
    fig.add_hline(y=vol_threshold, line=dict(color='white', dash='dash', width=1), row=2, col=1)
    # --- Painel 3: Stochastic Weight ---
    fig.add_trace(go.Scatter(x=df.index, y=df['feat_stoch_weight'], mode='lines', fill='tozeroy', line=dict(color='cyan', width=1.5), name='Stoch Weight'), row=3, col=1)
    # --- Painel 4: Drawdown ---
    drawdown = pf.drawdowns.drawdown
    fig.add_trace(go.Scatter(x=drawdown.index, y=drawdown, mode='lines', fill='tozeroy', line=dict(color='red', width=1.5), name='Drawdown'), row=4, col=1)

    fig.update_layout(height=800, template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10), showlegend=False, xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Preço (R$)", row=1, col=1); fig.update_yaxes(title_text="Ratio", row=2, col=1); fig.update_yaxes(title_text="Peso", row=3, col=1); fig.update_yaxes(title_text="DD (%)", tickformat=".2%", row=4, col=1)
    return fig

# --- FUNÇÃO DE PLOT (DNA) ---
def plot_dna_chart(df):
    """Cria o gráfico para visualizar os indicadores de DNA do ativo."""
    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
        row_heights=[0.55, 0.15, 0.15, 0.15],
        subplot_titles=("Preço", "Expoente de Hurst (Tendência vs Reversão)", "Entropia (Complexidade)", "Half-Life (Memória)")
    )
    # --- Painel 1: Preço ---
    fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Preço"), row=1, col=1)
    
    # --- Indicadores (se existirem) ---
    hurst_col = IndicatorNames.hurst(72, 'returns')
    entropy_col = IndicatorNames.entropy(20)
    halflife_col = 'half_life_60'
    
    if hurst_col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[hurst_col], name='Hurst', line=dict(color='cyan')), row=2, col=1)
        fig.add_hline(y=0.5, line=dict(color='white', dash='dash', width=1), row=2, col=1)
    
    if entropy_col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[entropy_col], name='Entropy', line=dict(color='magenta')), row=3, col=1)
        
    if halflife_col in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df[halflife_col], name='Half-Life', line=dict(color='yellow')), row=4, col=1)

    fig.update_layout(height=800, template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10), showlegend=False, xaxis_rangeslider_visible=False)
    fig.update_yaxes(title_text="Preço (R$)", row=1, col=1); fig.update_yaxes(title_text="Hurst", row=2, col=1); fig.update_yaxes(title_text="Entropia", row=3, col=1); fig.update_yaxes(title_text="Half-Life (dias)", row=4, col=1)
    return fig


# --- Início do App ---
st.title("🦅 Dashboard de Análise Quant")
log_dir = "src/co_piloto_quant/data/strategy_logs"
log_files = get_log_files(log_dir)

if not log_files:
    st.warning(f"Nenhum arquivo de log de backtest encontrado em '{log_dir}'. A aba 'Análise Forense' estará desabilitada.")
    # Permite que o app continue para a aba de DNA
    ticker_list = ["PETR4.SA", "VALE3.SA", "ITUB4.SA"] # Fallback
else:
    ticker_list = list(log_files.keys())

# --- Sidebar ---
st.sidebar.header("Seleção de Ativo")
selected_ticker = st.sidebar.selectbox("Selecione o Ativo para Análise", options=ticker_list)

# --- Abas Principais ---
tab1, tab2, tab3 = st.tabs(["🔎 Análise Forense (Backtest)", "🧬 Personalidade do Ativo (Backtest)", "📈 Indicadores de DNA (Cache)"])

# --- Aba 1: Análise Forense (Lógica Antiga) ---
with tab1:
    if selected_ticker not in log_files:
        st.info("Nenhum dado de backtest para este ativo. Selecione um ativo com log disponível para ver a análise forense.")
    else:
        df_backtest = load_backtest_data(log_files[selected_ticker])
        pf = run_forensic_backtest(df_backtest)
        
        st.subheader(f"Análise Gráfica Detalhada: {selected_ticker}")
        forensic_chart = plot_forensic_chart(df_backtest, pf)
        st.plotly_chart(forensic_chart, use_container_width=True)
        
        # Preenche KPIs na sidebar com dados do backtest
        stats = pf.stats()
        st.sidebar.header("Métricas de Performance (Backtest)")
        kpi1, kpi2 = st.sidebar.columns(2)
        kpi1.metric("Retorno Total", f"{stats['Total Return [%]']:.2f}%")
        kpi2.metric("Sharpe Ratio", f"{stats['Sharpe Ratio']:.2f}" if not np.isinf(stats['Sharpe Ratio']) else "N/A")
        kpi3, kpi4 = st.sidebar.columns(2)
        kpi3.metric("Max Drawdown", f"{stats['Max Drawdown [%]']:.2f}%")
        kpi4.metric("Taxa de Acerto", f"{stats['Win Rate [%]']:.2f}%")
        st.sidebar.header("Parâmetros Otimizados")
        kpi5, kpi6 = st.sidebar.columns(2)
        kpi5.metric("BB Std Dev", f"{df_backtest['param_bb_std'].iloc[0]:.2f}")
        kpi6.metric("Vol Threshold", f"{df_backtest['param_vol_threshold'].iloc[0]:.2f}")


# --- Aba 2: Personalidade do Ativo (Lógica Antiga) ---
with tab2:
    if selected_ticker not in log_files:
        st.info("Nenhum dado de backtest para este ativo. Selecione um ativo com log disponível para ver a análise de personalidade.")
    else:
        df_backtest = load_backtest_data(log_files[selected_ticker]) # Recarrega para escopo limpo
        pf = run_forensic_backtest(df_backtest)
        trades_df = get_trade_entry_features(pf.trades.records_readable, df_backtest)
        
        st.subheader("Análise Estatística dos Trades do Backtest")
        if trades_df.empty:
            st.info("Nenhum trade realizado para este ativo no período analisado.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                # ... (código da scatter plot mantido igual) ...
                st.write("**Resultado vs. Regime de Volatilidade**")
                scatter_fig = go.Figure(go.Scatter(x=trades_df['feat_regime_ratio'], y=trades_df['Return [%]'], mode='markers', marker=dict(color=trades_df['Return [%]'], colorscale='RdYlGn', showscale=True, cmin=-trades_df['Return [%]'].abs().max(), cmax=trades_df['Return [%]'].abs().max())))
                scatter_fig.add_vline(x=df_backtest['param_vol_threshold'].iloc[0], line=dict(color='white', dash='dash', width=1))
                scatter_fig.update_layout(template="plotly_dark", title_text="Cada ponto é um trade", xaxis_title="Regime Ratio (no momento da entrada)", yaxis_title="Retorno do Trade (%)")
                st.plotly_chart(scatter_fig, use_container_width=True)
            with col2:
                # ... (código do histograma mantido igual) ...
                st.write("**Distribuição dos Retornos dos Trades**")
                hist_fig = go.Figure(go.Histogram(x=trades_df['Return [%]'], marker_color='lightblue', nbinsx=30))
                hist_fig.update_layout(template="plotly_dark", title_text="Frequência dos Resultados", xaxis_title="Retorno do Trade (%)", yaxis_title="Número de Trades")
                st.plotly_chart(hist_fig, use_container_width=True)

# --- Aba 3: DNA do Ativo (Nova Lógica com DataManager) ---
with tab3:
    st.subheader(f"Análise de Indicadores de DNA: {selected_ticker}")
    st.info("Estes dados são carregados usando o DataManager, aproveitando o cache centralizado do sistema. Os indicadores são calculados e salvos pelo script `build_dna_b3.py`.")
    
    df_dna = load_dna_data_from_manager(selected_ticker)
    
    if df_dna.empty:
        st.warning("Não foi possível carregar os dados pelo DataManager. Execute o script `build_dna_b3.py` para calcular e salvar os indicadores.")
    else:
        dna_chart = plot_dna_chart(df_dna)
        st.plotly_chart(dna_chart, use_container_width=True)
        
        # Exibe as últimas métricas de DNA
        st.sidebar.header("Métricas de DNA (Hoje)")
        
        hurst_col = IndicatorNames.hurst(72, 'returns')
        entropy_col = IndicatorNames.entropy(20)
        halflife_col = 'half_life_60'

        latest_hurst = df_dna[hurst_col].iloc[-1] if hurst_col in df_dna.columns else "N/A"
        latest_entropy = df_dna[entropy_col].iloc[-1] if entropy_col in df_dna.columns else "N/A"
        latest_hl = df_dna[halflife_col].iloc[-1] if halflife_col in df_dna.columns else "N/A"

        st.sidebar.metric("Hurst (72p)", f"{latest_hurst:.3f}" if isinstance(latest_hurst, (int, float)) else "N/A")
        st.sidebar.metric("Entropia (20p)", f"{latest_entropy:.3f}" if isinstance(latest_entropy, (int, float)) else "N/A")
        st.sidebar.metric("Half-Life (60p)", f"{latest_hl:.1f} dias" if isinstance(latest_hl, (int, float)) else "N/A")

# --- Footer na Sidebar ---
st.sidebar.markdown("---")
st.sidebar.markdown("Co-Piloto Quant | Refatoração para DataManager concluída.")
