import sys
import os
import streamlit as st
import pandas as pd
import vectorbt as vbt
import plotly.graph_objects as go

# --- CORREÇÃO DE IMPORTAÇÃO ---
# Adiciona o diretório 'src' ao path para encontrar os módulos do projeto
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_all_available_tickers

@st.cache_data
def load_available_tickers():
    """Carrega e armazena em cache a lista de tickers disponíveis no banco de dados."""
    return get_all_available_tickers()

# --- CONFIGURAÇÃO DA PÁGINA STREAMLIT ---
st.set_page_config(page_title="Laboratório de Backtest (System TPM)", layout="wide")
st.title("🧪 Laboratório de Estratégia Quant (System TPM)")

# --- BARRA LATERAL (CONTROLES DA ESTRATÉGIA) ---
st.sidebar.header("⚙️ Parâmetros da Simulação")

# Carrega a lista de tickers e verifica se há algum
tickers_list = load_available_tickers()
if not tickers_list:
    st.sidebar.error("Nenhum ativo encontrado no banco. Execute 'run_scanner.py' primeiro.")
    st.stop()

# --- INPUTS DO USUÁRIO ---
ticker = st.sidebar.selectbox("Selecione o Ativo", tickers_list, help="Ativo para rodar o backtest.")
enable_short = st.sidebar.checkbox("Habilitar Operações Short", value=True, help="Permite que a estratégia opere vendido (Short).")
use_stochastic_filter = st.sidebar.checkbox("Usar Filtro Estocástico (Pullback)", value=True, help="Aplica um filtro de Estocástico para entradas em 'pullbacks'. Compra em sobrevenda e Venda em sobrecompra.")
bb_exit_std = st.sidebar.slider("Alvo de Lucro: Desvio Padrão da BB", 1.0, 3.0, 1.5, 0.1, help="Desvio padrão da Banda de Bollinger para a saída de lucro (Take Profit).")
stop_loss_pct = st.sidebar.slider("Stop Loss de Emergência (%)", 1, 25, 10, 1, help="Percentual fixo para a saída de emergência (Stop Loss).") / 100.0

