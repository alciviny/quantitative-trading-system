import sys
import os
import numpy as np
import pandas as pd
import vectorbt as vbt
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ===================== CONFIGURAÇÃO DE CAMINHO =====================
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.strategies.vectorized import generate_signals_vectorized
from co_piloto_quant.universe import get_all_available_tickers
from co_piloto_quant.indicators.special.kalman_bands import KalmanBands

# ===================== CONFIG STREAMLIT =====================
st.set_page_config(
    page_title="Dashboard Co-Piloto Quant",
    page_icon="📊",
    layout="wide"
)

st.title("🚁 Co-Piloto Quant — Visualização da Estratégia")
st.markdown("Visualização **idêntica ao run_backtest.py**, sem alterar a lógica.")

# ===================== SIDEBAR =====================
st.sidebar.header("Ativo")
tickers = get_all_available_tickers()

if not tickers:
    st.error("Nenhum ticker encontrado.")
    st.stop()

ticker = st.sidebar.selectbox("Ticker", tickers)

st.sidebar.divider()
st.sidebar.header("Parâmetros da Estratégia")

kb_entry_dev = st.sidebar.slider("Kalman Entry Dev", 0.1, 2.0, 0.45, 0.05)
kb_exit_dev = st.sidebar.slider("Kalman Exit Dev", 0.5, 4.0, 2.0, 0.1)
vol_ratio_limit = st.sidebar.slider("Vol Ratio Limit", 0.5, 3.0, 1.2, 0.1)

initial_capital = st.sidebar.number_input("Capital Inicial", value=100_000)
fees = st.sidebar.number_input("Taxas (%)", value=0.06) / 100

# ===================== DADOS =====================
@st.cache_data
def load_data(ticker):
    return load_price_data(ticker)

df = load_data(ticker)

if df is None or df.empty:
    st.error("Dados vazios.")
    st.stop()

# ===================== EXECUÇÃO =====================
if st.sidebar.button("🚀 Executar Backtest", type="primary"):

    with st.spinner("Calculando estratégia..."):
        close = df['close']
        high = df['high']
        low = df['low']

        # ---------- SINAIS ----------
        entries, exits = generate_signals_vectorized(
            high=high,
            low=low,
            close=close,
            bb_dev_range=np.array([kb_entry_dev]),
            vol_max_range=np.array([vol_ratio_limit]),
            bb_exit_std_dev=kb_exit_dev
        )

        # Garantir Series 1D
        if isinstance(entries, pd.DataFrame):
            entries = entries.iloc[:, 0]
        if isinstance(exits, pd.DataFrame):
            exits = exits.iloc[:, 0]

        # ---------- STOP ADAPTATIVO ----------
        ret = close.pct_change()
        adaptive_sl = pd.Series(
            np.clip(ret.rolling(20).std() * 4, 0.03, 0.10),
            index=close.index
        )

        # ---------- PORTFÓLIO ----------
        pf = vbt.Portfolio.from_signals(
            close=close,
            entries=entries,
            exits=exits,
            sl_stop=adaptive_sl,
            init_cash=initial_capital,
            fees=fees,
            freq="1D"
        )

        pf_bh = vbt.Portfolio.from_holding(
            close,
            init_cash=initial_capital,
            fees=fees,
            freq="1D"
        )

    # ===================== MÉTRICAS =====================
    if pf.trades.count() > 0:
        stats = pf.stats(
            settings=dict(
                trades=dict(
                    profit_factor=dict(apply=False)
                )
            )
        )

        stats_bh = pf_bh.stats(
            settings=dict(
                trades=dict(
                    profit_factor=dict(apply=False)
                )
            )
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Retorno Total",
            f"{stats['Total Return [%]']:.2f}%",
            f"{stats['Total Return [%]'] - stats_bh['Total Return [%]']:.2f}% vs B&H"
        )
        col2.metric("Sharpe", f"{stats['Sharpe Ratio']:.2f}")
        col3.metric("Max Drawdown", f"{stats['Max Drawdown [%]']:.2f}%")
        col4.metric("Win Rate", f"{stats['Win Rate [%]']:.2f}%")
    else:
        st.warning("Nenhum trade executado com esses parâmetros.")

    # ===================== TABS =====================
    tab1, tab2, tab3 = st.tabs(["📈 Gráfico", "📋 Trades", "📊 Retornos"])

    # ===================== GRÁFICO =====================
    with tab1:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.7, 0.3]
        )

        fig.add_trace(
            go.Scatter(x=close.index, y=close, name="Preço", line=dict(color="white")),
            row=1, col=1
        )

        kb_entry = KalmanBands.run(close, std_dev=kb_entry_dev)
        kb_exit = KalmanBands.run(close, std_dev=kb_exit_dev)

        fig.add_trace(go.Scatter(
            x=close.index, y=kb_entry.lower,
            name="Kalman Lower", line=dict(color="green", dash="dot")
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=close.index, y=kb_exit.upper,
            name="Kalman Upper", line=dict(color="red", dash="dot")
        ), row=1, col=1)

        entry_idx = entries[entries].index
        fig.add_trace(go.Scatter(
            x=entry_idx,
            y=close.loc[entry_idx],
            mode="markers",
            marker=dict(symbol="triangle-up", size=12, color="lime"),
            name="Entrada"
        ), row=1, col=1)

        if pf.trades.count() > 0:
            exit_idx = pf.trades.exit_idx
            fig.add_trace(go.Scatter(
                x=exit_idx,
                y=close.loc[exit_idx],
                mode="markers",
                marker=dict(symbol="triangle-down", size=12, color="red"),
                name="Saída"
            ), row=1, col=1)

        vol_fast = close.pct_change().rolling(10).std()
        vol_slow = close.pct_change().rolling(60).std()
        regime = vol_fast / (vol_slow + 1e-9)

        fig.add_trace(go.Scatter(
            x=regime.index, y=regime,
            name="Vol Ratio", line=dict(color="cyan")
        ), row=2, col=1)

        fig.add_hline(
            y=vol_ratio_limit,
            line_dash="dash",
            line_color="orange",
            row=2, col=1
        )

        fig.update_layout(
            height=800,
            template="plotly_dark",
            title=f"{ticker} — Estratégia Matrix/Kalman"
        )

        st.plotly_chart(fig, use_container_width=True)

    # ===================== TRADES =====================
    with tab2:
        if pf.trades.count() > 0:
            st.dataframe(pf.trades.records_readable, use_container_width=True)
        else:
            st.info("Nenhum trade.")

    # ===================== RETORNOS MENSAIS =====================
    with tab3:
        daily_returns = pf.daily_returns()

        if daily_returns is not None and not daily_returns.empty:
            monthly_returns = daily_returns.resample("M").sum()
            st.bar_chart(monthly_returns)
        else:
            st.info("Retornos insuficientes para cálculo mensal.")

else:
    st.info("👈 Ajuste os parâmetros e execute o backtest.")
