import pandas as pd
import numpy as np
from co_piloto_quant.strategies.rules import check_rules

def test_check_rules_live():
    # Dados sintéticos com colunas mínimas
    data = pd.DataFrame({
        'close': [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119],
        'bb_lower_20_2.0': [95]*20,
        'bb_upper_20_2.0': [105]*20,
        'stoch_k_14_3': [10]*20,
        'obtr': [1]*20,
        'obtr_tpm_middle_200': [0]*20,
        'wad': [1]*20,
        'wad_tpm_middle_200': [0]*20,
        'bb_middle_20': [100]*20,
        'wwma_200': [100]*20,
        'hurst_z_20': [0.0]*20,
        'entropy_z_20': [0.0]*20
    })
    result = check_rules(data, mode='live')
    assert isinstance(result, dict)
    assert 'Sinal_Compra' in result
    assert 'Sinal_Venda' in result
    assert 'Motivo_Bloqueio' in result
