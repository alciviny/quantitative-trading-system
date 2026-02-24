"""
Módulo de features: cálculo e engenharia de variáveis.
"""

import pandas as pd
from co_piloto_quant.data.indicator_engine import IndicatorEngine
from co_piloto_quant.config import (
    BB_PERIOD, PRICE_BB_DEVIATIONS, IFR_PERIOD, SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
    STOCH_K_PERIOD, STOCH_K_SMOOTH, STOCH_D_SMOOTH, HURST_WINDOW, ENTROPY_WINDOW
)

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula e adiciona todos os indicadores técnicos disponíveis ao DataFrame.
    """
    engine = IndicatorEngine(df)

    # Lista de indicadores a serem calculados (pode ser expandida)
    indicadores = [
        # Indicadores clássicos
        ('bollinger_bands', {'period': BB_PERIOD, 'std_devs': PRICE_BB_DEVIATIONS}),
        ('ifr', {'period': IFR_PERIOD}),
        ('ww_ma', {'period': IFR_PERIOD}),  # WWMA geralmente usa mesmo período do IFR
        ('system_tpm', {'indicator': 'obtr', 'period': SYSTEM_PERIOD, 'deviations': SYSTEM_DEVIATIONS}),
        ('stochastic', {'k_period': STOCH_K_PERIOD, 'k_smooth': STOCH_K_SMOOTH, 'd_smooth': STOCH_D_SMOOTH}),
        # Indicadores avançados
        ('hurst', {'window': HURST_WINDOW, 'kind': 'returns'}),
        ('entropy', {'window': ENTROPY_WINDOW}),
        ('directional_entropy', {'window': 21}),
        ('path_elasticity', {'window': 21}),
        ('volatility', {'period': 21}),  # Valor fixo, pode ser centralizado se desejar
        ('half_life', {'window': 60}),   # Valor fixo, pode ser centralizado se desejar
        ('ehlers_hilbert', {}),
        ('choppiness', {'window': 14}),  # Valor fixo, pode ser centralizado se desejar
    ]

    for nome, params in indicadores:
        engine.add_indicator(nome, **params)

    return engine.get_data()
