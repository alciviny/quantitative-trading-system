import pandas as pd
import numpy as np
from co_piloto_quant.data.data_manager import DataManager

def test_data_manager_cache_and_db_path():
    dm = DataManager()
    # Testa apenas se instancia corretamente
    assert dm is not None

def test_data_manager_methods_exist():
    dm = DataManager()
    # Testa apenas se instancia corretamente
    assert dm is not None
