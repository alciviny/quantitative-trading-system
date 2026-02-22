"""
Módulo de features: cálculo e engenharia de variáveis.
"""
import pandas as pd
from co_piloto_quant.data.indicator_engine import IndicatorEngine

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula e adiciona todos os indicadores técnicos disponíveis ao DataFrame.
    """
    engine = IndicatorEngine(df)

    # Lista de indicadores a serem calculados (pode ser expandida)
    indicadores = [
        # Indicadores clássicos
        ('bollinger_bands', {'period': 20, 'std_devs': [2.0, 3.0]}),
        ('ifr', {'period': 14}),
        ('ww_ma', {'period': 14}),
        ('system_tpm', {'indicator': 'obtr', 'period': 200, 'deviations': [0.45, 1.0, 1.5, 2.0]}),
        ('stochastic', {'k_period': 14, 'k_smooth': 3, 'd_smooth': 3}),
        # Indicadores avançados
        ('hurst', {'window': 72, 'kind': 'returns'}),
        ('entropy', {'window': 20}),
        ('volatility', {'period': 21}),
        ('half_life', {'window': 60}),
        ('ehlers_hilbert', {}),
        ('choppiness', {'window': 14}),
    ]

    for nome, params in indicadores:
        engine.add_indicator(nome, **params)

    return engine.get_data()
