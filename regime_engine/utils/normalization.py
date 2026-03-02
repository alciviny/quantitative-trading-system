import pandas as pd

def rolling_zscore(series, window=252):
    mean = series.shift(1).rolling(window).mean()
    std  = series.shift(1).rolling(window).std()
    return (series - mean) / (std + 1e-8)
