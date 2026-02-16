import pandas as pd
import numpy as np
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average

def test_ww_moving_average_basic():
    data = pd.DataFrame({'close': np.random.normal(100, 1, 100)})
    result = ww_moving_average(data, column='close', period=20)
    assert isinstance(result, pd.DataFrame)
    assert result.shape[0] == 100
    assert result.columns[0].startswith('wwma_')

def test_ww_moving_average_missing_column():
    data = pd.DataFrame({'open': np.random.normal(100, 1, 100)})
    try:
        ww_moving_average(data, column='close', period=20)
        assert False, 'Deveria lançar ValueError para coluna ausente'
    except ValueError:
        pass
