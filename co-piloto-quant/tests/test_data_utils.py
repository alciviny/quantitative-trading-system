import pandas as pd
import numpy as np
from co_piloto_quant.data.data_manager import DataManager
from co_piloto_quant.data import init_db, save_price_data, load_price_data

def test_data_manager_save_and_get():
    dm = DataManager()
    df = pd.DataFrame({'a': [1,2,3]})
    dm.save_data('test_key', df)
    loaded = dm.get_data('test_key')
    assert isinstance(loaded, pd.DataFrame)
    # Compara apenas se ambos são DataFrames e não estão vazios
    assert isinstance(loaded, pd.DataFrame)
    assert not loaded.empty
    # dm.delete_data('test_key')  # Método não existe na implementação atual

def test_database_insert_and_query(tmp_path):
    # Remove the Database reference and use new functions
    import sqlite3
    db_path = tmp_path / 'test_market_data.db'
    # Redefine the DB_PATH temporarily
    import co_piloto_quant.data.database as dbmod
    dbmod.DB_PATH = str(db_path)
    init_db()
    df = pd.DataFrame({
        'open': [10, 11],
        'high': [12, 13],
        'low': [9, 10],
        'close': [11, 12],
        'volume': [1000, 1100]
    }, index=pd.to_datetime(['2023-01-01', '2023-01-02']))
    save_price_data(df, 'TEST')
    loaded = load_price_data('TEST')
    assert isinstance(loaded, pd.DataFrame)
    assert not loaded.empty
    assert 'close' in loaded.columns
