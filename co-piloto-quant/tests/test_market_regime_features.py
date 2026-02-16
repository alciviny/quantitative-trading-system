import pandas as pd
import numpy as np
from co_piloto_quant.indicators.regimes.market_regime_features import realized_volatility, efficiency_ratio, drift_t_stat, rolling_trend_strength, rolling_skewness, rolling_kurtosis, tail_risk_index

def test_realized_volatility():
    data = pd.Series(np.random.normal(100, 1, 100))
    rv = realized_volatility(data, window=10)
    assert isinstance(rv, pd.Series)
    assert len(rv) == len(data)
    assert (rv.dropna() >= 0).all()

def test_efficiency_ratio():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
    er = efficiency_ratio(data, window=10)
    assert isinstance(er, pd.Series)
    assert len(er) == len(data)
    assert (er.dropna() >= 0).all()
    assert (er.dropna() <= 1).all()

def test_drift_t_stat():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
    tstat = drift_t_stat(data, window=10)
    assert isinstance(tstat, pd.Series)
    assert len(tstat) == len(data)

def test_rolling_trend_strength():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 100)))
    ts = rolling_trend_strength(data, window=10)
    assert isinstance(ts, pd.Series)
    assert len(ts) == len(data)

def test_rolling_skewness():
    data = pd.Series(np.random.normal(0, 1, 100))
    skew = rolling_skewness(data, window=10)
    assert isinstance(skew, pd.Series)
    assert len(skew) == len(data)

def test_rolling_kurtosis():
    data = pd.Series(np.random.normal(0, 1, 100))
    kurt = rolling_kurtosis(data, window=10)
    assert isinstance(kurt, pd.Series)
    assert len(kurt) == len(data)

def test_tail_risk_index():
    data = pd.Series(np.random.normal(0, 1, 100))
    tri = tail_risk_index(data, window=10)
    assert isinstance(tri, pd.Series)
    assert len(tri) == len(data)
