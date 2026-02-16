import pandas as pd
import numpy as np
from co_piloto_quant.indicators.regimes.market_regime_features import realized_volatility, volatility_of_volatility, ewma_volatility, efficiency_ratio, drift_t_stat, rolling_trend_strength, rolling_skewness, rolling_kurtosis, tail_risk_index

def test_realized_volatility_full():
    data = pd.Series(np.random.normal(100, 1, 200))
    rv = realized_volatility(data, window=20, annualize=True)
    assert isinstance(rv, pd.Series)
    assert len(rv) == len(data)
    assert (rv.dropna() >= 0).all()

def test_volatility_of_volatility_full():
    data = pd.Series(np.random.normal(100, 1, 200))
    rv = realized_volatility(data, window=20)
    vov = volatility_of_volatility(rv, window=10)
    assert isinstance(vov, pd.Series)
    assert len(vov) == len(data)
    assert (vov.dropna() >= 0).all()

def test_ewma_volatility_full():
    data = pd.Series(np.random.normal(100, 1, 200))
    ewma = ewma_volatility(data, lambda_=0.97, annualize=True)
    assert isinstance(ewma, pd.Series)
    assert len(ewma) == len(data)
    assert (ewma.dropna() >= 0).all()

def test_efficiency_ratio_full():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 200)))
    er = efficiency_ratio(data, window=20)
    assert isinstance(er, pd.Series)
    assert len(er) == len(data)
    assert (er.dropna() >= 0).all()
    assert (er.dropna() <= 1).all()

def test_drift_t_stat_full():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 200)))
    tstat = drift_t_stat(data, window=20)
    assert isinstance(tstat, pd.Series)
    assert len(tstat) == len(data)

def test_rolling_trend_strength_full():
    data = pd.Series(np.cumsum(np.random.normal(0, 1, 200)))
    ts = rolling_trend_strength(data, window=20)
    assert isinstance(ts, pd.Series)
    assert len(ts) == len(data)

def test_rolling_skewness_full():
    data = pd.Series(np.random.normal(0, 1, 200))
    skew = rolling_skewness(data, window=20)
    assert isinstance(skew, pd.Series)
    assert len(skew) == len(data)

def test_rolling_kurtosis_full():
    data = pd.Series(np.random.normal(0, 1, 200))
    kurt = rolling_kurtosis(data, window=20)
    assert isinstance(kurt, pd.Series)
    assert len(kurt) == len(data)

def test_tail_risk_index_full():
    data = pd.Series(np.random.normal(0, 1, 200))
    tri = tail_risk_index(data, window=20)
    assert isinstance(tri, pd.Series)
    assert len(tri) == len(data)
