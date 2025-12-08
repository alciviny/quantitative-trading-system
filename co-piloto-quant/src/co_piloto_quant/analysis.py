import pandas as pd
import numpy as np
import pandas_ta as ta
from co_piloto_quant.config import (STOCH_K_PERIOD,
                                     STOCH_K_SMOOTH,
                                     SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
                                     BB_PERIOD, PRICE_BB_DEVIATIONS)

# Importações dos indicadores
from co_piloto_quant.risk_regime import validate_market_regime, calculate_vol_of_vol
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.ehlers_hilbert import ehlers_sinewave
from co_piloto_quant.indicators.names import IndicatorNames

def safe_join(df_original: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

def calculate_z_score(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calcula o Z-Score (Desvio Padrão da Média).
    """
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    z_score = (series - roll_mean) / (roll_std + 1e-9)
    return z_score

def calculate_indicators(
    df: pd.DataFrame,
    hurst_window: int = 72,
    entropy_window: int = 20,
    halflife_window: int = 60,
    stoch_d_window: int = 3,
    bb_entry_deviation: float = 0.45,
    calculate_hurst: bool = True
) -> pd.DataFrame:
    
    if 'close' in df.columns:
        df = df[df['close'] > 0].copy()
    df = df[~df.index.duplicated(keep='first')]
    if len(df) < 200: return pd.DataFrame()

    wwma_200_col = IndicatorNames.wwma(200)
    if wwma_200_col not in df.columns:
        df[wwma_200_col] = ww_moving_average(df, period=200, column='close')
    
    df['IFR_120'] = ta.rsi(df['close'], length=120)
    
    all_bb_deviations = sorted(list(set(PRICE_BB_DEVIATIONS + [bb_entry_deviation])))
    bb_df = bollinger_bands(df, period=BB_PERIOD, std_devs=all_bb_deviations)
    df = safe_join(df, bb_df)

    stoch_df = calculate_stochastic_custom(df, k_period=STOCH_K_PERIOD, k_smooth=STOCH_K_SMOOTH, d_smooth=stoch_d_window)
    df = safe_join(df, stoch_df)

    obtr_tpm = calculate_system_tpm(df, indicator='obtr', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
    df = safe_join(df, obtr_tpm)
    wad_tpm = calculate_system_tpm(df, indicator='wad', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
    df = safe_join(df, wad_tpm)

    if calculate_hurst:
        hurst = calculate_rolling_hurst(df['close'], window=hurst_window, kind='returns')
        df = safe_join(df, pd.DataFrame(hurst))
    
    entropy_col = IndicatorNames.entropy(entropy_window)
    entropy_series = calculate_rolling_entropy(df['close'], window=entropy_window)
    entropy_series.name = entropy_col
    df = safe_join(df, entropy_series.to_frame())

    ou_stats = calculate_rolling_ou_params(df['close'], window=halflife_window)
    df = safe_join(df, ou_stats)
    
    hilbert_df = ehlers_sinewave(df, column='close')
    df = safe_join(df, hilbert_df)
    
    volvol_col = IndicatorNames.vol_of_vol(20)
    df[volvol_col] = df['close'].rolling(window=40, min_periods=25).apply(
        lambda x: calculate_vol_of_vol(x, window=20),
        raw=False
    )

    lookback_learning = 252 
    
    df[IndicatorNames.entropy_z(entropy_window)] = calculate_z_score(df[entropy_col], window=lookback_learning)
    
    if calculate_hurst:
        hurst_col = IndicatorNames.hurst(hurst_window, 'returns')
        df[IndicatorNames.hurst_z()] = calculate_z_score(df[hurst_col], window=lookback_learning)
        
    df[IndicatorNames.vol_of_vol_z()] = calculate_z_score(df[volvol_col], window=lookback_learning)

    return df

def check_rules(df: pd.DataFrame) -> dict:
    """
    Verifica sinais usando Lógica Adaptativa (Z-Scores).
    """
    if df.empty or len(df) < 20:
        return {'Sinal_Compra': False, 'Sinal_Venda': False, 'Motivo_Bloqueio': "Dados insuficientes"}

    risk_check = validate_market_regime(df)
    if not risk_check['approved']:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Stop_Loss_Sugerido_Long': None, 'Stop_Loss_Sugerido_Short': None, 
            'Motivo_Bloqueio': f"⛔ {risk_check['reason']}"
        }

    latest = df.iloc[-1]
    
    hurst_z_col = IndicatorNames.hurst_z()
    if latest.get(hurst_z_col, 0) < -0.5:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Motivo_Bloqueio': f"Tendência Fraca para o Padrão do Ativo (Hurst Z: {latest.get(hurst_z_col, 0):.2f})"
        }

    entropy_z_col = IndicatorNames.entropy_z(20) # Assuming entropy window is 20
    if latest.get(entropy_z_col, 0) > 1.0:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Motivo_Bloqueio': f"Ruído Anormal para o Ativo (Entropy Z: {latest.get(entropy_z_col, 0):.2f})"
        }

    bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, 0.45)
    bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, 0.45)
    stoch_k = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    
    is_in_buy_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_upper])
    is_stoch_buy = latest[stoch_k] < 30
    
    obtr_mid_band = IndicatorNames.tpm_band('obtr', 'middle_band')
    wad_mid_band = IndicatorNames.tpm_band('wad', 'middle_band')
    is_flow_buy = (latest.get('obtr', 0) > latest.get(obtr_mid_band, np.inf)) or \
                  (latest.get('wad', 0) > latest.get(wad_mid_band, np.inf))
    
    sinal_compra = is_in_buy_zone and is_stoch_buy and is_flow_buy
    
    bb_middle = IndicatorNames.bollinger_middle(BB_PERIOD)
    is_in_sell_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_middle])
    is_stoch_sell = latest[stoch_k] > 70
    is_flow_sell = latest.get('obtr', 0) < latest.get(obtr_mid_band, -np.inf)
    
    wwma_200 = IndicatorNames.wwma(200)
    sinal_venda = (latest['close'] < latest[wwma_200]) and is_in_sell_zone and is_stoch_sell and is_flow_sell

    motivo = "Aprovado" if (sinal_compra or sinal_venda) else "Sem gatilho técnico"

    return {
        'Sinal_Compra': bool(sinal_compra),
        'Sinal_Venda': bool(sinal_venda),
        'Stop_Loss_Sugerido_Long': float(latest[bb_lower]) if sinal_compra else None,
        'Stop_Loss_Sugerido_Short': float(latest[bb_upper]) if sinal_venda else None,
        'Motivo_Bloqueio': motivo
    }