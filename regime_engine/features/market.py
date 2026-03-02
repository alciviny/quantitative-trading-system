import numpy as np
import pandas as pd

def add_market_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona features de mercado ao DataFrame.
    """
    def _log_returns(close):
        return np.log(close / close.shift(1))

    # Realized volatility
    if 'close' in df.columns:
        window = 20
        returns = _log_returns(df['close'])
        df['realized_volatility'] = np.sqrt((returns ** 2).rolling(window).sum())

    # Volatility of volatility
    if 'realized_volatility' in df.columns:
        df['volatility_of_volatility'] = df['realized_volatility'].rolling(window).std(ddof=1)

    # Efficiency ratio (Kaufman)
    if 'close' in df.columns:
        window = 20
        change = df['close'].diff(window).abs()
        volatility = df['close'].diff().abs().rolling(window).sum()
        df['efficiency_ratio'] = change / (volatility + 1e-8)

    # Rolling trend strength (exemplo: zscore do retorno acumulado)
    if 'close' in df.columns:
        window = 20
        df['rolling_trend_strength'] = (df['close'].pct_change(window) - df['close'].pct_change(window).mean()) / (df['close'].pct_change(window).std() + 1e-8)

    # Drift t-stat (exemplo simplificado)
    if 'close' in df.columns:
        window = 20
        returns = df['close'].pct_change()
        mean = returns.rolling(window).mean()
        std = returns.rolling(window).std()
        df['drift_t_stat'] = mean / (std / np.sqrt(window) + 1e-8)

    # Market entropy (exemplo simplificado)
    if 'close' in df.columns:
        window = 20
        returns = df['close'].pct_change()
        def rolling_entropy(x):
            h = np.histogram(x, bins=10)[0]
            s = np.sum(h)
            if s > 0:
                return -np.sum((h / s) * np.log((h / s) + 1e-8))
            else:
                return np.nan
        entropy = returns.rolling(window).apply(rolling_entropy, raw=True)
        df['market_entropy'] = entropy

    # Hurst (placeholder, pois cálculo real é mais complexo)
    if 'close' in df.columns:
        window = 72
        def hurst_exponent(ts):
            N = len(ts)
            if N < 20:
                return np.nan
            lags = range(2, 20)
            tau = [np.std(np.subtract(ts[lag:], ts[:-lag])) for lag in lags]
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            return poly[0]
        df['hurst'] = df['close'].rolling(window).apply(hurst_exponent, raw=True)

    # Retornos
    if 'close' in df.columns:
        df['returns'] = df['close'].pct_change()

    return df
