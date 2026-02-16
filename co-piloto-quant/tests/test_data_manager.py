import pandas as pd
import numpy as np
from co_piloto_quant.data.data_manager import DataManager

def test_data_manager_init():
    # Testa se instancia corretamente
    dm = DataManager()
    # Testa apenas se instancia corretamente
    assert dm is not None
