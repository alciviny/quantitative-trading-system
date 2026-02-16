import pandas as pd
import numpy as np
from co_piloto_quant.data.indicator_engine import IndicatorEngine

def test_indicator_engine_add_bollinger():
    data = pd.DataFrame({'close': np.random.normal(100, 1, 100),
                        'high': np.random.normal(101, 1, 100),
                        'low': np.random.normal(99, 1, 100)})
    engine = IndicatorEngine(data)
    engine.add_indicator('bollinger_bands', period=20, std_devs=[2.0])
    df = engine.get_data()
    assert any('bb_middle_20' in c for c in df.columns)
    assert any('bb_upper_20_2.0' in c for c in df.columns)
    assert any('bb_lower_20_2.0' in c for c in df.columns)

def test_indicator_engine_add_ifr():
    data = pd.DataFrame({'close': np.random.normal(100, 1, 100),
                        'high': np.random.normal(101, 1, 100),
                        'low': np.random.normal(99, 1, 100)})
    engine = IndicatorEngine(data)
    engine.add_indicator('ifr', period=14)
    df = engine.get_data()
    assert any('rsi_14' in c for c in df.columns)
