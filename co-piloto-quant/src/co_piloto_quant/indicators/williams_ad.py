import pandas as pd

def williams_ad(data: pd.DataFrame, smooth_period: int = None) -> pd.Series:
    """
    Calculates the Williams Accumulation/Distribution (A/D) indicator,
    with an optional Welles Wilder's smoothing.

    Args:
        data (pd.DataFrame): DataFrame with 'High', 'Low', 'Close', and 'Volume' columns.
        smooth_period (int, optional): The period for Welles Wilder's smoothing. 
                                       If None, raw A/D is returned. Defaults to None.

    Returns:
        pd.Series: A pandas Series with the Williams A/D values, smoothed if period is provided.
    """
    # Make a copy to avoid modifying the original DataFrame and normalize column names
    data = data.copy()
    data.rename(columns={
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume'
    }, inplace=True)

    if not all(col in data.columns for col in ['High', 'Low', 'Close', 'Volume']):
        raise ValueError("Input DataFrame must contain 'High', 'Low', 'Close', and 'Volume' columns.")

    close_yesterday = data['Close'].shift(1)

    true_range_high = pd.concat([data['High'], close_yesterday], axis=1).max(axis=1)
    true_range_low = pd.concat([data['Low'], close_yesterday], axis=1).min(axis=1)

    price_change = pd.Series(0.0, index=data.index)

    # Close > Yesterday's Close
    price_change[data['Close'] > close_yesterday] = data['Close'] - true_range_low

    # Close < Yesterday's Close
    price_change[data['Close'] < close_yesterday] = data['Close'] - true_range_high

    ad_today = price_change * data['Volume']

    williams_ad_series = ad_today.cumsum()
    williams_ad_series.name = 'williams_ad'

    if smooth_period is not None:
        # A suavização de Welles Wilder é uma Média Móvel Exponencial (EMA) com alpha = 1 / período.
        # Usamos adjust=False para corresponder à fórmula recursiva padrão usada em plataformas de trading.
        wilder_smooth = williams_ad_series.ewm(alpha=1/smooth_period, adjust=False).mean()
        wilder_smooth.name = f'williams_ad_wilder_{smooth_period}'
        return wilder_smooth
    
    return williams_ad_series
