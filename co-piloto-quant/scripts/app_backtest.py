import sys
import os
from io import BytesIO
from datetime import datetime

# Garante que o Python encontre a pasta 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import streamlit as st
import pandas as pd
import vectorbt as vbt
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Importações do projeto
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_all_available_tickers
from co_piloto_quant.config import STOCH_K_SMOOTH

# --- FUNÇÕES AUXILIARES ---
@st.cache_data
def load_available_tickers():
    """Carrega a lista de tickers disponíveis de forma cacheada."""
    return get_all_available_tickers()

def to_excel(df_parametros, df_metricas, df_trades):
    """Cria um arquivo Excel em memória com múltiplos dataframes em abas separadas."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_parametros.to_excel(writer, sheet_name='Parametros', index=False)
        df_metricas_df = df_metricas.to_frame() if isinstance(df_metricas, pd.Series) else df_metricas
        df_metricas_df.to_excel(writer, sheet_name='Metricas')
        if not df_trades.empty:
            df_trades.to_excel(writer, sheet_name='Trades', index=False)
        # Auto-ajuste da largura das colunas
        for sheet_name, current_df in {'Parametros': df_parametros, 'Metricas': df_metricas_df, 'Trades': df_trades}.items():
            if not current_df.empty:
                worksheet = writer.sheets[sheet_name]
                for idx, col_name in enumerate(current_df.columns):
                    series = pd.Series([col_name] + current_df[col_name].astype(str).tolist())
                    max_len = series.map(len).max() + 2
                    worksheet.set_column(idx, idx, max_len)
    return output.getvalue()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Laboratório Quant (Dupla Blindagem)", layout="wide")
st.title("🛡️ Estratégia Quant System TPM (Dupla Camada de Segurança)")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parâmetros de Backtest")

tickers_list = load_available_tickers()
if not tickers_list:
    st.error("Nenhum dado de ticker encontrado. Rode o pipeline de dados primeiro.")
    st.stop()

ticker = st.sidebar.selectbox("Ativo", tickers_list, index=tickers_list.index('PETR4') if 'PETR4' in tickers_list else 0)

st.sidebar.subheader("Estratégia Principal")
enable_short = st.sidebar.checkbox("Habilitar Operações Short (Venda)", value=True)
use_stoch_filter = st.sidebar.checkbox("Usar Filtro Estocástico (Exaustão)", value=True)
bb_exit_std = st.sidebar.slider("Take Profit: Banda (Desvios)", 1.0, 4.0, 2.0, 0.1)
bb_entry_std = st.sidebar.slider("Entry Zone: Banda (Desvios)", 0.1, 1.0, 0.45, 0.05)
sl_stop = st.sidebar.slider("Stop Loss Fixo (%)", 1, 20, 10, 1) / 100.0

st.sidebar.subheader("Parâmetros do Estocástico")
stoch_k_window = st.sidebar.slider("Janela %K", 5, 200, 80, 1)
stoch_d_window = st.sidebar.slider("Janela %D", 1, 20, 3, 1)

# --- FILTROS DE RISCO ---
st.sidebar.divider()
st.sidebar.subheader("🛡️ Dupla Camada de Segurança")
use_risk_filters = st.sidebar.checkbox("Ativar Filtros de Risco", value=True)
volvol_limit = st.sidebar.number_input("Limite Vol-of-Vol (Anti-Crash)", 0.010, 0.100, 0.030, 0.001, format="%.3f")
vol_raw_limit = st.sidebar.number_input("Limite Vol Pura (Anti-Turbulência)", 0.010, 0.100, 0.035, 0.001, format="%.3f")

# Opções de Filtro de Regime
st.sidebar.divider()
st.sidebar.subheader("Filtros de Regime de Mercado")
use_hurst_filter = st.sidebar.checkbox("Ativar Filtro Hurst (Tendência)", value=True)
use_entropy_filter = st.sidebar.checkbox("Ativar Filtro Entropia (Ruído)", value=True)
use_halflife_filter = st.sidebar.checkbox("Ativar Filtro Half-Life (Sustentação)", value=True)

if st.sidebar.button("RODAR SIMULAÇÃO", use_container_width=True):
    with st.spinner(f"Simulando {ticker}..."):
        df_raw = load_price_data(ticker)
        if df_raw.empty: st.error("Dados não encontrados."); st.stop()

        df = calculate_indicators(df_raw, 72, 20, 60, stoch_k_window, stoch_d_window, bb_entry_std)
        if df.empty: st.error("Erro ao calcular indicadores."); st.stop()

        close = df['close']
        returns = close.pct_change()

        # --- CÁLCULO DA DUPLA CAMADA DE RISCO ---
        vol_vol = returns.rolling(20).std().diff().abs()
        vol_raw = returns.rolling(20).std()
        
        risk_safe = pd.Series(True, index=df.index)
        if use_risk_filters:
            cond1 = vol_vol <= volvol_limit
            cond2 = vol_raw <= vol_raw_limit
            risk_safe = cond1 & cond2

        # --- LÓGICA DE TRADING ---
        regime_filter = pd.Series(True, index=df.index)
        if use_hurst_filter: regime_filter &= (df['Hurst_72_returns'] >= 0.53)
        if use_entropy_filter: regime_filter &= (df['Entropy_20'] <= 3.2)
        if use_halflife_filter: regime_filter &= (df['HalfLife_60'] >= 15)

        # Lógica Long
        regras_tecnicas_long = (close <= df[f'BB_Upper_{200}_{bb_entry_std}']) & (df['obtr'] > df['obtr_bb_middle_band'])
        if use_stoch_filter: regras_tecnicas_long &= (df[f'stoch_k_{stoch_k_window}_{STOCH_K_SMOOTH}'] < 30)
        long_entries = regras_tecnicas_long & regime_filter & risk_safe

        long_exits = (close >= df[f'BB_Upper_{200}_{bb_exit_std}'])
        if use_risk_filters: long_exits |= ~risk_safe

        # Lógica Short
        short_entries, short_exits = pd.Series(False, index=df.index), pd.Series(False, index=df.index)
        if enable_short:
            regras_tecnicas_short = (close < df['WWMA_200']) & (df['obtr'] < df['obtr_bb_middle_band'])
            if use_stoch_filter: regras_tecnicas_short &= (df[f'stoch_k_{stoch_k_window}_{STOCH_K_SMOOTH}'] > 70)
            short_entries = regras_tecnicas_short & regime_filter & risk_safe
            
            short_exits = (close <= df[f'BB_Lower_{200}_2.0'])
            if use_risk_filters: short_exits |= ~risk_safe

        if not long_entries.any() and not short_entries.any(): st.warning("Nenhum sinal de entrada foi gerado.")
        
        pf = vbt.Portfolio.from_signals(close, long_entries.fillna(False), long_exits.fillna(False), short_entries.fillna(False), short_exits.fillna(False),
                                        sl_stop=sl_stop, init_cash=100000, fees=0.0006, slippage=0.001, freq='1D')
        
        stats = pf.stats()
        st.header("Métricas de Desempenho (Dupla Blindagem)")
        c1, c2, c3, c4, c5 = st.columns([1,1,1,1,2])
        c1.metric("Retorno Total", f"{stats.get('Total Return [%]', 0):.1f}%")
        c2.metric("Win Rate", f"{stats.get('Win Rate [%]', 0):.1f}%")
        c3.metric("Sharpe Ratio", f"{stats.get('Sharpe Ratio', 0):.2f}")
        c4.metric("Max Drawdown", f"{stats.get('Max Drawdown [%]', 0):.1f}%")

        params = pd.DataFrame([{"Ativo": ticker, "VolVol Limit": volvol_limit, "RawVol Limit": vol_raw_limit, "Filtros Risco": use_risk_filters}]).T.reset_index()
        trades = pf.trades.records_readable if pf.trades.count() > 0 else pd.DataFrame()
        with c5: st.download_button("📥 Baixar Relatório (.xlsx)", to_excel(params, stats, trades), f"backtest_{ticker}.xlsx")

        # --- GRÁFICOS ---
        st.subheader("Análise Gráfica: Preço, Sinais e Risco")
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

        fig.add_trace(go.Scatter(x=df.index, y=close, name='Preço', line=dict(color='white')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index[long_entries], y=close[long_entries], mode='markers', name='Compra', marker=dict(color='cyan', symbol='triangle-up', size=12)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index[short_entries], y=close[short_entries], mode='markers', name='Venda', marker=dict(color='magenta', symbol='triangle-down', size=12)), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=vol_vol, name='Vol-of-Vol', line=dict(color='orange')), row=2, col=1)
        fig.add_hline(y=volvol_limit, line_dash="dash", line_color="orange", row=2, col=1, annotation_text="Limite VolVol")
        
        fig.add_trace(go.Scatter(x=df.index, y=vol_raw, name='Vol Pura', line=dict(color='yellow')), row=2, col=1)
        fig.add_hline(y=vol_raw_limit, line_dash="dash", line_color="yellow", row=2, col=1, annotation_text="Limite Vol Pura")
        
        if use_risk_filters:
            unsafe_periods = df.index[~risk_safe]
            for period_start in unsafe_periods:
                fig.add_vrect(x0=period_start, x1=period_start + pd.Timedelta(days=1), fillcolor="rgba(255,0,0,0.2)", layer="below", line_width=0, row=1, col=1)

        fig.update_layout(height=800, title_text=f"Análise de Risco Duplo ({ticker})", legend_title="Legenda", template="plotly_dark")
        fig.update_yaxes(title_text="Preço", row=1, col=1)
        fig.update_yaxes(title_text="Métricas de Risco", row=2, col=1)
        st.plotly_chart(fig, use_container_width=True)

        if not trades.empty:
            st.subheader("Histórico de Trades")
            st.dataframe(trades.sort_values(by='Entry Timestamp', ascending=False), use_container_width=True)
else:
    st.info("👈 Configure os parâmetros e clique em 'RODAR SIMULAÇÃO'.")