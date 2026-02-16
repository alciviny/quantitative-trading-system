import pandas as pd
import numpy as np
import pytest
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst

def test_calculate_rolling_hurst_basic():
    # Série simples com tendência
    data = pd.Series(np.arange(100) + np.random.normal(0, 1, 100))
    result = calculate_rolling_hurst(data, window=20)
    assert isinstance(result, pd.Series)
    assert len(result) == len(data)
    # Hurst deve estar entre 0 e 1 (exceto NaN iniciais)
    assert result.dropna().between(0, 1).all()

def test_calculate_rolling_hurst_nan():
    # Série com NaNs
    data = pd.Series([np.nan]*10 + list(np.arange(20)))
    result = calculate_rolling_hurst(data, window=10)
    assert result.isnull().sum() >= 10
    assert (result.dropna() >= 0).all()
    assert (result.dropna() <= 1).all()

def test_calculate_rolling_hurst_constant():
    # Série constante
    data = pd.Series([5.0]*50)
    result = calculate_rolling_hurst(data, window=10)
    # Hurst de série constante deve ser NaN ou próximo de 0.5
    assert (result.dropna() >= 0).all()
    assert (result.dropna() <= 1).all()
