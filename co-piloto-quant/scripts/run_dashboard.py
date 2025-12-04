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

# 2. Configurações Dinâmicas
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ Ajuste Fino")
periodo_bb = st.sidebar.slider("Período Bollinger/Médias", 20, 300, 200)
desvio_bb = st.sidebar.number_input("Desvio Padrão", 1.0, 3.0, 2.0, 0.1)
ver_bandas_sistema = st.sidebar.checkbox("Ver Bandas de Fluxo (TPM)", value=True)

# --- Na Barra Lateral, adicione este controle novo ---
st.sidebar.markdown("---")
st.sidebar.subheader("🔬 Laboratório Quant")
modo_analise_profunda = st.sidebar.checkbox("Ativar Indicadores Espectrais (Half-Life/Hilbert)", value=False)

# --- Corpo Principal ---
st.title(f"📊 Análise Quantitativa: {selected_ticker}")

df = load_processed_data(selected_ticker)

if df.empty:
    st.error("Arquivo vazio.")
else:
    # Recalcula indicadores visuais baseados nos sliders (Interatividade!)
    df_visual = df.copy()
    
    # Validação de Regras (Usando o último candle)
    last_row = df.iloc[-1]
    regras = check_rules(last_row)

    # --- Painel de Status (Topo) ---
    # AGORA COM 5 COLUNAS PARA INCLUIR O HURST
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Preço Atual", f"R$ {last_row['close']:.2f}")
    
    with col2:
        status_compra = "SIM" if regras.get('Sinal_Compra') else "NÃO"
        st.metric("Sinal de COMPRA", status_compra, delta="Potencial Alta" if regras.get('Sinal_Compra') else None)

    with col3:
        status_venda = "SIM" if regras.get('Sinal_Venda') else "NÃO"
        st.metric("Sinal de VENDA", status_venda, delta_color="inverse", delta="-Potencial Baixa" if regras.get('Sinal_Venda') else None)

    with col4:
        squeeze = "ALERTA" if regras.get('Potencial_Squeeze') else "Normal"
        st.metric("Volatilidade", squeeze, delta="Explosão Iminente" if regras.get('Potencial_Squeeze') else None, delta_color="off")

    # --- NOVO CARD PARA O HURST ---
    with col5:
        # Pega o valor do Hurst diretamente do dicionário de regras para consistência
        hurst_val = regras.get('Hurst_Score', 0.5)
        
        # Define o texto do regime
        if hurst_val > 0.6:
            regime = "TENDÊNCIA"
            delta_color = "normal" # Verde
        elif hurst_val < 0.4:
            regime = "LATERAL"
            delta_color = "inverse" # Vermelho
        else:
            regime = "NEUTRO"
            delta_color = "off" # Cinza
            
        st.metric("Regime (Hurst)", f"{hurst_val:.2f}", delta=regime, delta_color=delta_color)


    # --- Visualização Gráfica (Plotly) ---
    
    # Definição dinâmica de linhas baseada no modo escolhido
    if modo_analise_profunda:
        total_rows = 8 # AUMENTADO PARA 8 LINHAS
        # Alturas ajustadas para 8 gráficos, dando um pouco mais de espaço para os de física
        row_heights = [0.35, 0.10, 0.10, 0.10, 0.10, 0.10, 0.075, 0.075] 
        titles = (
            "Ação do Preço & Estrutura", "Fluxo (OBTR/WAD)", "Oscilador (IFR)", 
            "Estocástico (80,3,3)", "Regime (Hurst)", 
            "Ciclos de Mercado (Hilbert Sine)", 
            "Física: Half-Life (Barras)", # Título separado
            "Física: Entropia (Linha)"     # Título separado
        )
        fig_height = 2000 # Altura aumentada
    else:
        total_rows = 5
        row_heights = [0.40, 0.15, 0.15, 0.15, 0.15]
        titles = (
            "Ação do Preço & Estrutura", "Fluxo (OBTR/WAD)", "Oscilador (IFR)", 
            "Estocástico (80,3,3)", "Regime (Hurst)"
        )
        fig_height = 1400

    fig = make_subplots(
        rows=total_rows, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=titles,
        # REMOVIDO secondary_y, agora todos os eixos são primários
        specs=[[{"secondary_y": False}]] * total_rows 
    )

    # --- PLOTS ORIGINAIS (LINHAS 1-5) ---

    # 1. PREÇO (Row 1)
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="OHLC"
    ), row=1, col=1)

    # Média Móvel
    fig.add_trace(go.Scatter(
        x=df.index, y=df['close'].ewm(alpha=1/periodo_bb, adjust=False).mean(), 
        line=dict(color='orange', width=2), name=f"Média Wilder {periodo_bb}"
    ), row=1, col=1)
    
    # Banda de Squeeze (0.45)
    if 'BB_Upper_200_0.45' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Upper_200_0.45'], 
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Lower_200_0.45'], 
            line=dict(width=0), 
            fill='tonexty', fillcolor='rgba(0, 255, 0, 0.15)',
            name="Zona Squeeze (0.45)"
        ), row=1, col=1)

    # Bandas de Bollinger (2.0)
    if 'BB_Upper_200_2.0' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Upper_200_2.0'], 
            line=dict(color='gray', width=1, dash='dot'), showlegend=False
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=df.index, y=df['BB_Lower_200_2.0'], 
            line=dict(color='gray', width=1, dash='dot'), name="Bollinger (2.0)",
            fill='tonexty', fillcolor='rgba(128,128,128,0.1)'
        ), row=1, col=1)

    # 2. FLUXO (Row 2)
    if 'obtr' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['obtr'], line=dict(color='#00FF00', width=1), name="OBTR (Fluxo)"), row=2, col=1)
        if ver_bandas_sistema and 'obtr_bb_upper_band_0_45' in df.columns:
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_upper_band_0_45'], line=dict(width=0), showlegend=False), row=2, col=1)
             fig.add_trace(go.Scatter(x=df.index, y=df['obtr_bb_lower_band_0_45'], line=dict(width=0), fill='tonexty', fillcolor='rgba(0, 255, 0, 0.1)', name="Zona OBTR"), row=2, col=1)

    if 'wad' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['wad'], line=dict(color='#FF00FF', width=1), name="Williams A/D"), row=2, col=1)
        if ver_bandas_sistema and 'wad_bb_upper_band_0_45' in df.columns:
             fig.add_trace(go.Scatter(x=df.index, y=df['wad_bb_upper_band_0_45'], line=dict(width=0), showlegend=False), row=2, col=1)
             fig.add_trace(go.Scatter(x=df.index, y=df['wad_bb_lower_band_0_45'], line=dict(width=0), fill='tonexty', fillcolor='rgba(255, 0, 255, 0.1)', name="Zona WAD"), row=2, col=1)

    # 3. IFR (Row 3)
    if 'IFR_120' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['IFR_120'], line=dict(color='cyan', width=1.5), name="IFR 120"), row=3, col=1)
        fig.add_hline(y=50, line_dash="dash", line_color="white", opacity=0.3, row=3, col=1)
        fig.add_hrect(y0=48, y1=52, fillcolor="white", opacity=0.1, layer="below", line_width=0, row=3, col=1)

    # 4. ESTOCÁSTICO (Row 4)
    col_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    col_d = f'stoch_d_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}_{STOCH_D_SMOOTH}'

    if col_k in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col_k], 
            line=dict(color='#E377C2', width=1.5), name="Stoch %K"
        ), row=4, col=1)
        if col_d in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df[col_d], 
                line=dict(color='white', width=1, dash='dot'), name="Stoch %D"
            ), row=4, col=1)
        
        fig.add_hline(y=20, line_dash="dash", line_color="gray", opacity=0.5, row=4, col=1)
        fig.add_hline(y=80, line_dash="dash", line_color="gray", opacity=0.5, row=4, col=1)

    # 5. HURST EXPONENT (Row 5) - NOVO BLOCO
    col_hurst = 'Hurst_72_returns' # Nome da coluna CORRIGIDO
    
    if col_hurst in df.columns:
        # Plota a Linha do Hurst
        fig.add_trace(go.Scatter(
            x=df.index, y=df[col_hurst],
            line=dict(color='yellow', width=1.5), name="Hurst"
        ), row=5, col=1)
        
        # Zonas de Regime (Background Colorido)
        # Verde para Tendência (> 0.6)
        fig.add_hrect(y0=0.6, y1=1.0, fillcolor="green", opacity=0.15, layer="below", line_width=0, row=5, col=1)
        # Vermelho para Lateralidade/Reversão (< 0.4)
        fig.add_hrect(y0=0.0, y1=0.4, fillcolor="red", opacity=0.15, layer="below", line_width=0, row=5, col=1)
        # Linha Neutra
        fig.add_hline(y=0.5, line_dash="dot", line_color="gray", opacity=0.5, row=5, col=1)
        
        # Ajusta range do eixo Y para focar na área útil
        fig.update_yaxes(range=[0.2, 0.9], row=5, col=1)
    
    # -------------------------------------------------------------------------
    # --- NOVAS VISUALIZAÇÕES (Fórmulas Invisíveis) ---
    # -------------------------------------------------------------------------
    
    if modo_analise_profunda:
        # 6. HILBERT SINE WAVE (Row 6) - O Gatilho de Precisão
        if 'Hilbert_Sine' in df.columns and 'Hilbert_Lead' in df.columns:
            # Onda Senoidal (Verde Neon)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Hilbert_Sine'],
                line=dict(color='#00FF00', width=1.5), name="Hilbert Sine"
            ), row=6, col=1)
            
            # Onda Líder (Amarelo - Antecipa o movimento)
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Hilbert_Lead'],
                line=dict(color='yellow', width=1, dash='solid'), name="Hilbert Lead"
            ), row=6, col=1)

            # Linhas de Gatilho (+0.7 e -0.7)
            fig.add_hline(y=0.7, line_dash="dot", line_color="gray", row=6, col=1)
            fig.add_hline(y=-0.7, line_dash="dot", line_color="gray", row=6, col=1)
            
            # Preenchimento visual de Fundo/Topo
            fig.add_hrect(y0=-1, y1=-0.7, fillcolor="green", opacity=0.1, line_width=0, row=6, col=1) # Zona de Compra
            fig.add_hrect(y0=0.7, y1=1, fillcolor="red", opacity=0.1, line_width=0, row=6, col=1)     # Zona de Venda

        # 7. FÍSICA DE MERCADO: HALF-LIFE (Row 7) - AGORA SOZINHO
        if 'HalfLife_60' in df.columns:
            # Clip visual para não estragar o gráfico quando HL explode para 1000
            hl_plot = df['HalfLife_60'].clip(upper=50) 
            
            fig.add_trace(go.Bar(
                x=df.index, y=hl_plot,
                marker_color='rgba(100, 200, 255, 0.3)',
                name="Half-Life (Dias)",
            ), row=7, col=1)

            # Linha de corte para opções (Ex: 10 dias)
            fig.add_hline(y=10, line_dash="dash", line_color="cyan", annotation_text="Zona Opções (&lt;10d)", row=7, col=1)

        # 8. FÍSICA DE MERCADO: ENTROPIA (Row 8) - NOVO PAINEL
        if 'Entropy_20' in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index, y=df['Entropy_20'],
                line=dict(color='orange', width=2),
                name="Entropia (Caos)"
            ), row=8, col=1) # MOVIDO PARA ROW 8
            
            # Zona de Caos (> 3.0 bits)
            fig.add_hrect(y0=3.0, y1=4.0, fillcolor="red", opacity=0.1, line_width=0, row=8, col=1) # MOVIDO PARA ROW 8

        # ATUALIZAÇÃO DOS EIXOS Y SEPARADAMENTE
        fig.update_yaxes(title_text="Half-Life (Dias)", range=[0, 50], row=7, col=1)
        fig.update_yaxes(title_text="Entropia (Bits)", range=[1, 4], row=8, col=1)

    # Layout Final
    fig.update_layout(
        height=fig_height, # Aumentei a altura para caber o 5º gráfico
        xaxis_rangeslider_visible=False,
        template="plotly_white",
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