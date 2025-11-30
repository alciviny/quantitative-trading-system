import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
from pathlib import Path

# --- Configuração de Caminhos ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

from co_piloto_quant.config import PROCESSED_DATA_PATH
from co_piloto_quant.analysis import load_processed_data, check_rules

# Importando indicadores (Reaproveitando sua lógica existente)
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
# ... outros imports
from co_piloto_quant.config import PROCESSED_DATA_PATH, STOCH_K_PERIOD, STOCH_K_SMOOTH, STOCH_D_SMOOTH

# --- Configuração da Página ---
st.set_page_config(page_title="Co-Piloto Quant Pro", layout="wide", page_icon="📊")

# --- CSS Customizado para dar ar profissional ---
st.markdown("""
<style>
    .stMetric {
        background-color: #1E1E1E;
        padding: 10px;
        border-radius: 5px;
        border: 1px solid #333;
    }
    .big-font {
        font-size: 20px !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- Barra Lateral (Controles) ---
st.sidebar.title("🎛️ Painel de Controle")

# 1. Seletor de Ativo
try:
    files = list(PROCESSED_DATA_PATH.glob("*_processed.csv"))
    tickers = [f.name.replace("_processed.csv", "") for f in files]
    if not tickers:
        st.error("Nenhum dado encontrado. Rode o pipeline primeiro.")
        st.stop()
    selected_ticker = st.sidebar.selectbox("Escolha o Ativo:", tickers)
except Exception as e:
    st.error(f"Erro ao ler arquivos: {e}")
    st.stop()

# 2. Configurações Dinâmicas (Isso o seu script antigo não tinha fácil!)
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ajuste Fino")
periodo_bb = st.sidebar.slider("Período Bollinger/Médias", 20, 300, 200)
desvio_bb = st.sidebar.number_input("Desvio Padrão", 1.0, 3.0, 2.0, 0.1)
ver_bandas_sistema = st.sidebar.checkbox("Ver Bandas de Fluxo (TPM)", value=True)

# --- Corpo Principal ---
st.title(f"📊 Análise Quantitativa: {selected_ticker}")

df = load_processed_data(selected_ticker)

if df.empty:
    st.error("Arquivo vazio.")
else:
    # Recalcula indicadores visuais baseados nos sliders (Interatividade!)
    # Nota: Estamos recalculando apenas visualmente, as regras do analysis.py usam o padrão do config
    df_visual = df.copy()
    
    # Validação de Regras (Usando o último candle)
    last_row = df.iloc[-1]
    # Aqui chamamos sua função de check_rules que já valida tudo
    regras = check_rules(last_row)

    # --- Painel de Status (Topo) ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Preço Atual", f"R$ {last_row['close']:.2f}")
    
    with col2:
        # Lógica de cor para o status
        status_compra = "SIM" if regras.get('Sinal_Compra') else "NÃO"
        cor_compra = "off" if not regras.get('Sinal_Compra') else "normal"
        st.metric("Sinal de COMPRA", status_compra, delta="Potencial Alta" if regras.get('Sinal_Compra') else None)

    with col3:
        status_venda = "SIM" if regras.get('Sinal_Venda') else "NÃO"
        st.metric("Sinal de VENDA", status_venda, delta_color="inverse", delta="-Potencial Baixa" if regras.get('Sinal_Venda') else None)

    with col4:
        squeeze = "ALERTA" if regras.get('Potencial_Squeeze') else "Normal"
        st.metric("Volatilidade", squeeze, delta="Explosão Iminente" if regras.get('Potencial_Squeeze') else None, delta_color="off")

    # --- Visualização Gráfica (Plotly) ---
 # Setup de Subplots (Preço + Fluxo + IFR + Estocástico)
    fig = make_subplots(
        rows=4, cols=1,  # <--- MUDAR PARA 4
        shared_xaxes=True, 
        vertical_spacing=0.03, 
        # Ajustando alturas: Preço maior, outros menores
        row_heights=[0.50, 0.15, 0.15, 0.20], 
        subplot_titles=("Ação do Preço & Estrutura", "Fluxo (OBTR/WAD)", "Oscilador (IFR)", "Estocástico (80,3,3)")
    )

    # 1. Gráfico de Preço (Candles)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
        name="OHLC"
    ), row=1, col=1)

    # Média Móvel (Interativa pelo Slider)
    mm_col = f'WWMA_{periodo_bb}' # Se não existir, teria que calcular, mas vamos usar a 200 fixa ou calcular on-the-fly
    # Para simplificar a visualização, vamos plotar a 200 fixa do arquivo ou calcular simples aqui
    fig.add_trace(go.Scatter(
        x=df.index, y=df['close'].ewm(span=periodo_bb).mean(), 
        line=dict(color='orange', width=2), name=f"Média {periodo_bb}"
    ), row=1, col=1)

    # Bandas de Bollinger Visuais
    if 'BB_Upper_200_2.0' in df.columns: # Usando as processadas
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Upper_200_2.0'], 
            line=dict(color='gray', width=1, dash='dot'), showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Lower_200_2.0'], 
            line=dict(color='gray', width=1, dash='dot'), name="Bollinger (Padrão)",
            fill='tonexty', fillcolor='rgba(128,128,128,0.1)'
        ), row=1, col=1)

    # 2. Gráfico de Fluxo (TPM)
    if 'obtr' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['obtr'], line=dict(color='#00FF00', width=1), name="OBTR (Fluxo)"), row=2, col=1)
        
        # Bandas do System TPM (Visualização rica que você fez no outro script)
        if ver_bandas_sistema and 'obtr_bb_upper_band_0_45' in df.columns:
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_upper_band_0_45'], line=dict(width=0), showlegend=False), row=2, col=1)
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_lower_band_0_45'], line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 255, 0, 0.1)', name="Zona de Fluxo"), row=2, col=1)




# 2. Gráfico de Fluxo (TPM)
    # --- PLOT DO OBTR ---
    if 'obtr' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['obtr'], line=dict(color='#00FF00', width=1), name="OBTR (Fluxo)"), row=2, col=1)
        
        if ver_bandas_sistema and 'obtr_bb_upper_band_0_45' in df.columns:
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_upper_band_0_45'], line=dict(width=0), showlegend=False), row=2, col=1)
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_lower_band_0_45'], line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 255, 0, 0.1)', name="Zona OBTR"), row=2, col=1)

    # --- ADICIONAR ESTE BLOCO PARA O WILLIAMS (WAD) ---
    if 'wad' in df.columns:
        # Usando uma cor diferente (ex: amarelo ou magenta) para diferenciar
        fig.add_trace(go.Scatter(x=df.index, y=df['wad'], line=dict(color='#FF00FF', width=1), name="Williams A/D"), row=2, col=1)
        
        # Opcional: Adicionar bandas do WAD se quiser visualizar também
        if ver_bandas_sistema and 'wad_bb_upper_band_0_45' in df.columns:
             fig.add_trace(go.Scatter(x=df.index, y=df['wad_bb_upper_band_0_45'], line=dict(width=0), showlegend=False), row=2, col=1)
             fig.add_trace(go.Scatter(x=df.index, y=df['wad_bb_lower_band_0_45'], line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 0, 255, 0.1)', name="Zona WAD"), row=2, col=1)





















    # 3. Gráfico de IFR
    if 'IFR_120' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['IFR_120'], line=dict(color='cyan', width=1.5), name="IFR 120"), row=3, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3, row=3, col=1)
        fig.add_hrect(y0=48, y1=52, fillcolor="white", opacity=0.1, layer="below", line_width=0, row=3, col=1)




# 4. Gráfico de Estocástico (NOVO BLOCO)
    # Monta os nomes das colunas dinamicamente baseado no config
    col_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    col_d = f'stoch_d_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}_{STOCH_D_SMOOTH}'

    if col_k in df.columns:
        # Linha K (Rápida) - Cor sólida vibrante
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col_k], 
            line=dict(color='#E377C2', width=1.5), name="Stoch %K"
        ), row=4, col=1)
        
        # Linha D (Sinal) - Tracejada
        if col_d in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_d], 
                line=dict(color='white', width=1, dash='dot'), name="Stoch %D"
            ), row=4, col=1)

        # Linhas de Referência (20 e 80)
        fig.add_hline(y=20, line_dash="dash", line_color="gray", opacity=0.5, row=4, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", opacity=0.5, row=4, col=1)
        
        # Opcional: Pintar zonas extremas
        fig.add_hrect(y0=80, y1=100, fillcolor="red", opacity=0.1, line_width=0, row=4, col=1)
        fig.add_hrect(y0=0, y1=20, fillcolor="green", opacity=0.1, line_width=0, row=4, col=1)
    # Layout Final
    fig.update_layout(
        height=1200,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1, x=0)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Debug Area ---
    with st.expander("🕵️ Detalhes das Regras (Debug)"):
        st.write("Estado das variáveis no último candle:")
        st.json(regras)
        st.write("Dados Brutos (Últimos 5 dias):")
        st.dataframe(df.tail(5))