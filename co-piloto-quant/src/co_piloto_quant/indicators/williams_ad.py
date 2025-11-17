import pandas as pd
import numpy as np

def williams_ad(data: pd.DataFrame, smooth_period: int = None) -> pd.Series:
    """
    Calcula o indicador Williams Accumulation/Distribution (A/D).

    Este indicador mede a pressão de compra e venda acumulada, multiplicando
    a variação de preço pelo volume.

    Args:
        data (pd.DataFrame): DataFrame contendo os dados de preço e volume.
                             Deve conter as colunas 'high', 'low', 'close', 'volume'.
        smooth_period (int, optional): O período para suavização opcional
                                       usando a Média Móvel de Wilder.
                                       Defaults to None.

    Returns:
        pd.Series: Uma série contendo o valor do Williams A/D (suavizado ou não).
    
    Raises:
        ValueError: Se as colunas necessárias não forem encontradas.
    """
    required_cols = ['high', 'low', 'close', 'volume']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"Input DataFrame must contain {required_cols} columns. Found: {data.columns.tolist()}")

    close = data['close']
    high = data['high']
    low = data['low']
    volume = data['volume']
    
    close_yesterday = close.shift(1)

 
    true_range_high = np.maximum(high, close_yesterday)
    true_range_low = np.minimum(low, close_yesterday)

    
    conditions = [
        close > close_yesterday,
        close < close_yesterday,
    ]
    choices = [
        close - true_range_low,
        close - true_range_high,
    ]
    price_change = np.select(conditions, choices, default=0.0)

 
    ad_today = price_change * volume
    williams_ad_series = ad_today.cumsum()
    williams_ad_series.name = 'williams_ad'

    if smooth_period is not None:
        wilder_smooth = williams_ad_series.ewm(alpha=1/smooth_period, adjust=False).mean()
        wilder_smooth.name = f'williams_ad_wilder_{smooth_period}'
        return wilder_smooth
    
    return williams_ad_series
