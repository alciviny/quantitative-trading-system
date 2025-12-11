import pandas as pd
import numpy as np

from co_piloto_quant.risk_regime import validate_market_regime
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.config import (
    BB_PERIOD,
    STOCH_K_PERIOD,
    STOCH_K_SMOOTH,
    BB_ENTRY_STD_DEV_DEFAULT,
    HURST_WINDOW,
    ENTROPY_WINDOW,
    SYSTEM_PERIOD,
)

def check_rules(df: pd.DataFrame) -> dict:
    """
    Verifica as regras de trading para a última entrada de dados do DataFrame,
    simulando um cenário de tempo real.

    Esta função combina filtros de regime de mercado (risco), condições de tendência,
    ruído e gatilhos técnicos baseados em indicadores.

    Args:
        df (pd.DataFrame): DataFrame contendo todos os dados de preço e indicadores
                           calculados. A última linha é usada para a decisão.

    Returns:
        dict: Um dicionário contendo os sinais de compra/venda, stops sugeridos
              e o motivo da decisão (ou bloqueio).
    """
    if df.empty or len(df) < 20:
        return {
            'Sinal_Compra': False, 
            'Sinal_Venda': False, 
            'Motivo_Bloqueio': "Dados insuficientes para análise."
        }

    # 1. Filtro de Regime de Risco
    risk_check = validate_market_regime(df)
    if not risk_check['approved']:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False,
            'Stop_Loss_Sugerido_Long': None, 'Stop_Loss_Sugerido_Short': None,
            'Motivo_Bloqueio': f"⛔ {risk_check['reason']}"
        }

    latest = df.iloc[-1]

    # 2. Filtros de Qualidade do Sinal (baseados em Z-Scores)
    hurst_z_col = IndicatorNames.hurst_z(HURST_WINDOW)
    if latest.get(hurst_z_col, 0) < -0.5:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False,
            'Motivo_Bloqueio': f"Tendência Fraca (Hurst Z: {latest.get(hurst_z_col, 0):.2f})"
        }

    entropy_z_col = IndicatorNames.entropy_z(ENTROPY_WINDOW)
    if latest.get(entropy_z_col, 0) > 1.0:
        return {
            'Sinal_Compra': False, 'Sinal_Venda': False,
            'Motivo_Bloqueio': f"Ruído Anormal (Entropy Z: {latest.get(entropy_z_col, 0):.2f})"
        }

    # 3. Gatilhos de Entrada (Técnicos)
    bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, BB_ENTRY_STD_DEV_DEFAULT)
    stoch_k = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    
    # Nomes dos indicadores de fluxo
    obtr_name = IndicatorNames.obtr()
    wad_name = IndicatorNames.wad()
    obtr_mid_band = IndicatorNames.tpm_band(obtr_name, SYSTEM_PERIOD, 'middle')
    wad_mid_band = IndicatorNames.tpm_band(wad_name, SYSTEM_PERIOD, 'middle')

    # Regra de Compra
    is_in_buy_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_upper])
    is_stoch_buy = latest[stoch_k] < 30
    
    is_flow_buy = (latest.get(obtr_name, 0) > latest.get(obtr_mid_band, np.inf)) or \
                  (latest.get(wad_name, 0) > latest.get(wad_mid_band, np.inf))
    
    sinal_compra = is_in_buy_zone and is_stoch_buy and is_flow_buy
    
    # Regra de Venda
    bb_middle = IndicatorNames.bollinger_middle(BB_PERIOD)
    is_in_sell_zone = (latest['close'] >= latest[bb_lower]) and (latest['close'] <= latest[bb_middle])
    is_stoch_sell = latest[stoch_k] > 70
    is_flow_sell = latest.get(obtr_name, 0) < latest.get(obtr_mid_band, -np.inf)
    
    wwma_200 = IndicatorNames.wwma(200)
    sinal_venda = (latest['close'] < latest.get(wwma_200, np.inf)) and is_in_sell_zone and is_stoch_sell and is_flow_sell

    motivo = "Aprovado" if (sinal_compra or sinal_venda) else "Sem gatilho técnico"

    return {
        'Sinal_Compra': bool(sinal_compra),
        'Sinal_Venda': bool(sinal_venda),
        'Stop_Loss_Sugerido_Long': float(latest[bb_lower]) if sinal_compra else None,
        'Stop_Loss_Sugerido_Short': float(latest[bb_upper]) if sinal_venda else None,
        'Motivo_Bloqueio': motivo
    }
