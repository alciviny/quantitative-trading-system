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
        
        # Ensure df_metricas is a DataFrame before writing and mapping
        if isinstance(df_metricas, pd.Series):
            df_metricas_df = df_metricas.to_frame() # Convert Series to DataFrame
        else:
            df_metricas_df = df_metricas

        df_metricas_df.to_excel(writer, sheet_name='Metricas')
        if not df_trades.empty:
            df_trades.to_excel(writer, sheet_name='Trades', index=False)
        # Map sheet names to their corresponding dataframes for auto-adjustment
        dataframes_map = {
            'Parametros': df_parametros,
            'Metricas': df_metricas_df,
        }
        if not df_trades.empty:
            dataframes_map['Trades'] = df_trades

        # Auto-ajuste da largura das colunas
        for sheet_name, current_df in dataframes_map.items():
            worksheet = writer.sheets[sheet_name]
            if not current_df.empty and not current_df.columns.empty:
                for idx, col_name in enumerate(current_df.columns):
                    # Get data for the current column, including header
                    series = pd.Series([col_name] + current_df[col_name].astype(str).tolist())
                    max_len = series.astype(str).map(len).max() + 2 # Calculate max length
                    worksheet.set_column(idx, idx, max_len)
    processed_data = output.getvalue()
    return processed_data

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Laboratório Quant", layout="wide")
st.title("jEstratégia Quant System TPM")

# --- BARRA LATERAL ---
st.sidebar.header("⚙️ Parâmetros de Backtest")

tickers_list = load_available_tickers()
if not tickers_list:
    st.error("Nenhum dado de ticker encontrado. Rode o pipeline de dados primeiro.")
    st.stop()

ticker = st.sidebar.selectbox("Ativo", tickers_list, index=0)

# Opções de Estratégia
st.sidebar.subheader("Estratégia Principal")
enable_short = st.sidebar.checkbox("Habilitar Operações Short (Venda)", value=True)
usar_filtro_inclinacao = st.sidebar.checkbox("Exigir Inclinação da Média (Slope)", value=True)
use_stoch_filter = st.sidebar.checkbox("Usar Filtro Estocástico (Gatilho Exaustão)", value=True)
bb_exit_std = st.sidebar.slider("Take Profit (Long): Banda (Desvios)", 1.0, 4.0, 2.0, 0.1)
bb_entry_std = st.sidebar.slider("Entry Zone: Banda (Desvios)", 0.1, 1.0, 0.45, 0.05)
sl_stop = st.sidebar.slider("Stop Loss de Emergência (%)", 1, 20, 10, 1) / 100.0

st.sidebar.subheader("Parâmetros do Estocástico") # New subheader
stoch_k_window = st.sidebar.slider("Janela %K Estocástico", min_value=5, max_value=200, value=80, step=1)
stoch_d_window = st.sidebar.slider("Janela %D Estocástico", min_value=1, max_value=20, value=3, step=1)

# Opções de Filtro de Regime
st.sidebar.divider()
st.sidebar.subheader("Filtros de Regime de Mercado")
use_hurst_filter = st.sidebar.checkbox("Ativar Filtro Hurst", value=True)
use_entropy_filter = st.sidebar.checkbox("Ativar Filtro Entropia", value=True)
use_halflife_filter = st.sidebar.checkbox("Ativar Filtro Half-Life", value=True)

col1, col2 = st.sidebar.columns(2)
hurst_window = col1.number_input("Janela Hurst", min_value=10, max_value=252, value=72, step=1)
hurst_threshold = col2.number_input("Corte Hurst >=", min_value=0.0, max_value=1.0, value=0.53, step=0.01)

col3, col4 = st.sidebar.columns(2)
entropy_window = col3.number_input("Janela Entropia", min_value=5, max_value=100, value=20, step=1)
entropy_threshold = col4.number_input("Corte Entropia <=", min_value=0.0, max_value=10.0, value=3.2, step=0.1)

col5, col6 = st.sidebar.columns(2)
halflife_window = col5.number_input("Janela Half-Life", min_value=10, max_value=252, value=60, step=1)
halflife_threshold = col6.number_input("Corte Half-Life >=", min_value=0, max_value=200, value=15, step=1)