# --- BOTÃO DE EXECUÇÃO ---
if st.sidebar.button("RODAR SIMULAÇÃO"):
    with st.spinner(f"Processando backtest para {ticker}..."):
        # 1. CARREGAR DADOS
        df_raw = load_price_data(ticker)
        if df_raw.empty or len(df_raw) < 250: # Aumenta a verificação para garantir dados suficientes para a WWMA_200
            st.error(f"Dados insuficientes para {ticker}. Execute o scanner ou escolha outro ativo.")
            st.stop()

        # 2. CALCULAR INDICADORES
        try:
            # Esta função deve calcular todos os indicadores necessários, incluindo WWMA, BBs, OBTR, WAD e Estocástico
            df = calculate_indicators(df_raw)
            # Garante que as colunas necessárias existem
            required_cols = ['close', 'WWMA_200', 'stoch_k_80_3', 'obtr', 'obtr_bb_middle_band', 'wad', 'wad_bb_middle_band', 'Entropy_20', 'BB_Upper_200_0.45', 'BB_Lower_200_0.45', 'BB_Middle_200']
            if not all(col in df.columns for col in required_cols):
                 st.error(f"Erro: A função 'calculate_indicators' não retornou todas as colunas necessárias. Verifique a implementação em 'src/co_piloto_quant/analysis.py'. Colunas faltando podem incluir: {set(required_cols) - set(df.columns)}")
                 st.stop()
        except Exception as e:
            st.error(f"Erro fatal ao calcular indicadores: {e}")
            st.stop()

        # 3. GERAR SINAIS DE ENTRADA E SAÍDA (LÓGICA UNIFICADA)

        # --- Filtros Comuns ---
        is_orderly = df['Entropy_20'] < 3.2 # Filtro de regime (entropia)

        # --- LÓGICA DE ENTRADA (COMPRA / LONG) ---
        tendencia_alta = df['close'] > df['WWMA_200']
        preco_na_metade_superior = (df['close'] <= df['BB_Upper_200_0.45']) & (df['close'] >= df['BB_Middle_200'])
        fluxo_alta = (df['obtr'] > df['obtr_bb_middle_band']) | (df['wad'] > df['wad_bb_middle_band'])
        
        potencial_long = tendencia_alta & preco_na_metade_superior & fluxo_alta & is_orderly
        
        # Aplica filtro estocástico se habilitado
        stoch_k_col = 'stoch_k_80_3'
        if use_stochastic_filter:
            condicao_stoch_compra = df[stoch_k_col] < 30
            entries = potencial_long & condicao_stoch_compra
        else:
            entries = potencial_long

        # --- LÓGICA DE ENTRADA (VENDA / SHORT) ---
        if enable_short:
            tendencia_baixa = df['close'] < df['WWMA_200']
            preco_na_metade_inferior = (df['close'] >= df['BB_Lower_200_0.45']) & (df['close'] <= df['BB_Middle_200'])
            fluxo_baixa = (df['obtr'] < df['obtr_bb_middle_band']) | (df['wad'] < df['wad_bb_middle_band'])
            
            potencial_short = tendencia_baixa & preco_na_metade_inferior & fluxo_baixa & is_orderly

            # Aplica filtro estocástico se habilitado
            if use_stochastic_filter:
                condicao_stoch_venda = df[stoch_k_col] > 70
                short_entries = potencial_short & condicao_stoch_venda
            else:
                short_entries = potencial_short
        else:
            short_entries = pd.Series(False, index=df.index) # Se short não estiver habilitado, todos os sinais são falsos

        # --- LÓGICA DE SAÍDA HÍBRIDA ---
        # A saída de STOP LOSS é gerenciada pelo `sl_stop` do vectorbt.
        # Aqui, definimos apenas a saída de LUCRO (Take Profit) dinâmica.

        # COMPATIBILIDADE PYTHON 3.13: Cálculo manual das bandas de saída
        rolling_mean = df['close'].rolling(window=200).mean()
        rolling_std = df['close'].rolling(window=200).std()
        
        # Saída de lucro para Long: Tocar a banda superior
        exits = df['close'] >= (rolling_mean + (bb_exit_std * rolling_std))
        
        # Saída de lucro para Short: Tocar a banda inferior
        short_exits = df['close'] <= (rolling_mean - (bb_exit_std * rolling_std))

        # Limpeza de NaNs para evitar erros no vectorbt
        entries = entries.fillna(False)
        exits = exits.fillna(False)
        short_entries = short_entries.fillna(False)
        short_exits = short_exits.fillna(False)

        # 4. EXECUTAR BACKTEST COM VECTORBT
        if entries.sum() == 0 and short_entries.sum() == 0:
            st.warning("Nenhum sinal de entrada (Compra ou Venda) foi gerado com os parâmetros atuais.")
        else:
            # Executa o portfólio usando a saída híbrida:
            # - `exits`/`short_exits` para Take Profit (banda oposta)
            # - `sl_stop` para Stop Loss de emergência (percentual fixo)
            pf = vbt.Portfolio.from_signals(
                close=df['close'],
                entries=entries,
                exits=exits,
                short_entries=short_entries,
                short_exits=short_exits,
                sl_stop=stop_loss_pct,  # ESSENCIAL: Stop loss fixo para ambas as direções
                init_cash=10000,
                fees=0.0006,        # Taxa B3 (aprox. 0.03% por ordem)
                slippage=0.001,     # Derrapagem de 0.1%
                freq='1D'           # Frequência diária
            )

            # 5. RENDERIZAR RESULTADOS
            st.header("📈 Resultados do Backtest")

            # Métricas Principais (KPIs)
            stats = pf.stats()
            kpi1, kpi2, kpi3, kpi4 = st.columns(4)
            kpi1.metric("Retorno Total", f"{stats['Total Return [%]']:.1f}%")
            kpi2.metric("Taxa de Acerto (Win Rate)", f"{stats['Win Rate [%]']:.1f}%")
            kpi3.metric("Sharpe Ratio", f"{stats['Sharpe Ratio']:.2f}")
            kpi4.metric("Drawdown Máximo", f"{stats['Max Drawdown [%]']:.1f}%")
            
            # Gráfico de Operações (Plotly)
            st.subheader("Gráfico de Operações")
            # O `pf.plot()` já plota as entradas Short (triângulo vermelho) automaticamente
            fig = pf.plot(settings=dict(width=None, height=600))
            st.plotly_chart(fig, use_container_width=True)

            # Tabela de Trades (Diário)
            st.subheader("Diário de Trades")
            # `records_readable` agora inclui a coluna 'Side' (Long/Short)
            trades = pf.trades.records_readable
            st.dataframe(trades.sort_values(by='Entry Timestamp', ascending=False), use_container_width=True)

            # Curva de Capital vs. Buy & Hold
            st.subheader("Curva de Capital vs. Benchmark (Buy & Hold)")
            equity_curve = pf.value()
            benchmark_curve = (df['close'] / df['close'].iloc[0]) * pf.init_cash
            
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
    st.info("👈 Ajuste os parâmetros na barra lateral e clique em 'RODAR SIMULAÇÃO' para começar.")
