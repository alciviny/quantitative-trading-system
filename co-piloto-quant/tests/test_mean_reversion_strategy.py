import pandas as pd
import numpy as np
from co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy

def test_mean_reversion_strategy_basic():
    # Gera dados sintéticos
    data = pd.DataFrame({
        'close': np.random.normal(100, 1, 300),
        'vol_signal': ['CALM']*300,
        'Entropy_20': [2.0]*300,
        'VolVol_Z': [1.0]*300,
        'Entropy_Z': [0.5]*300
    })
    # Adiciona colunas necessárias
    data['rsi_120'] = np.random.uniform(30, 70, 300)
    strategy = MeanReversionStrategy()
    result = strategy._calculate_signals(data)
    assert 'SIGNAL' in result.columns
    assert set(result['SIGNAL'].unique()).issubset({'BUY','SELL','HOLD'})
    assert 'STOP_LOSS' in result.columns
