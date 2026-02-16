import pandas as pd
import numpy as np
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy

def test_calculate_rolling_entropy_basic():
    data = pd.Series(np.random.normal(100, 1, 100))
    result = calculate_rolling_entropy(data, window=20)
    assert isinstance(result, pd.Series)
    assert len(result) == len(data)
    assert (result.dropna() >= 0).all()

def test_calculate_rolling_entropy_constant():
    data = pd.Series([100.0]*50)
    result = calculate_rolling_entropy(data, window=10)
    assert (result.dropna() == 0).all()
