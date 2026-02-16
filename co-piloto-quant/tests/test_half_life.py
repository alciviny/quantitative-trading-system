import pandas as pd
import numpy as np
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params

def test_calculate_rolling_ou_params_basic():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
    result = calculate_rolling_ou_params(data, window=20)
    assert isinstance(result, pd.DataFrame)
    assert any(col.startswith('half_life') for col in result.columns)
    assert len(result) == len(data)
    half_life_col = [col for col in result.columns if col.startswith('half_life')][0]
    assert (result[half_life_col].dropna() >= 0).all()

def test_calculate_rolling_ou_params_nan():
    data = pd.Series([np.nan]*10 + list(np.arange(20)))
    result = calculate_rolling_ou_params(data, window=10)
    # Procura a coluna correta com prefixo 'half_life'
    half_life_col = [col for col in result.columns if col.startswith('half_life')][0]
    # O cálculo preenche os primeiros valores com 1000.0 em vez de NaN
    # Verifica se pelo menos os 10 primeiros valores são 1000.0 (indicando ausência de cálculo válido)
    assert (result[half_life_col].iloc[:10] == 1000.0).all()
