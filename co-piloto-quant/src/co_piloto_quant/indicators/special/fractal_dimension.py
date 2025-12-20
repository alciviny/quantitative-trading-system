import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True, fastmath=True)
def _sevcik_fd_window(values: np.ndarray) -> float:
    N = values.shape[0]
    if N < 2:
        return np.nan

    vmin = values[0]
    vmax = values[0]

    for i in range(1, N):
        if values[i] < vmin:
            vmin = values[i]
        elif values[i] > vmax:
            vmax = values[i]

    # Série constante → linha reta
    if vmax == vmin:
        return 1.0

    inv_range = 1.0 / (vmax - vmin)
    step_x = 1.0 / (N - 1)

    L = 0.0
    prev_y = (values[0] - vmin) * inv_range

    for i in range(1, N):
        y = (values[i] - vmin) * inv_range
        dy = y - prev_y
        L += np.sqrt(dy * dy + step_x * step_x)
        prev_y = y

    if L <= 0.0:
        return np.nan

    denom = np.log(2.0 * (N - 1))
    if denom == 0.0:
        return np.nan

    return 1.0 + (np.log(L) + np.log(2.0)) / denom


@njit(cache=True, fastmath=True)
def _rolling_fdi(prices: np.ndarray, window: int) -> np.ndarray:
    n = prices.shape[0]
    out = np.full(n, np.nan)

    for i in range(window - 1, n):
        out[i] = _sevcik_fd_window(prices[i - window + 1 : i + 1])

    return out


def calculate_rolling_fdi(
    close_prices: pd.Series,
    window: int = 30
) -> pd.Series:
    """
    Fractal Dimension Index (FDI) - Sevcik
    Implementação profissional otimizada com Numba.
    """
    values = close_prices.to_numpy(dtype=np.float64)
    fdi = _rolling_fdi(values, window)

    return pd.Series(
        fdi,
        index=close_prices.index,
        name=f"FDI_{window}"
    )
