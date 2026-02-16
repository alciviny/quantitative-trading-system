import pandas as pd
import numpy as np
from co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy
from co_piloto_quant.strategies.rules import check_rules

def test_mean_reversion_strategy_buy_sell():
    data = pd.DataFrame({
        'close': np.linspace(100, 120, 300),
        'vol_signal': ['CALM']*300,
        'Entropy_20': [2.0]*300,
        'VolVol_Z': [1.0]*300,
        'Entropy_Z': [0.5]*300,
        'rsi_120': np.concatenate([np.linspace(30, 70, 150), np.linspace(70, 30, 150)])
    })
    strategy = MeanReversionStrategy()
    result = strategy._calculate_signals(data)
    assert 'SIGNAL' in result.columns
    assert set(result['SIGNAL'].unique()).issubset({'BUY','SELL','HOLD'})
    assert 'STOP_LOSS' in result.columns

def test_check_rules_vectorized():
    data = pd.DataFrame({
        'close': np.linspace(100, 120, 100),
        'bb_lower_20_2.0': [95]*100,
        'bb_upper_20_2.0': [105]*100,
        'stoch_k_14_3': [10]*100,
        'obtr': [1]*100,
        'obtr_tpm_middle_200': [0]*100,
        'wad': [1]*100,
        'wad_tpm_middle_200': [0]*100,
        'bb_middle_20': [100]*100,
        'wwma_200': [100]*100,
        'hurst_z_20': [0.0]*100,
        'entropy_z_20': [0.0]*100
    })
    result = check_rules(data, mode='vectorized')
    assert isinstance(result, dict)
    assert 'entries' in result
    assert 'exits' in result
    assert 'short_entries' in result
    assert 'short_exits' in result
