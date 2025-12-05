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
    Implementação Fiel do Ehlers Hilbert Sine Wave, agora incluindo a geração
    da coluna de status textual do ciclo.
    """
    col_lower = column.lower()
    if col_lower not in data.columns:
        if 'close' in data.columns:
            col_lower = 'close'
        else:
            return pd.DataFrame()

    prices = data[col_lower].values.astype(float)
    n = len(prices)

    ema_period = 60
    ema = pd.Series(prices).ewm(span=ema_period, adjust=False).mean().values
    detrended_prices = prices - ema
    
    sine = np.full(n, np.nan)
    lead_sine = np.full(n, np.nan)
    period = np.full(n, 20.0)
    phase = np.full(n, np.nan)
    
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

    short_period = float(config.HILBERT_SHORT_PERIOD)
    long_period = float(config.HILBERT_LONG_PERIOD)

    for i in range(n):
        if i >= 3:
            smooth[i] = (4*detrended_prices[i] + 3*detrended_prices[i-1] + 2*detrended_prices[i-2] + detrended_prices[i-3]) / 10.0
        else:
            smooth[i] = detrended_prices[i]

    ss_short = ehlers_super_smoother(smooth, short_period)
    ss_long = ehlers_super_smoother(smooth, long_period)
    roof = ss_short - ss_long
    hp = roof 

    for i in range(6, n):
        cycle_adj = 0.075 * period[i-1] + 0.54
        src, src_m2, src_m4, src_m6 = hp[i], hp[i-2], hp[i-4], hp[i-6]
        q1[i] = (0.0962 * src + 0.5769 * src_m2 - 0.5769 * src_m4 - 0.0962 * src_m6) * cycle_adj
        i1[i] = smooth[i-3]
        i2[i], q2[i] = 0.2 * i1[i] + 0.8 * i2[i-1], 0.2 * q1[i] + 0.8 * q2[i-1]
        
        prev_amp = math.hypot(i2[i-1], q2[i-1]) + eps
        curr_amp = math.hypot(i2[i], q2[i]) + eps
        inorm, qnorm = i2[i] / curr_amp, q2[i] / curr_amp
        inorm_prev, qnorm_prev = i2[i-1] / prev_amp, q2[i-1] / prev_amp

        re_raw[i] = inorm * inorm_prev + qnorm * qnorm_prev
        im_raw[i] = inorm * qnorm_prev - qnorm * inorm_prev
        re_s[i], im_s[i] = 0.2 * re_raw[i] + 0.8 * re_s[i-1], 0.2 * im_raw[i] + 0.8 * im_s[i-1]

        d_phase = math.atan2(im_s[i], re_s[i]) * rad2deg if abs(re_s[i]) > eps or abs(im_s[i]) > eps else 0.0
        d_phase = max(min(d_phase, 60.0), 1.0)
        inst_period = 360.0 / d_phase if d_phase != 0 else period[i-1]
        period[i] = 0.33 * inst_period + 0.67 * period[i-1]

        phase_deg = math.atan2(q2[i], i2[i]) * rad2deg if abs(i2[i]) > eps or abs(q2[i]) > eps else 0.0
        prev_phase = phase[i-1] if not np.isnan(phase[i-1]) else phase_deg
        diff = phase_deg - prev_phase
        while diff > 180: diff -= 360
        while diff < -180: diff += 360
        if diff > 90: phase_deg -= 360
        elif diff < -90: phase_deg += 360
        
        phase[i] = phase_deg
        sine[i] = math.sin(phase[i] * deg2rad)
        lead_sine[i] = math.sin((phase[i] + 45.0) * deg2rad)

    df_result = pd.DataFrame(index=data.index)
    df_result['Hilbert_Sine'] = sine
    df_result['Hilbert_Lead'] = lead_sine
    df_result['Hilbert_Period'] = period
    
    # --- LÓGICA DE STATUS DO CICLO (VETORIZADA) ---
    # Adicionada aqui para que o indicador já retorne o status textual
    ciclo_alta = df_result['Hilbert_Sine'] > df_result['Hilbert_Lead']
    ciclo_baixa = df_result['Hilbert_Sine'] < df_result['Hilbert_Lead']
    fundo_confirmado = df_result['Hilbert_Sine'] < -0.7
    topo_confirmado = df_result['Hilbert_Sine'] > 0.7
    # O período do ciclo para swing trade deve ser razoável
    ciclo_saudavel = (df_result['Hilbert_Period'] > 10) & (df_result['Hilbert_Period'] < 60)
    
    # Usa np.select para uma lógica if/elif/else eficiente em DataFrames
    conditions = [
        ~ciclo_saudavel,
        fundo_confirmado & ciclo_alta,
        topo_confirmado & ciclo_baixa,
        fundo_confirmado,
        topo_confirmado,
        ciclo_alta,
        ciclo_baixa
    ]
    choices = [
        "Caótico",
        "Virada (Fundo)",
        "Virada (Topo)",
        "Fundo Extremo",
        "Topo Extremo",
        "Subindo",
        "Caindo"
    ]
    df_result['Hilbert_Status'] = np.select(conditions, choices, default="Neutro")
    # --- FIM DA LÓGICA DE STATUS ---

    # Limpeza do warmup (20 barras)
    df_result.iloc[:20] = np.nan
    
    return df_result

# Alias para facilitar importação
ehlers_sinewave = calculate_ehlers_sinewave
