from src import etl
import pandas as pd

def test_load_and_save_parquet(tmp_path):
    df = pd.DataFrame({'a': [1, 2], 'b': [3, 4]})
    file = tmp_path / 'test.parquet'
    etl.save_parquet(df, file)
    df2 = etl.load_parquet(file)
    assert df2.equals(df)
