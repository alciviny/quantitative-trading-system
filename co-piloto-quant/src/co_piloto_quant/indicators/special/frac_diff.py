# src/co_piloto_quant/indicators/special/frac_diff.py
"""
Fractional Differentiation Indicators

Implementa diferenciação fracionária com janela fixa, adequada para:
- Backtests vetorizados
- Trading ao vivo (janela limitada)
- Indicadores técnicos estacionarizados

Baseado em:
- Marcos López de Prado (Advances in Financial Machine Learning)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ============================================================================
# PESOS DA DIFERENCIAÇÃO FRACIONÁRIA
# ============================================================================

@lru_cache(maxsize=128)
def _get_fracdiff_weights(d: float, window: int) -> np.ndarray:
    """
    Gera e cacheia os pesos da diferenciação fracionária.

    Parameters
    ----------
    d : float
        Ordem da diferenciação fracionária.
    window : int
        Tamanho da janela fixa.

    Returns
    -------
    np.ndarray
        Vetor coluna (window x 1) com os pesos invertidos.
    """
    if window < 2:
        raise ValueError("window deve ser >= 2")

    w = np.empty(window, dtype=np.float64)
    w[0] = 1.0

    for k in range(1, window):
        w[k] = -w[k - 1] * (d - k + 1) / k

    return w[::-1].reshape(-1, 1)


# ============================================================================
# DIFERENCIAÇÃO FRACIONÁRIA — JANELA FIXA
# ============================================================================

def fractional_diff_fixed_window(
    series: pd.Series,
    d: float = 0.4,
    window: int = 20,
    min_periods: Optional[int] = None,
) -> pd.Series:
    """
    Aplica diferenciação fracionária usando janela fixa.

    Esta abordagem:
    - Preserva memória longa parcialmente
    - Garante estacionariedade parcial
    - É adequada para execução em tempo real

    Parameters
    ----------
    series : pd.Series
        Série temporal de entrada.
    d : float, default=0.4
        Ordem da diferenciação fracionária (0 < d < 1 típico).
    window : int, default=20
        Tamanho da janela fixa.
    min_periods : int, optional
        Número mínimo de observações para cálculo.
        Default = window.

    Returns
    -------
    pd.Series
        Série diferenciada fracionariamente.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("series deve ser um pd.Series")

    if not 0 <= d <= 1:
        raise ValueError("d deve estar no intervalo [0, 1]")

    if window < 2:
        raise ValueError("window deve ser >= 2")

    if min_periods is None:
        min_periods = window

    # Remove NaNs iniciais
    series = series.astype(np.float64)

    # Pesos (cacheados)
    weights = _get_fracdiff_weights(d, window)

    logger.debug(
        "Aplicando fracdiff | d=%.3f | window=%d | min_periods=%d",
        d, window, min_periods
    )

    # Aplicação via rolling (numpy dot)
    output = series.rolling(
        window=window,
        min_periods=min_periods
    ).apply(
        lambda x: np.dot(x, weights)[0],
        raw=True
    )

    output.name = f"{series.name}_fracdiff_d{d}_w{window}"
    return output
