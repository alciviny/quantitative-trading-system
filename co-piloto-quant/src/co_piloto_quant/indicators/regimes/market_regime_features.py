"""
Market Regime Feature Engine
============================

Features institucionais para classificação de regimes de mercado.

Dimensões cobertas:
1. Volatilidade (nível + aceleração)
2. Direcionalidade estatística
3. Assimetria estrutural

Todas as funções:
- Usam log-retornos quando necessário
- São robustas a NaN
- São numericamente estáveis
"""

import numpy as np
import pandas as pd
from typing import Optional


# ==========================================================
# UTILIDADE INTERNA
# ==========================================================

def _log_returns(close: pd.Series) -> pd.Series:
    return np.log(close / close.shift(1))


# ==========================================================
# ===================== VOLATILIDADE =======================
# ==========================================================

def realized_volatility(
    close: pd.Series,
    window: int = 20,
    annualize: bool = False,
    trading_periods: int = 252
) -> pd.Series:
    """
    Realized Volatility via soma dos quadrados dos log-retornos.
    """
    returns = _log_returns(close)
    rv = np.sqrt((returns ** 2).rolling(window).sum())

    if annualize:
        rv *= np.sqrt(trading_periods)

    rv.name = f"RV_{window}"
    return rv


def volatility_of_volatility(
    rv: pd.Series,
    window: int = 20
) -> pd.Series:
    """
    Volatility of Volatility (aceleração de regime).
    """
    vov = rv.rolling(window).std(ddof=1)
    vov.name = f"VoV_{window}"
    return vov


def ewma_volatility(
    close: pd.Series,
    lambda_: float = 0.94,
    annualize: bool = False,
    trading_periods: int = 252
) -> pd.Series:
    """
    EWMA Volatility (RiskMetrics style).
    λ típico:
        0.94 diário
        0.97 semanal
    """
    returns = _log_returns(close).fillna(0.0)
    var = np.zeros(len(returns))

    var[0] = returns.iloc[0] ** 2

    for i in range(1, len(returns)):
        var[i] = lambda_ * var[i - 1] + (1 - lambda_) * returns.iloc[i] ** 2

    vol = np.sqrt(var)

    if annualize:
        vol *= np.sqrt(trading_periods)

    return pd.Series(vol, index=close.index, name="EWMA_VOL")


def efficiency_ratio(
    close: pd.Series,
    window: int = 20
) -> pd.Series:
    """
    Kaufman Efficiency Ratio.
    Mede direcionalidade vs ruído.
    """
    change = close.diff(window).abs()
    volatility = close.diff().abs().rolling(window).sum()

    er = change / volatility.replace(0, np.nan)
    er.name = f"Efficiency_{window}"

    return er


# ==========================================================
# ================= DIRECIONALIDADE ========================
# ==========================================================

def drift_t_stat(
    close: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    T-stat do drift (significância estatística da tendência).
    """
    returns = _log_returns(close)

    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std(ddof=1)

    t_stat = mean / (std / np.sqrt(window))
    t_stat.name = f"DriftT_{window}"

    return t_stat


def rolling_trend_strength(
    close: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    Força de tendência via regressão linear rolling.
    Normalizada pela volatilidade do preço.
    """
    y = np.log(close).values
    x = np.arange(len(y))

    slope = np.full(len(y), np.nan)

    for i in range(window - 1, len(y)):
        x_window = x[i - window + 1:i + 1]
        y_window = y[i - window + 1:i + 1]

        x_demean = x_window - x_window.mean()
        y_demean = y_window - y_window.mean()

        denom = np.sum(x_demean ** 2)
        if denom == 0:
            continue

        beta = np.sum(x_demean * y_demean) / denom
        slope[i] = beta

    trend = pd.Series(slope, index=close.index)

    norm = close.rolling(window).std(ddof=1)
    strength = trend / norm

    strength.name = f"TrendStrength_{window}"
    return strength


# ==========================================================
# ===================== ASSIMETRIA =========================
# ==========================================================

def rolling_skewness(
    close: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    Rolling skewness dos log-retornos.
    """
    returns = _log_returns(close)
    skew = returns.rolling(window).skew()

    skew.name = f"Skew_{window}"
    return skew


def rolling_kurtosis(
    close: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    Rolling kurtosis dos log-retornos.
    """
    returns = _log_returns(close)
    kurt = returns.rolling(window).kurt()

    kurt.name = f"Kurt_{window}"
    return kurt


def tail_risk_index(
    close: pd.Series,
    window: int = 50
) -> pd.Series:
    """
    Índice combinado de risco de cauda.
    Combina assimetria e excesso de kurtosis.
    """
    skew = rolling_skewness(close, window)
    kurt = rolling_kurtosis(close, window)

    excess_kurt = (kurt - 3).clip(lower=0)
    tri = np.abs(skew) + excess_kurt

    tri.name = f"TailRisk_{window}"
    return tri
