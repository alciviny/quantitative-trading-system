import pandas as pd
import numpy as np
from co_piloto_quant.indicators.special.fractal_dimension import calculate_rolling_fdi

def test_calculate_rolling_fdi_basic():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
    result = calculate_rolling_fdi(data, window=20)
    assert isinstance(result, pd.Series)
    assert len(result) == len(data)
    assert (result.dropna() >= 0).all()
    assert (result.dropna() <= 2).all()

def test_calculate_rolling_fdi_nan():
    data = pd.Series([np.nan]*10 + list(np.arange(20)))
    result = calculate_rolling_fdi(data, window=10)
    assert result.isnull().sum() >= 9
