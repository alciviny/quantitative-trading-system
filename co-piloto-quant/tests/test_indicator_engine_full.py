import pandas as pd
import numpy as np
import pytest
from co_piloto_quant.data.indicator_engine import IndicatorEngine

def test_indicator_engine_add_multiple_indicators():
    data = pd.DataFrame({
        'close': np.random.normal(100, 1, 100),
        'high': np.random.normal(101, 1, 100),
        'low': np.random.normal(99, 1, 100)
    })
    engine = IndicatorEngine(data)
    engine.add_indicator('bollinger_bands', period=20, std_devs=[2.0])
    engine.add_indicator('ifr', period=14)
    engine.add_indicator('ww_ma', period=20)
    engine.add_indicator('hurst', window=20)
    engine.add_indicator('entropy', window=20)
    df = engine.get_data()
    # Checa se as colunas principais foram adicionadas
    assert any('bb_middle_20' in c for c in df.columns)
    assert any('rsi_14' in c for c in df.columns)
    assert any('wwma_20' in c for c in df.columns)
    assert any('hurst' in c for c in df.columns)
    assert any('entropy' in c for c in df.columns)

def test_indicator_engine_invalid_indicator():
    data = pd.DataFrame({'close': np.random.normal(100, 1, 10), 'high': np.random.normal(101, 1, 10), 'low': np.random.normal(99, 1, 10)})
    engine = IndicatorEngine(data)
    # Não deve lançar erro, apenas warning
    engine.add_indicator('inexistente')
    df = engine.get_data()
    assert isinstance(df, pd.DataFrame)
