import sys
import os

# Garante que o Python encontre a pasta 'src'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import streamlit as st
import pandas as pd
import vectorbt as vbt
import plotly.graph_objects as go

# Importações do projeto
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_all_available_tickers

# --- FUNÇÃO CACHEADA ---
@st.cache_data
def load_available_tickers():
    return get_all_available_tickers()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Laboratório Quant", layout="wide")
st.title("🧪 Laboratório de Estratégia Quant (System TPM)")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parâmetros")

tickers_list = load_available_tickers()
if not tickers_list:
    st.error("Sem dados. Rode o scanner primeiro.")
    st.stop()

ticker = st.sidebar.selectbox("Ativo", tickers_list, index=0)

# Opções de Estratégia
enable_short = st.sidebar.checkbox("Habilitar Operações Short (Venda)", value=True)
use_stoch = st.sidebar.checkbox("Usar Filtro Estocástico (Pullback)", value=True)

# Sliders de Gestão de Risco
st.sidebar.divider()
bb_exit_std = st.sidebar.slider("Take Profit: Banda (Desvios)", 1.0, 3.0, 1.5, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss de Emergência (%)", 1, 20, 10, 1) / 100.0

if st.sidebar.button("RODAR SIMULAÇÃO"):
    with st.spinner(f"Simulando {ticker}..."):
        # 1. Dados
        df_raw = load_price_data(ticker)
        if df_raw.empty:
            st.error("Dados vazios.")
            st.stop()
            
        try:
            df = calculate_indicators(df_raw)
        except Exception as e:
            st.error(f"Erro indicadores: {e}")
            st.stop()

        # --- LÓGICA UNIFICADA (Idêntica ao run_backtest.py) ---
        
        # Filtros Globais
        is_orderly = True
        if 'Entropy_20' in df.columns:
            is_orderly = df['Entropy_20'] < 3.2

        # ---------------------------
        # LÓGICA LONG (COMPRA)
        # ---------------------------
        tendencia_alta = df['close'] > df['WWMA_200']
        
        # Entrada: Preço na metade superior da banda (Pullback na alta)
        bb_upper_045 = df.get(f'BB_Upper_{200}_0.45', df['close'])
        bb_middle = df.get(f'BB_Middle_{200}', df['close'])
        
        # Regra de Pullback: Preço recuou para a zona "morna" (entre meio e 0.45)
        preco_zona_compra = (df['close'] <= bb_upper_045) & (df['close'] >= bb_middle)
        
        # Fluxo
        obtr_mid = df.get('obtr_bb_middle_band', -999999)
        wad_mid = df.get('wad_bb_middle_band', -999999)
        fluxo_alta = (df['obtr'] > obtr_mid) | (df['wad'] > wad_mid)
        
        entries = tendencia_alta & preco_zona_compra & fluxo_alta & is_orderly
        
        # Filtro Estocástico (Opcional)
        if use_stoch:
            stoch_col = 'stoch_k_80_3'
            if stoch_col in df.columns:
                entries = entries & (df[stoch_col] < 30)
        
        # Saída Long (Take Profit Dinâmico na Banda)
        # Cálculo Pandas para compatibilidade Python 3.13
        rolling_mean = df['close'].rolling(window=200).mean()
        rolling_std = df['close'].rolling(window=200).std()
        
        bb_upper_exit = rolling_mean + (bb_exit_std * rolling_std)
        exits = df['close'] >= bb_upper_exit

        # ---------------------------
        # LÓGICA SHORT (VENDA)
        # ---------------------------
        short_entries = pd.Series(False, index=df.index)
        short_exits = pd.Series(False, index=df.index)

        if enable_short:
            tendencia_baixa = df['close'] < df['WWMA_200']
            
            # Entrada Short: Metade inferior da banda
            bb_lower_045 = df.get(f'BB_Lower_{200}_0.45', df['close'])
            preco_zona_venda = (df['close'] >= bb_lower_045) & (df['close'] <= bb_middle)
            
            fluxo_baixa = (df['obtr'] < obtr_mid) | (df['wad'] < wad_mid)
            
            short_entries = tendencia_baixa & preco_zona_venda & fluxo_baixa & is_orderly
            
            if use_stoch and 'stoch_k_80_3' in df.columns:
                short_entries = short_entries & (df['stoch_k_80_3'] > 70)
            
            # Saída Short (Take Profit na Banda Inferior)
            bb_lower_exit = rolling_mean - (bb_exit_std * rolling_std)
            short_exits = df['close'] <= bb_lower_exit

        # Limpeza
        entries = entries.fillna(False)
        exits = exits.fillna(False)
        short_entries = short_entries.fillna(False)
        short_exits = short_exits.fillna(False)

        if entries.sum() == 0 and short_entries.sum() == 0:
            st.warning("Sem sinais com estes parâmetros.")
        else:
            # 3. Execução VectorBT
            pf = vbt.Portfolio.from_signals(
                close=df['close'],
                entries=entries,
                exits=exits,
                short_entries=short_entries,
                short_exits=short_exits,
                sl_stop=stop_loss_pct,  # Stop Loss de Emergência OBRIGATÓRIO
                init_cash=10000,
                fees=0.0006,
                slippage=0.001,
                freq='1D'
            )

            # --- VISUALIZAÇÃO ---
            stats = pf.stats()
            
            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Retorno Total", f"{stats['Total Return [%]']:.1f}%")
            col2.metric("Win Rate", f"{stats['Win Rate [%]']:.1f}%")
            col3.metric("Sharpe Ratio", f"{stats['Sharpe Ratio']:.2f}")
            col4.metric("Max Drawdown", f"{stats['Max Drawdown [%]']:.1f}%")

            # Gráfico
            st.subheader("Gráfico de Operações")
            fig = pf.plot(settings=dict(width=None, height=600))
            st.plotly_chart(fig, use_container_width=True)

            # Curva de Equity
            st.subheader("Evolução do Capital")
            equity = pf.value()
            benchmark = (df['close'] / df['close'].iloc[0]) * 10000
            
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(x=equity.index, y=equity, name="Estratégia", line=dict(color='green')))
            fig2.add_trace(go.Scatter(x=benchmark.index, y=benchmark, name="Buy & Hold", line=dict(color='gray', dash='dot')))
            st.plotly_chart(fig2, use_container_width=True)

            # Tabela
            st.subheader("Histórico de Trades")
            st.dataframe(pf.trades.records_readable.sort_values(by='Entry Timestamp', ascending=False), use_container_width=True)
else:
    st.info("👈 Configure e clique em RODAR SIMULAÇÃO")