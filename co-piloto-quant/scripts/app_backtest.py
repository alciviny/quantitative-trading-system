import sys
import os

# --- CORREÇÃO DE IMPORTAÇÃO ---
# Garante que o Python encontre a pasta 'src' onde está o co_piloto_quant
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import streamlit as st
import pandas as pd
import vectorbt as vbt
import plotly.graph_objects as go

# Importações do seu projeto
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_all_available_tickers

# --- FUNÇÃO CACHEADA PARA CARREGAR TICKERS ---
@st.cache_data
def load_available_tickers():
    """Carrega a lista de tickers do banco de dados e a mantém em cache."""
    return get_all_available_tickers()

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Laboratório de Backtest", layout="wide")
st.title("🧪 Laboratório de Estratégia Quant (System TPM)")

# --- BARRA LATERAL (CONTROLES) ---
st.sidebar.header("⚙️ Parâmetros da Estratégia")

# Carrega a lista de tickers disponíveis
tickers_list = load_available_tickers()

if not tickers_list:
    st.sidebar.error("Nenhum ativo encontrado no banco de dados. Rode o 'run_scanner.py' primeiro.")
    st.stop() # Interrompe a execução do app se não houver tickers

# Seletor de Ativo
ticker = st.sidebar.selectbox("Selecione o Ativo", tickers_list)

# O filtro Hurst foi desabilitado permanentemente para focar nos sinais técnicos.
st.sidebar.info("O filtro de regime (Hurst) foi removido.")

bb_exit_std = st.sidebar.slider("Saída: Bandas Bollinger (Desvios)", 1.0, 3.0, 1.5, 0.1)
stop_loss_pct = st.sidebar.slider("Stop Loss (%)", 1, 20, 10, 1) / 100.0

# Botão para Rodar
if st.sidebar.button("RODAR SIMULAÇÃO"):
    with st.spinner(f"Processando {ticker}..."):
        # 1. Carregar Dados
        df_raw = load_price_data(ticker)
        
        if df_raw.empty:
            st.error(f"Sem dados para {ticker} no banco de dados. Tente rodar o scanner primeiro.")
        else:
            # 2. Calcular Indicadores (Hurst, Entropia, etc.)
            try:
                df = calculate_indicators(df_raw)
            except Exception as e:
                st.error(f"Erro ao calcular indicadores: {e}")
                st.stop()
            
            if df.empty:
                st.warning("Dados insuficientes para cálculo de indicadores.")
                st.stop()

            # --- LÓGICA VETORIZADA ---
            
                        # Filtro de Regime (Hurst) foi desabilitado.
            is_trending = True
            
            # Fallback seguro para Entropia
            if 'Entropy_20' in df.columns:
                is_orderly = df['Entropy_20'] < 3.2 
            else:
                is_orderly = True

            # Regras Técnicas (Setup de Compra)
            tendencia_alta = df['close'] > df['WWMA_200']
            
            # Preço dentro da banda de consolidação (1.0 desvio)
            bb_upper_1 = df.get(f'BB_Upper_{200}_1.0', df['close'] * 1.1)
            bb_lower_1 = df.get(f'BB_Lower_{200}_1.0', df['close'] * 0.9)
            preco_dentro_base = (df['close'] <= bb_upper_1) & (df['close'] >= bb_lower_1)
            
            # Fluxo (OBTR ou WAD acima da média)
            obtr_mid = df.get('obtr_bb_middle_band', 0)
            wad_mid = df.get('wad_bb_middle_band', 0)
            fluxo_alta = (df['obtr'] > obtr_mid) | (df['wad'] > wad_mid)
            
            # Sinal Final de Entrada
            entries = tendencia_alta & preco_dentro_base & fluxo_alta & is_orderly
            
            # --- CORREÇÃO: CÁLCULO DE SAÍDA VIA PANDAS ---
            # Substitui o vbt.BBANDS que estava falhando no Python 3.13
            rolling_mean = df['close'].rolling(window=200).mean()
            rolling_std = df['close'].rolling(window=200).std()
            bb_upper_exit = rolling_mean + (bb_exit_std * rolling_std)
            
            # Sinal de Saída (Take Profit Dinâmico)
            exits = df['close'] >= bb_upper_exit

            # Limpeza de NaNs
            entries = entries.fillna(False)
            exits = exits.fillna(False)

            if entries.sum() == 0:
                st.warning("Nenhum sinal de entrada encontrado com estes parâmetros.")
            else:
                # 3. Executar VectorBT
                pf = vbt.Portfolio.from_signals(
                    close=df['close'],
                    entries=entries,
                    exits=exits,
                    sl_stop=stop_loss_pct,
                    init_cash=10000,
                    fees=0.0006,    # Taxas B3
                    slippage=0.001, # Slippage
                    freq='1D'
                )

                # --- RESULTADOS VISUAIS ---
                
                # Métricas Principais (KPIs)
                stats = pf.stats()
                
                kpi1, kpi2, kpi3, kpi4 = st.columns(4)
                kpi1.metric("Retorno Total", f"{stats['Total Return [%]']:.1f}%")
                kpi2.metric("Win Rate", f"{stats['Win Rate [%]']:.1f}%")
                kpi3.metric("Sharpe Ratio", f"{stats['Sharpe Ratio']:.2f}")
                kpi4.metric("Max Drawdown", f"{stats['Max Drawdown [%]']:.1f}%")

                # Gráfico Interativo
                st.subheader("Gráfico de Operações")
                # VectorBT tem integração nativa com Plotly
                fig = pf.plot(settings=dict(width=None, height=600))
                st.plotly_chart(fig, use_container_width=True)

                # Tabela de Trades
                st.subheader("Diário de Trades")
                trades = pf.trades.records_readable
                st.dataframe(trades.sort_values(by='Entry Timestamp', ascending=False), use_container_width=True)

                # Comparação com Benchmark
                st.subheader("Curva de Equity vs Benchmark (Buy & Hold)")
                equity_curve = pf.value()
                # Normaliza o Benchmark para começar com o mesmo valor inicial (10.000)
                benchmark_curve = (df['close'] / df['close'].iloc[0]) * 10000
                
                fig_compare = go.Figure()
                fig_compare.add_trace(go.Scatter(x=equity_curve.index, y=equity_curve, name='Estratégia (System TPM)', line=dict(color='green', width=2)))
                fig_compare.add_trace(go.Scatter(x=benchmark_curve.index, y=benchmark_curve, name=f'Benchmark ({ticker})', line=dict(dash='dot', color='gray')))
                
                fig_compare.update_layout(
                    title="Performance Comparativa", 
                    yaxis_title="Capital (R$)",
                    xaxis_title="Data",
                    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
                )
                st.plotly_chart(fig_compare, use_container_width=True)

else:
    st.info("👈 Ajuste os parâmetros na barra lateral e clique em RODAR SIMULAÇÃO.")