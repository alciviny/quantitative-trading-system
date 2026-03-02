import numpy as np

def rolling_zscore(series, window):
    """Calcula o z-score rolling de uma série."""
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    z = (series - mean) / (std + 1e-8)
    return z

def robust_zscore(series, window):
    """Calcula o z-score robusto (mediana/MAD) rolling de uma série."""
    median = series.rolling(window).median()
    mad = series.rolling(window).apply(lambda x: np.median(np.abs(x - np.median(x))))
    # Proteção: se MAD for muito pequeno, retorna zero para evitar explosão
    min_mad = 1e-3
    denom = mad.copy()
    denom[denom < min_mad] = np.nan  # ou zero, se preferir z-score neutro
    z = (series - median) / denom
    z = z.fillna(0)  # z-score neutro onde não há variação
    return z