if st.sidebar.button("RODAR SIMULAÇÃO"):
    with st.spinner(f"Simulando {ticker}..."):
        # 1. Carregar Dados
        df_raw = load_price_data(ticker)
        if df_raw.empty:
            st.error("Dados não encontrados para o ativo. Rode o pipeline de dados primeiro.")
            st.stop()

        # 2. Calcular Indicadores
        try:
            df = calculate_indicators(
                df_raw,
                hurst_window=hurst_window,
                entropy_window=entropy_window,
                halflife_window=halflife_window,
                stoch_k_window=stoch_k_window,
                stoch_d_window=stoch_d_window,
                bb_entry_deviation=bb_entry_std # Passa o desvio da banda de entrada
            )
        except Exception as e:
            st.error(f"Erro ao calcular indicadores: {e}")
            st.stop()

        # Extrair séries
        close = df['close']
        open_price = df['open']
        high_price = df['high']
        low_price = df['low']
        wwma_200 = df['WWMA_200']
        obtr = df['obtr']
        obtr_mid = df['obtr_bb_middle_band']
        stoch_k = df[f'stoch_k_{stoch_k_window}_{STOCH_K_SMOOTH}']
        bb_upper_entry = df[f'BB_Upper_{200}_{bb_entry_std}']
        bb_middle = df[f'BB_Middle_{200}']
        bb_lower_entry = df[f'BB_Lower_{200}_{bb_entry_std}']

        # Cálculo da inclinação da WWMA_200
        if usar_filtro_inclinacao:
            inclinacao_positiva = wwma_200.diff(5) > 0
            inclinacao_negativa = wwma_200.diff(5) < 0
        else:
            inclinacao_positiva = pd.Series(True, index=df.index) # Não aplica filtro
            inclinacao_negativa = pd.Series(True, index=df.index) # Não aplica filtro

        # 3. Lógica de Trading
        regime_filter = pd.Series(True, index=df.index) # Start with all True

        if use_hurst_filter:
            filtro_tendencia = df[f'Hurst_{hurst_window}_returns'] >= hurst_threshold
            regime_filter &= filtro_tendencia
        if use_entropy_filter:
            filtro_caos = df[f'Entropy_{entropy_window}'] <= entropy_threshold
            regime_filter &= filtro_caos
        if use_halflife_filter:
            filtro_sustentacao = df[f'HalfLife_{halflife_window}'] >= halflife_threshold
            regime_filter &= filtro_sustentacao

        # --- LÓGICA LONG ---
        # NOVA "ZONA DE VALOR": Preço entre BB Inferior (bb_lower_entry) e BB Superior (bb_upper_entry)
        regras_tecnicas_long = ((close >= bb_lower_entry) & (close <= bb_upper_entry)) & (obtr > obtr_mid) & inclinacao_positiva

        if use_stoch_filter:
            regras_tecnicas_long &= (stoch_k < 30)
        long_entries = regras_tecnicas_long & regime_filter
        
        rolling_mean = close.rolling(window=200).mean()
        rolling_std = close.rolling(window=200).std()
        bb_upper_exit = rolling_mean + (bb_exit_std * rolling_std)
        long_exits = close >= bb_upper_exit

        # --- LÓGICA SHORT ---
        short_entries, short_exits = pd.Series(False, index=df.index), pd.Series(False, index=df.index)
        if enable_short:
            regras_tecnicas_short = (close < wwma_200) & ((close >= bb_lower_entry) & (close <= bb_middle)) & (obtr < obtr_mid) & inclinacao_negativa
            if use_stoch_filter:
                regras_tecnicas_short &= (stoch_k > 70)
            short_entries = regras_tecnicas_short & regime_filter
            bb_lower_exit = rolling_mean - (2.0 * rolling_std) # Fixo em 2.0 std para saída Short
            short_exits = close <= bb_lower_exit

        # Limpeza final
        long_entries, long_exits = long_entries.fillna(False), long_exits.fillna(False)
        short_entries, short_exits = short_entries.fillna(False), short_exits.fillna(False)

        if long_entries.sum() == 0 and short_entries.sum() == 0:
            st.warning("Nenhum sinal de entrada foi gerado com os parâmetros atuais.")
            st.stop()
        
        # 4. Execução do Backtest
        pf = vbt.Portfolio.from_signals(
            close=close, entries=long_entries, exits=long_exits,
            short_entries=short_entries, short_exits=short_exits,
            sl_stop=sl_stop, init_cash=10000, fees=0.0006, slippage=0.001, freq='1D'
        )

        # 5. Visualização e Relatório
        stats = pf.stats()
        
        st.header("Métricas de Desempenho")
        
        # --- Geração do Relatório para Download ---
        parametros_simulacao = pd.DataFrame([{
            "Ativo": ticker, "Data Simulação": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Short Habilitado": enable_short, "Filtro Estocástico": use_stoch_filter,
            "TP Long (STD)": bb_exit_std, "Stop Loss (%)": sl_stop * 100,
            "Filtro Hurst Ativo": use_hurst_filter,
            "Filtro Entropia Ativo": use_entropy_filter,
            "Filtro Half-Life Ativo": use_halflife_filter, "Janela Hurst": hurst_window,
            "Corte Hurst": hurst_threshold, "Janela Entropia": entropy_window,
            "Corte Entropia": entropy_threshold, "Janela Half-Life": halflife_window,
            "Corte Half-Life": halflife_threshold
        }]).T.reset_index()
        parametros_simulacao.columns = ["Parâmetro", "Valor"]
        
        trades_df = pf.trades.records_readable if not pf.trades.records.empty else pd.DataFrame()
        excel_data = to_excel(parametros_simulacao, stats, trades_df)

        # --- Exibição das Métricas e Botão de Download ---
        col1, col2, col3, col4, col5 = st.columns([1,1,1,1,2])
        col1.metric("Retorno Total", f"{stats.get('Total Return [%]', 0):.1f}%")
        col2.metric("Win Rate", f"{stats.get('Win Rate [%]', 0):.1f}%")
        col3.metric("Sharpe Ratio", f"{stats.get('Sharpe Ratio', 0):.2f}")
        col4.metric("Max Drawdown", f"{stats.get('Max Drawdown [%]', 0):.1f}%")
        with col5:
            st.write("") # Espaçador
            st.download_button(
                label=" Baixar Relatório em Excel",
                data=excel_data,
                file_name=f"relatorio_backtest_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.subheader("Gráfico de Operações")
        
        fig = pf.plot(settings=dict(width=None, height=600))
        
        # Adicionar as Bandas de Bollinger de Entrada ao gráfico
        fig.add_trace(go.Scatter(x=df.index, y=bb_upper_entry, mode='lines', 
                                 name=f'BB Upper ({bb_entry_std})', 
                                 line=dict(color='rgba(255, 165, 0, 0.5)', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=df.index, y=bb_middle, mode='lines', 
                                 name='BB Middle', 
                                 line=dict(color='rgba(0, 0, 255, 0.5)', width=1, dash='dot')))
        fig.add_trace(go.Scatter(x=df.index, y=bb_lower_entry, mode='lines', 
                                 name=f'BB Lower ({bb_entry_std})', 
                                 line=dict(color='rgba(255, 165, 0, 0.5)', width=1, dash='dot')))

        st.plotly_chart(fig, width='stretch')

        st.subheader("Curva de Capital (Equity)")
        equity = pf.value()
        benchmark = (close / close.iloc[0]) * 10000
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=equity.index, y=equity, mode='lines', name="Estratégia", line=dict(color='green')))
        fig2.add_trace(go.Scatter(x=benchmark.index, y=benchmark, mode='lines', name="Buy & Hold", line=dict(color='gray', dash='dot')))
        fig2.update_layout(title="Estratégia vs. Buy & Hold", yaxis_title="Valor do Portfólio ($)")
        st.plotly_chart(fig2, width='stretch')

        st.subheader("Histórico de Trades")
        if not trades_df.empty:
            st.dataframe(trades_df.sort_values(by='Entry Timestamp', ascending=False), width='stretch')
        else:
            st.info("Nenhum trade foi executado.")

else:
    st.info("👈 Configure os parâmetros na barra lateral e clique em 'RODAR SIMULAÇÃO' para começar.")