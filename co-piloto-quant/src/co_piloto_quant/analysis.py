import pandas as pd
import numpy as np
import pandas_ta as ta
from co_piloto_quant.config import (STOCH_K_PERIOD,
                                     STOCH_K_SMOOTH,
                                     SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
                                     BB_PERIOD, PRICE_BB_DEVIATIONS)

# Importações dos indicadores (mantém os mesmos)
from co_piloto_quant.risk_regime import validate_market_regime, calculate_vol_of_vol
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.ehlers_hilbert import ehlers_sinewave

def safe_join(df_original: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

def calculate_z_score(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calcula o Z-Score (Desvio Padrão da Média).
    Isso normaliza o indicador:
    0.0  = Comportamento perfeitamente normal para este ativo.
    +2.0 = Excepcionalmente alto (Top 2.5% do histórico).
    -2.0 = Excepcionalmente baixo.
    """
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    # Adicionamos 1e-9 para evitar divisão por zero
    z_score = (series - roll_mean) / (roll_std + 1e-9)
    return z_score

def calculate_indicators(
    df: pd.DataFrame,
    hurst_window: int = 72,
    entropy_window: int = 20,
    halflife_window: int = 60,
    stoch_k_window: int = 80,
    stoch_d_window: int = 3,
    bb_entry_deviation: float = 0.45,
    calculate_hurst: bool = True 
) -> pd.DataFrame:
    
    # 1. Limpeza e Validação
    if 'close' in df.columns:
        df = df[df['close'] > 0].copy()
    df = df[~df.index.duplicated(keep='first')]
    if len(df) < 200: return pd.DataFrame()

    # 2. Indicadores Técnicos Clássicos (Bandas, Stoch, WWMA)
    # [Mantém a lógica original de cálculo técnico...]
    if 'WWMA_200' not in df.columns:
        df['WWMA_200'] = ww_moving_average(df, period=200, column='close')
    
    df['IFR_120'] = ta.rsi(df['close'], length=120)
    
    # Bandas de Bollinger
    all_bb_deviations = sorted(list(set(PRICE_BB_DEVIATIONS + [bb_entry_deviation])))
    bb_df = bollinger_bands(df, period=BB_PERIOD, std_devs=all_bb_deviations)
    df = safe_join(df, bb_df)

    # Estocástico
    stoch_df = calculate_stochastic_custom(df, k_period=stoch_k_window, k_smooth=STOCH_K_SMOOTH, d_smooth=stoch_d_window)
    df = safe_join(df, stoch_df)

    # Fluxo (TPM)
    obtr_tpm = calculate_system_tpm(df, indicator='obtr', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
    df = safe_join(df, obtr_tpm)
    wad_tpm = calculate_system_tpm(df, indicator='wad', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
    df = safe_join(df, wad_tpm)

    # 3. Indicadores de Regime (Forensics)
    # Hurst
    if calculate_hurst:
        hurst = calculate_rolling_hurst(df['close'], window=hurst_window, kind='returns')
        df = safe_join(df, pd.DataFrame(hurst))
    
    # Entropia
    entropy_series = calculate_rolling_entropy(df['close'], window=entropy_window)
    entropy_series.name = f'Entropy_{entropy_window}'
    df = safe_join(df, entropy_series.to_frame())

    # Half-Life
    ou_stats = calculate_rolling_ou_params(df['close'], window=halflife_window)
    df = safe_join(df, ou_stats)
    
    # Hilbert
    hilbert_df = ehlers_sinewave(df, column='close')
    df = safe_join(df, hilbert_df)
    
    # Volatilidade da Volatilidade (VolVol)
    # Usando a função robusta de risk_regime para consistência
    df['VolVol_20'] = df['close'].rolling(window=40, min_periods=25).apply(
        lambda x: calculate_vol_of_vol(x, window=20),
        raw=False
    )

    # --- A MÁGICA PROFISSIONAL: NORMALIZAÇÃO (Z-SCORES) ---
    # Aqui o sistema "aprende" o que é normal para o ativo nos últimos ~1 ano (252 dias)
    lookback_learning = 252 
    
    # Z-Score da Entropia: O quão "caótico" está comparado ao normal DESTE ativo?
    df['Entropy_Z'] = calculate_z_score(df[f'Entropy_{entropy_window}'], window=lookback_learning)
    
    # Z-Score do Hurst: A tendência está excepcionalmente forte (Z > 0) ou fraca (Z < 0)?
    if calculate_hurst:
        df['Hurst_Z'] = calculate_z_score(df['Hurst_72_returns'], window=lookback_learning)
        
    # Z-Score da VolVol: O risco de crash está anormalmente alto?
    df['VolVol_Z'] = calculate_z_score(df['VolVol_20'], window=lookback_learning)

    return df

def check_rules(df: pd.DataFrame) -> dict:
    """
    Verifica sinais usando Lógica Adaptativa (Z-Scores).
    Não usamos mais números mágicos absolutos como 3.2 ou 0.53.
    """
    if df.empty or len(df) < 20:
        return {'Sinal_Compra': False, 'Sinal_Venda': False, 'Motivo_Bloqueio': "Dados insuficientes"}

    # Validação de Risco (Chama o risk_regime atualizado)
    risk_check = validate_market_regime(df)
    if not risk_check['approved']:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Stop_Loss_Sugerido_Long': None, 'Stop_Loss_Sugerido_Short': None, 
            'Motivo_Bloqueio': f"⛔ {risk_check['reason']}"
        }

    latest = df.iloc[-1]
    
    # --- FILTROS DE REGIME ADAPTATIVOS ---
    
    # 1. Filtro de Tendência (Hurst Adaptativo)
    # Regra: Hurst deve estar ACIMA da média histórica do ativo (Z > 0)
    # ou pelo menos não muito abaixo (Z > -0.5)
    if latest.get('Hurst_Z', 0) < -0.5:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Motivo_Bloqueio': f"Tendência Fraca para o Padrão do Ativo (Hurst Z: {latest['Hurst_Z']:.2f})"
        }

    # 2. Filtro de Ruído (Entropia Adaptativa)
    # Regra: Entropia não pode estar muito acima do normal (Z < 1.0)
    # Aceitamos até 1 desvio padrão acima da média, mais que isso é caos anormal.
    if latest.get('Entropy_Z', 0) > 1.0:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Motivo_Bloqueio': f"Ruído Anormal para o Ativo (Entropy Z: {latest['Entropy_Z']:.2f})"
        }

    # --- LÓGICA TÉCNICA (Sniper) ---
    # (Essa parte se mantém igual, pois Preço/Bandas já são relativos por natureza)
    
    bb_upper = f'BB_Upper_{BB_PERIOD}_0.45' 
    bb_lower = f'BB_Lower_{BB_PERIOD}_0.45'
    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    
    # Compra
    is_in_buy_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_upper])
    is_stoch_buy = latest[stoch_k] < 30
    # Fluxo (Simplificado para exemplo)
    is_flow_buy = (latest['obtr'] > latest['obtr_bb_middle_band']) or (latest['wad'] > latest['wad_bb_middle_band'])
    
    sinal_compra = is_in_buy_zone and is_stoch_buy and is_flow_buy
    
    # Venda
    # ... (mesma lógica anterior) ...
    bb_middle = f'BB_Middle_{BB_PERIOD}'
    is_in_sell_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_middle])
    is_stoch_sell = latest[stoch_k] > 70
    is_flow_sell = latest['obtr'] < latest['obtr_bb_middle_band']
    
    sinal_venda = (latest['close'] < latest['WWMA_200']) and is_in_sell_zone and is_stoch_sell and is_flow_sell

    motivo = "Aprovado" if (sinal_compra or sinal_venda) else "Sem gatilho técnico"

    return {
        'Sinal_Compra': bool(sinal_compra),
        'Sinal_Venda': bool(sinal_venda),
        'Stop_Loss_Sugerido_Long': float(latest[bb_lower]) if sinal_compra else None,
        'Stop_Loss_Sugerido_Short': float(latest[bb_upper]) if sinal_venda else None,
        'Motivo_Bloqueio': motivo
    }