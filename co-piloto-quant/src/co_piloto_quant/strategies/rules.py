import pandas as pd
import numpy as np

from co_piloto_quant.risk_regime import RiskRegimeManager
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.config import (
    BB_PERIOD,
    STOCH_K_PERIOD,
    STOCH_K_SMOOTH,
    BB_ENTRY_STD_DEV_DEFAULT,
    HURST_WINDOW,
    ENTROPY_WINDOW,
    SYSTEM_PERIOD,
    FILTER_MAX_VOLATILITY,
    FILTER_MAX_RAW_ENTROPY
)

def check_rules_live(df: pd.DataFrame) -> dict:
    """
    Verifica as regras de trading para a última vela (cenário de tempo real).
    """
    if df.empty or len(df) < 20:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False, 
            'Motivo_Bloqueio': "Dados insuficientes para análise."
        }

    risk_manager = RiskRegimeManager()
    risk_check = risk_manager.validate_market_regime(df)
    if not risk_check['approved']:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False,
            'Stop_Loss_Sugerido_Long': None, 'Stop_Loss_Sugerido_Short': None,
            'Motivo_Bloqueio': f"⛔ {risk_check['reason']}"
        }

    latest = df.iloc[-1]
    hurst_z_col = IndicatorNames.hurst_z(HURST_WINDOW)
    if latest.get(hurst_z_col, 0) < -0.5:
        return { 'Sinal_Compra': False, 'Sinal_Venda': False, 'Motivo_Bloqueio': f"Tendência Fraca (Hurst Z: {latest.get(hurst_z_col, 0):.2f})" }

    entropy_z_col = IndicatorNames.entropy_z(ENTROPY_WINDOW)
    if latest.get(entropy_z_col, 0) > 1.0:
        return { 'Sinal_Compra': False, 'Sinal_Venda': False, 'Motivo_Bloqueio': f"Ruído Anormal (Entropy Z: {latest.get(entropy_z_col, 0):.2f})" }

    bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    stoch_k = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    
    obtr_name, wad_name = IndicatorNames.obtr(), IndicatorNames.wad()
    obtr_mid_band = IndicatorNames.tpm_band(obtr_name, SYSTEM_PERIOD, 'middle')
    wad_mid_band = IndicatorNames.tpm_band(wad_name, SYSTEM_PERIOD, 'middle')

    is_in_buy_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_upper])
    is_stoch_buy = latest[stoch_k] < 30
    is_flow_buy = (latest.get(obtr_name, 0) > latest.get(obtr_mid_band, np.inf)) or (latest.get(wad_name, 0) > latest.get(wad_mid_band, np.inf))
    sinal_compra = is_in_buy_zone and is_stoch_buy and is_flow_buy
    
    bb_middle = IndicatorNames.bollinger_middle(BB_PERIOD)
    is_in_sell_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_middle])
    is_stoch_sell = latest[stoch_k] > 70
    is_flow_sell = latest.get(obtr_name, 0) < latest.get(obtr_mid_band, -np.inf)
    wwma_200 = IndicatorNames.wwma(200)
    sinal_venda = (latest['close'] < latest.get(wwma_200, np.inf)) and is_in_sell_zone and is_stoch_sell and is_flow_sell

    motivo = "Aprovado" if (sinal_compra or sinal_venda) else "Sem gatilho técnico"
    return {
        'Sinal_Compra': bool(sinal_compra), 'Sinal_Venda': bool(sinal_venda),
        'Stop_Loss_Sugerido_Long': float(latest[bb_lower]) if sinal_compra else None,
        'Stop_Loss_Sugerido_Short': float(latest[bb_upper]) if sinal_venda else None,
        'Motivo_Bloqueio': motivo
    }

def check_rules_vectorized(df: pd.DataFrame) -> dict:
    """
    Verifica as regras de trading de forma vetorial para backtesting.
    """
    hurst_col = IndicatorNames.hurst(HURST_WINDOW, kind='price')
    vol_col = IndicatorNames.volatility(21)
    entropy_col = IndicatorNames.entropy(ENTROPY_WINDOW)

    required_cols = [hurst_col, vol_col, entropy_col]
    if not all(col in df.columns for col in required_cols):
        return {
            'entries': pd.Series(False, index=df.index), 'exits': pd.Series(False, index=df.index),
            'short_entries': pd.Series(False, index=df.index), 'short_exits': pd.Series(False, index=df.index)
        }
        
    regime_ok = (
        (df[hurst_col] >= 0.5) &
        (df[vol_col] < FILTER_MAX_VOLATILITY) &
        (df[entropy_col] < FILTER_MAX_RAW_ENTROPY)
    )

    hurst_z_col = IndicatorNames.hurst_z(HURST_WINDOW)
    entropy_z_col = IndicatorNames.entropy_z(ENTROPY_WINDOW)
    qualidade_ok = (
        (df.get(hurst_z_col, pd.Series(0, index=df.index)) >= -0.5) &
        (df.get(entropy_z_col, pd.Series(0, index=df.index)) <= 1.0)
    )
    filtro_geral = regime_ok & qualidade_ok

    bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    stoch_k = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    
    obtr_name, wad_name = IndicatorNames.obtr(), IndicatorNames.wad()
    obtr_mid_band = IndicatorNames.tpm_band(obtr_name, SYSTEM_PERIOD, 'middle')
    wad_mid_band = IndicatorNames.tpm_band(wad_name, SYSTEM_PERIOD, 'middle')

    is_in_buy_zone = (df['close'] >= df[bb_lower]) & (df['close'] <= df[bb_upper])
    is_stoch_buy = df[stoch_k] < 30
    is_flow_buy = (df.get(obtr_name, 0) > df.get(obtr_mid_band, np.inf)) | (df.get(wad_name, 0) > df.get(wad_mid_band, np.inf))
    entries = filtro_geral & is_in_buy_zone & is_stoch_buy & is_flow_buy
    
    bb_middle = IndicatorNames.bollinger_middle(BB_PERIOD)
    is_in_sell_zone = (df['close'] >= df[bb_lower]) & (df['close'] <= df[bb_middle])
    is_stoch_sell = df[stoch_k] > 70
    is_flow_sell = df.get(obtr_name, 0) < df.get(obtr_mid_band, -np.inf)
    wwma_200 = IndicatorNames.wwma(200)
    is_below_long_term_ma = df['close'] < df.get(wwma_200, np.inf)
    short_entries = filtro_geral & is_below_long_term_ma & is_in_sell_zone & is_stoch_sell & is_flow_sell

    bb_upper_exit = IndicatorNames.bollinger_upper(BB_PERIOD, 2.0)
    bb_lower_exit = IndicatorNames.bollinger_lower(BB_PERIOD, 2.0)
    exits = (df['close'] >= df[bb_upper_exit]) | (~filtro_geral)
    short_exits = (df['close'] <= df[bb_lower_exit]) | (~filtro_geral)

    return {
        'entries': entries, 'exits': exits,
        'short_entries': short_entries, 'short_exits': short_exits
    }

def check_rules(df: pd.DataFrame, mode: str = 'live', **kwargs) -> dict:
    """
    Ponto de entrada unificado para a estratégia 'rules'.
    Delega para a função correta (live ou vetorial) com base no modo.
    """
    if mode == 'vectorized':
        return check_rules_vectorized(df, **kwargs)
    return check_rules_live(df, **kwargs)