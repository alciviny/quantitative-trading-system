import pandas as pd
import numpy as np
from co_piloto_quant.indicators.regimes.market_regime_features import realized_volatility, volatility_of_volatility, ewma_volatility, efficiency_ratio, drift_t_stat, rolling_trend_strength, rolling_skewness, rolling_kurtosis, tail_risk_index

def test_volatility_of_volatility():
    data = pd.Series(np.random.normal(100, 1, 100))
    rv = realized_volatility(data, window=10)
    vov = volatility_of_volatility(rv, window=5)
    assert isinstance(vov, pd.Series)
    assert len(vov) == len(data)
    assert (vov.dropna() >= 0).all()

def test_ewma_volatility():
    data = pd.Series(np.random.normal(100, 1, 100))
    ewma = ewma_volatility(data, lambda_=0.94)
    assert isinstance(ewma, pd.Series)
    assert len(ewma) == len(data)
    assert (ewma.dropna() >= 0).all()
