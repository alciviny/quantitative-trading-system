import pandas as pd
import numpy as np
import math
from co_piloto_quant import config

def ehlers_super_smoother(prices: np.ndarray, period: float) -> np.ndarray:
    """
    Filtro SuperSmoother de Ehlers (2-pole Butterworth modificado).
    Remove aliasing e ruído com atraso mínimo.
    """
    n = len(prices)
    out = np.zeros(n)
    
    # Proteção para períodos muito curtos
    if period < 1.0:
        period = 1.0
        
    # Coeficientes derivados da fórmula do Ehlers
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -a1 * a1
    c1 = 1.0 - c2 - c3
    
    # Inicialização segura
    out[0] = prices[0]
    out[1] = prices[1]
    
    for i in range(2, n):
        out[i] = c1 * (prices[i] + prices[i-1]) / 2.0 + c2 * out[i-1] + c3 * out[i-2]
        
    return out

def calculate_ehlers_sinewave(data: pd.DataFrame, column: str = 'close') -> pd.DataFrame:
    """
    Implementação Fiel do Ehlers Hilbert Sine Wave (Versão DSP).
    
    Ajustes Realizados:
    1. Roofing Filter: Banda ajustada para 6-40 barras (Swing Trade).
    2. Discriminador Homodino: Normalizado pela amplitude (robusto a volatilidade).
    3. Fase: Controle de continuidade para evitar saltos.
    """
    col_lower = column.lower()
    if col_lower not in data.columns:
        if 'close' in data.columns:
            col_lower = 'close'
        else:
            return pd.DataFrame()

    # Prepara os dados
    prices = data[col_lower].values.astype(float)
    n = len(prices)
    
    # Arrays de Saída
    sine = np.full(n, np.nan)
    lead_sine = np.full(n, np.nan)
    period = np.full(n, 20.0) # Valor inicial conservador
    phase = np.full(n, np.nan)
    
    # Arrays de Estado
    smooth = np.zeros(n)
    i1 = np.zeros(n)
    q1 = np.zeros(n)
    i2 = np.zeros(n)
    q2 = np.zeros(n)
    re_raw = np.zeros(n)
    im_raw = np.zeros(n)
    re_s = np.zeros(n)
    im_s = np.zeros(n)

    eps = 1e-9
    rad2deg = 180.0 / math.pi
    deg2rad = math.pi / 180.0

    # --- CONFIGURAÇÃO DO ROOFING FILTER (A CORREÇÃO DA "PEGADINHA") ---
    # Short: 6 (Filtra ruído de curtíssimo prazo)
    # Long: 40 (Filtra a tendência macro, deixando o ciclo de Swing Trade passar)
    short_period = float(config.HILBERT_SHORT_PERIOD)
    long_period = float(config.HILBERT_LONG_PERIOD)

    # 1. Pré-suavização WMA (4-3-2-1)
    for i in range(n):
        if i >= 3:
            smooth[i] = (4*prices[i] + 3*prices[i-1] + 2*prices[i-2] + prices[i-3]) / 10.0
        else:
            smooth[i] = prices[i]

    # 2. Roofing Filter (SuperSmoother Curto - SuperSmoother Longo)
    ss_short = ehlers_super_smoother(smooth, short_period)
    ss_long = ehlers_super_smoother(smooth, long_period)
    roof = ss_short - ss_long
    
    # O Roofing Filter é a entrada para o Hilbert
    hp = roof 

    # Loop Principal
    for i in range(6, n):
        # Ajuste adaptativo do filtro Hilbert baseado no período medido anterior
        cycle_adj = 0.075 * period[i-1] + 0.54

        # 3. Transformada de Hilbert (Filtro 7-Tap)
        src = hp[i]
        src_m2 = hp[i-2] if i-2 >= 0 else 0.0
        src_m4 = hp[i-4] if i-4 >= 0 else 0.0
        src_m6 = hp[i-6] if i-6 >= 0 else 0.0
        
        q1[i] = (0.0962 * src + 0.5769 * src_m2 - 0.5769 * src_m4 - 0.0962 * src_m6) * cycle_adj
        i1[i] = smooth[i-3] # Alinhamento de Lag (3 barras)

        # 4. Suavização I/Q (Filtro EMA Fast)
        i2[i] = 0.2 * i1[i] + 0.8 * i2[i-1]
        q2[i] = 0.2 * q1[i] + 0.8 * q2[i-1]

        # 5. Normalização de Amplitude (Homodyne Robustness)
        prev_amp = math.hypot(i2[i-1], q2[i-1]) + eps
        curr_amp = math.hypot(i2[i], q2[i]) + eps
        
        inorm = i2[i] / curr_amp
        qnorm = q2[i] / curr_amp
        inorm_prev = i2[i-1] / prev_amp
        qnorm_prev = q2[i-1] / prev_amp

        # 6. Discriminador Homodino (Produto Complexo)
        re_raw[i] = inorm * inorm_prev + qnorm * qnorm_prev
        im_raw[i] = inorm * qnorm_prev - qnorm * inorm_prev

        # Suavização do Vetor de Fase
        re_s[i] = 0.2 * re_raw[i] + 0.8 * re_s[i-1]
        im_s[i] = 0.2 * im_raw[i] + 0.8 * im_s[i-1]

        # 7. Cálculo do Período
        if abs(re_s[i]) > eps or abs(im_s[i]) > eps:
            d_phase = math.atan2(im_s[i], re_s[i]) * rad2deg
        else:
            d_phase = 0.0
            
        # Clamping (Limitar a variação do período para valores sadios)
        d_phase = max(min(d_phase, 60.0), 1.0)
        
        inst_period = 360.0 / d_phase if d_phase != 0 else period[i-1]
        
        # Suavização do Período (Alpha 0.33 padrão Ehlers)
        period[i] = 0.33 * inst_period + 0.67 * period[i-1]

        # 8. Cálculo da Fase (Sinal Analítico)
        if abs(i2[i]) > eps or abs(q2[i]) > eps:
            phase_deg = math.atan2(q2[i], i2[i]) * rad2deg
        else:
            phase_deg = 0.0

        # Controle de Continuidade (Phase Wrapping)
        prev_phase = phase[i-1] if not np.isnan(phase[i-1]) else phase_deg
        diff = phase_deg - prev_phase
        
        # Ajusta para o caminho mais curto no círculo trigonométrico
        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        
        # Se a diferença for extrema, ajusta a fase absoluta
        if diff > 90: phase_deg -= 360
        elif diff < -90: phase_deg += 360
        
        phase[i] = phase_deg

        # 9. Saídas Finais (Seno e Seno Adiantado)
        sine[i] = math.sin(phase[i] * deg2rad)
        lead_sine[i] = math.sin((phase[i] + 45.0) * deg2rad)

    # Montagem do DataFrame
    df_result = pd.DataFrame(index=data.index)
    df_result['Hilbert_Sine'] = sine
    df_result['Hilbert_Lead'] = lead_sine
    df_result['Hilbert_Period'] = period
    
    # Limpeza do warmup (20 barras)
    df_result.iloc[:20] = np.nan
    
    return df_result

# Alias para facilitar importação
ehlers_sinewave = calculate_ehlers_sinewave
