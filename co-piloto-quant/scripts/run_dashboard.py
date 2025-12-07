# scripts/run_dashboard.py

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# --- Configuração de Caminhos ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

from co_piloto_quant.config import PROCESSED_DATA_PATH, BB_PERIOD

# --- Configuração da Página ---
st.set_page_config(
    page_title="Co-Piloto Quant | Pro Dashboard",
    layout="wide",
    page_icon="🦅"
)

# --- CSS Profissional (Ajustado) ---
st.markdown("""
<style>
    .stApp { background-color: #0E1117; }
    .stMetric { background-color: #262730; border-radius: 8px; padding: 10px; border: 1px solid #444; }
    /* Caixas de Texto Personalizadas */
    .personality-box {
        padding: 15px;
        border-radius: 10px;
        background-color: rgba(255, 255, 255, 0.05);
        border-left: 4px solid #3498db;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

def load_data(ticker):
    file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
    if not file_path.exists(): return None
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df

def calculate_financial_performance(df):
    """
    Simula o resultado financeiro de seguir os sinais.
    Retorna: Lucro Total (%) e Fator de Lucro.
    """
    if 'SIGNAL' not in df.columns: return 0.0, 0.0, 0
    
    # Filtra onde houve sinal (ignorando HOLD)
    trades = df[df['SIGNAL'].isin(['BUY', 'SELL'])].copy()
    
    if trades.empty: return 0.0, 0.0, 0
    
    balance = 100.0 # Começa com base 100%
    wins = 0
    losses = 0
    total_trades = 0
    
    # Simulação Simplificada: Segura por 5 dias ou até sinal oposto (simplificado para 5 dias fixos aqui)
    holding_period = 5 
    
    for date, row in trades.iterrows():
        try:
            # Pega o preço N dias depois
            idx_loc = df.index.get_loc(date)
            if idx_loc + holding_period >= len(df): continue
            
            entry = row['close']
            exit_price = df.iloc[idx_loc + holding_period]['close']
            
            if row['SIGNAL'] == 'BUY':
                r = (exit_price - entry) / entry
            else: # SELL
                r = (entry - exit_price) / entry
                
            balance *= (1 + r)
            
            if r > 0: wins += 1
            else: losses += 1
            total_trades += 1
        except:
            continue
            
    total_return_pct = (balance - 100.0)
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
    
    return total_return_pct, win_rate, total_trades

def get_asset_personality(df):
    """
    Calcula as estatísticas descritivas (DNA) do ativo.
    """
    stats = {}
    
    # 1. Personalidade do Hurst (Tendência)
    if 'Hurst_72_returns' in df.columns: # Usando o valor bruto, não o Z
        h = df['Hurst_72_returns'].dropna()
        stats['hurst_mean'] = h.mean()
        stats['hurst_current'] = h.iloc[-1]
        # Percentil: Onde o valor atual se encaixa na história?
        stats['hurst_percentile'] = h.rank(pct=True).iloc[-1] * 100 
        
    # 2. Personalidade da Volatilidade (Normalizada)
    if 'Hurst_Z' in df.columns: # Usando Z como proxy de desvio
        z = df['Hurst_Z'].dropna()
        stats['z_mean'] = z.mean() # Deve ser perto de 0
        stats['z_current'] = z.iloc[-1]
        stats['z_max'] = z.max()
        stats['z_min'] = z.min()
        
    return stats

# --- SIDEBAR: OPERACIONAL ---
st.sidebar.title("🎛️ Centro de Controle")

files = list(PROCESSED_DATA_PATH.glob("*_processed.csv"))
tickers = [f.name.replace("_processed.csv", "") for f in files]
if not tickers: st.stop()

selected_ticker = st.sidebar.selectbox("Ativo", tickers)
df = load_data(selected_ticker)
latest = df.iloc[-1]
signal = latest.get('SIGNAL', 'HOLD')

# --- Calculadora de Risco (Mantida) ---
st.sidebar.markdown("---")
st.sidebar.subheader("💰 Calculadora de Lote")
capital = st.sidebar.number_input("Capital (R$)", 10000.0, 1000000.0, 100000.0)
risk_pct = st.sidebar.slider("Risco (%)", 0.5, 5.0, 1.0)
entry_price = latest['close']
stop_loss = latest.get('STOP_LOSS', 0)

# Lógica de Stop Padrão se não houver sinal
if pd.isna(stop_loss) or stop_loss == 0:
    stop_dist_pct = 0.03 
    if signal == 'BUY': stop_loss = entry_price * (1 - stop_dist_pct)
    else: stop_loss = entry_price * (1 + stop_dist_pct)

risk_money = capital * (risk_pct / 100)
dist_price = abs(entry_price - stop_loss)
qty = int(risk_money / dist_price) if dist_price > 0 else 0
st.sidebar.info(f"Stop: R$ {stop_loss:.2f}\n\nLote: **{qty} ações**")

# --- CORPO PRINCIPAL ---
st.title(f"🦅 Pro Analysis: {selected_ticker}")

# 1. KPI DE RESULTADO (A resposta para 'Eu tive lucro?')
ret_total, win_rate, n_trades = calculate_financial_performance(df)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("Preço", f"R$ {latest['close']:.2f}")
kpi2.metric("Sinal Vigente", signal, delta="AÇÃO NECESSÁRIA" if signal != 'HOLD' else None)
# Mostra o lucro acumulado simulado
kpi3.metric("Lucro Acumulado (Simulado)", f"{ret_total:+.2f}%", f"{n_trades} trades")
kpi4.metric("Taxa de Acerto", f"{win_rate:.0f}%", "Consistência")

# 2. DNA DO ATIVO (A resposta para 'Qual o normal dele?')
stats = get_asset_personality(df)

with st.expander("🧬 DNA e Personalidade do Ativo (Análise Profunda)", expanded=True):
    col_dna1, col_dna2 = st.columns(2)
    
    with col_dna1:
        st.markdown(f"### 🌊 Tendência (Hurst)")
        h_curr = stats.get('hurst_current', 0.5)
        h_mean = stats.get('hurst_mean', 0.5)
        h_pct = stats.get('hurst_percentile', 50)
        
        st.write(f"**Valor Atual:** {h_curr:.2f}")
        st.write(f"**Média Histórica:** {h_mean:.2f}")
        
        # Interpretação
        if h_curr > h_mean + 0.05:
            msg = "🔥 **Estado: Tendência Forte.** O ativo está muito mais direcional que o normal."
        elif h_curr < h_mean - 0.05:
            msg = "🦀 **Estado: Lateralidade Extrema.** O ativo está mais 'preso' que o habitual."
        else:
            msg = "⚖️ **Estado: Normal.** Comportamento padrão para este ativo."
        st.info(msg)
        st.progress(int(h_pct)) # Barra visual de 0 a 100%
        st.caption(f"O Hurst atual é maior que {h_pct:.0f}% do histórico desse ativo.")

    with col_dna2:
        st.markdown(f"### ⚡ Anomalia (Z-Score)")
        z_curr = stats.get('z_current', 0)
        z_max = stats.get('z_max', 3)
        z_min = stats.get('z_min', -3)
        
        st.write(f"**Z-Score Atual:** {z_curr:.2f}")
        st.write(f"**Extremos Históricos:** {z_min:.2f} a {z_max:.2f}")
        
        if abs(z_curr) > 2.0:
            st.warning("⚠️ **Evento Raro!** Estamos em um desvio estatístico de 2 sigmas. Reversão ou explosão iminente.")
        else:
            st.success("✅ **Comportamento Estatístico Aceitável.** Sem anomalias graves.")

# 3. GRÁFICOS CORRIGIDOS (Eixos Separados)
fig = make_subplots(
    rows=3, cols=1, 
    shared_xaxes=True, 
    vertical_spacing=0.08, # Mais espaço entre gráficos
    row_heights=[0.6, 0.2, 0.2],
    subplot_titles=("Preço e Sinais", "Ciclo de Tendência (Hurst)", "Oscilador de Entrada (Stoch)")
)

# Grafico 1: Preço
fig.add_trace(go.Candlestick(
    x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="OHLC"
), row=1, col=1)

# Sinais (Plotados com segurança no eixo Y do preço)
buys = df[df['SIGNAL'] == 'BUY']
if not buys.empty:
    fig.add_trace(go.Scatter(
        x=buys.index, y=buys['low']*0.99, mode='markers', 
        marker=dict(symbol='triangle-up', size=12, color='#00FF00'), name="COMPRA"
    ), row=1, col=1)

sells = df[df['SIGNAL'] == 'SELL']
if not sells.empty:
    fig.add_trace(go.Scatter(
        x=sells.index, y=sells['high']*1.01, mode='markers', 
        marker=dict(symbol='triangle-down', size=12, color='#FF0000'), name="VENDA"
    ), row=1, col=1)

# Bandas (Adicionar apenas linhas, sem preenchimento pesado para limpar visual)
if f'BB_Upper_{BB_PERIOD}_0.45' in df.columns:
    fig.add_trace(go.Scatter(x=df.index, y=df[f'BB_Upper_{BB_PERIOD}_0.45'], line=dict(width=0.5, color='gray'), showlegend=False), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df[f'BB_Lower_{BB_PERIOD}_0.45'], line=dict(width=0.5, color='gray'), showlegend=False), row=1, col=1)

# Grafico 2: Hurst (Eixo Y independente garantido)
if 'Hurst_Z' in df.columns:
    fig.add_trace(go.Scatter(
        x=df.index, y=df['Hurst_Z'], line=dict(color='yellow', width=1.5), name="Hurst Z"
    ), row=2, col=1)
    fig.add_hline(y=0, line_color="white", line_dash="dot", row=2, col=1)

# Grafico 3: Estocástico
stoch_col = [c for c in df.columns if 'stoch_k' in c]
if stoch_col:
    fig.add_trace(go.Scatter(
        x=df.index, y=df[stoch_col[0]], line=dict(color='cyan', width=1.5), name="Stoch"
    ), row=3, col=1)
    fig.add_hline(y=20, line_color="green", line_dash="dash", row=3, col=1)
    fig.add_hline(y=80, line_color="red", line_dash="dash", row=3, col=1)

fig.update_layout(height=900, template="plotly_dark", margin=dict(t=30, b=10, l=10, r=10), showlegend=False)
st.plotly_chart(fig, use_container_width=True)