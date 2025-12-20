import numpy as np
import pandas as pd
from numba import njit


@njit(cache=True)
def _lz_complexity_binary(seq: np.ndarray) -> float:
    """
    Lempel-Ziv Complexity (LZ76) para sequência binária.
    """
    n = seq.size
    if n == 0:
        return np.nan

    i, k, l = 0, 1, 1
    c = 1

    while True:
        if seq[i + k - 1] != seq[l + k - 1]:
            if k > c:
                c = k
            i += 1
            if i == l:
                c += 1
                l += k
                if l >= n:
                    break
                i = 0
                k = 1
            else:
                k = 1
        else:
            k += 1
            if l + k > n:
                c += 1
                break

    return c


@njit(cache=True)
def _rolling_lzc(returns: np.ndarray, window: int) -> np.ndarray:
    n = returns.size
    out = np.full(n, np.nan)

    for i in range(window - 1, n):
        # Binarização: direção do retorno
        seq = np.zeros(window, dtype=np.int8)
        for j in range(window):
            seq[j] = 1 if returns[i - window + 1 + j] > 0 else 0

        c = _lz_complexity_binary(seq)

        # Normalização clássica
        if c > 0:
            out[i] = c * np.log2(window) / window
        else:
            out[i] = np.nan

    return out


def calculate_rolling_lzc(
    close_prices: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    Lempel–Ziv Complexity (LZC) – versão profissional.

    Mede a complexidade informacional do mercado.
    Valores normalizados em torno de [0.5 – 1.5].

    Interpretação:
    - LZC baixa  → estrutura / previsibilidade
    - LZC alta   → caos / saturação informacional
    """
    returns = close_prices.pct_change().to_numpy(dtype=np.float64)
    lzc = _rolling_lzc(returns, window)

    return pd.Series(
        lzc,
        index=close_prices.index,
        name=f"LZC_{window}"
    )
