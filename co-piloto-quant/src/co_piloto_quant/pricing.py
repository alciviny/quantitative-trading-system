"""
Módulo de Precificação de Opções (Pricing Engine) — PRODUCTION READY v2
Implementa Black-Scholes-Merton (BSM), Gregas e Solver de Volatilidade.

Melhorias:
- NaN Propagation: Retorna estrutura de NaNs se a vol for inválida (evita crash downstream).
- Logging Ajustado: Debug para dados sujos, Warning apenas para falha de solver.
- Docstrings: Explica explicitamente o payoff no vencimento (Cash, sem desconto).
- Mid-Price Helper: Utilitário para lidar com spread B3.

Dependências: scipy, numpy, pandas, logging
"""

from __future__ import annotations
import math
import logging
from dataclasses import dataclass
from typing import Union, Dict, Optional, Tuple, List

import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq

# Configuração de Logger
logger = logging.getLogger(__name__)

# Tipo customizado para aceitar float ou array numpy/pandas
Numeric = Union[float, np.ndarray, pd.Series]

# Constante para evitar divisão por zero (epsilon)
EPS = 1e-9

def _to_years(days: Numeric, business_days: int = 252) -> Numeric:
    """
    Converte dias úteis para anos.
    
    CRÍTICO:
    - O input `days` DEVE ser calculado usando um calendário de DIAS ÚTEIS.
    """
    return np.maximum(days, 0) / float(business_days)


def get_mid_price(bid: float, ask: float, last: float) -> float:
    """
    Calcula o Mid-Price. Fallback para Last se spread for inválido.
    """
    if bid > 0 and ask > 0 and bid < ask:
        return (bid + ask) / 2.0
    return last


def _d1_d2(S: Numeric, K: Numeric, T: Numeric, r: Numeric, q: Numeric, sigma: Numeric) -> Tuple[Numeric, Numeric]:
    """Cálculo auxiliar de d1 e d2 protegido contra divisão por zero."""
    T_safe = np.maximum(T, EPS)
    sigma_safe = np.maximum(sigma, EPS)

    with np.errstate(divide='ignore', invalid='ignore'):
        d1 = (np.log(S / K) + (r - q + 0.5 * sigma_safe ** 2) * T_safe) / (sigma_safe * np.sqrt(T_safe))
        d2 = d1 - sigma_safe * np.sqrt(T_safe)

    return d1, d2


def black_scholes(
    S: Numeric,
    K: Numeric,
    T: Numeric,
    r: Numeric,
    sigma: Numeric,
    option_type: str = 'call',
    q: Numeric = 0.0,
) -> Numeric:
    """
    Calcula o PREÇO TEÓRICO (Black-Scholes-Merton).
    
    NOTA SOBRE VENCIMENTO (T=0):
    Retorna o Payoff Cash imediato (Valor Intrínseco). 
    Não aplica desconto a valor presente para T=0, pois a liquidação é considerada imediata.
    Se precisar de Valuation Intradiário com desconto, use: intrinsic * exp(-r * dt).
    """
    d1, d2 = _d1_d2(S, K, T, r, q, sigma)

    T_arr = np.asarray(T)
    is_expired = T_arr == 0 if T_arr.shape != () else (T == 0)

    if option_type.lower().startswith('c'):
        price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)

    # Tratamento de Expiração (T=0)
    try:
        if np.any(is_expired):
            intrinsic = np.where(option_type.lower().startswith('c'), 
                               np.maximum(S - K, 0.0), 
                               np.maximum(K - S, 0.0))
            price = np.where(is_expired, intrinsic, price)
    except Exception:
        if is_expired:
            price = max(S - K, 0.0) if option_type.lower().startswith('c') else max(K - S, 0.0)

    return price


def calculate_greeks(
    S: Numeric,
    K: Numeric,
    T: Numeric,
    r: Numeric,
    sigma: Numeric,
    option_type: str = 'call',
    q: Numeric = 0.0,
    theta_convention: str = 'calendar', 
    gamma_cap: Optional[float] = 1000.0,
) -> Dict[str, Numeric]:
    """
    Calcula Gregas: Delta, Gamma, Vega (%), Theta (dia), Rho.
    """
    # PROPAGAÇÃO EXPLÍCITA DE NaN
    # Se sigma for NaN (ou array de NaNs), retorna dicionário de NaNs para evitar erros downstream.
    if np.any(np.isnan(sigma)):
        if np.isscalar(sigma):
            nan_val = float('nan')
            return {'delta': nan_val, 'gamma': nan_val, 'vega': nan_val, 'theta': nan_val, 'rho': nan_val}
        else:
            # Se for array, deixamos o numpy propagar naturalmete no d1/d2, 
            # mas se quiser forçar tudo NaN caso um falhe (comportamento rígido), descomente abaixo.
            # Por padrão, vamos deixar o vetor processar os válidos e NaN nos inválidos.
            pass

    T_safe = np.maximum(T, EPS)
    d1, d2 = _d1_d2(S, K, T_safe, r, q, sigma)

    pdf_d1 = norm.pdf(d1)
    cdf_d1 = norm.cdf(d1)
    cdf_d2 = norm.cdf(d2)

    # --- DELTA ---
    if option_type.lower().startswith('c'):
        delta = np.exp(-q * T_safe) * cdf_d1
    else:
        delta = np.exp(-q * T_safe) * (cdf_d1 - 1)

    # --- GAMMA ---
    denom = S * sigma * np.sqrt(T_safe)
    gamma = (np.exp(-q * T_safe) * pdf_d1) / np.maximum(denom, EPS)
    
    if gamma_cap is not None:
        gamma = np.clip(gamma, -abs(gamma_cap), abs(gamma_cap))

    # --- VEGA (%) ---
    vega_abs = S * np.exp(-q * T_safe) * pdf_d1 * np.sqrt(T_safe)
    vega_pct = vega_abs / 100.0

    # --- THETA (dia) ---
    term1 = -(S * np.exp(-q * T_safe) * pdf_d1 * sigma) / (2 * np.sqrt(T_safe))
    if option_type.lower().startswith('c'):
        term2 = -r * K * np.exp(-r * T_safe) * cdf_d2
        term3 = q * S * np.exp(-q * T_safe) * cdf_d1
        theta_yearly = term1 + term2 - term3
    else:
        term2 = r * K * np.exp(-r * T_safe) * norm.cdf(-d2)
        term3 = q * S * np.exp(-q * T_safe) * norm.cdf(-d1)
        theta_yearly = term1 + term2 + term3

    divisor = 365.0 if theta_convention == 'calendar' else 252.0
    theta_daily = theta_yearly / divisor

    # --- RHO ---
    if option_type.lower().startswith('c'):
        rho = K * T_safe * np.exp(-r * T_safe) * cdf_d2
    else:
        rho = -K * T_safe * np.exp(-r * T_safe) * norm.cdf(-d2)
    rho = rho / 100.0

    return {
        'delta': delta, 'gamma': gamma, 'vega': vega_pct, 'theta': theta_daily, 'rho': rho
    }


def implied_volatility(
    price: float,
    S: float,
    K: float,
    T: float,
    r: float,
    option_type: str = 'call',
    q: float = 0.0,
    sigma_bounds: Tuple[float, float] = (1e-4, 5.0),
    xtol: float = 1e-6,
) -> float:
    """
    Calcula a VOLATILIDADE IMPLÍCITA (IV) via Brent-q.
    Retorna np.nan se falhar.
    """
    if T <= 0 or price <= 0:
        return float('nan')

    # Verifica arbitragem (Preço < Intrínseco)
    intrinsic = max(0.0, S - K) if option_type.lower().startswith('c') else max(0.0, K - S)
    
    # DEBUG: Loga como debug (dado sujo) em vez de warning (erro de sistema)
    if price < intrinsic - 1e-12:
        logger.debug(f"IV Skip: Preço abaixo do intrínseco. S={S}, K={K}, Price={price}, Intr={intrinsic:.2f}")
        return float('nan')

    low_sigma, high_sigma = sigma_bounds
    try:
        price_low = black_scholes(S, K, T, r, low_sigma, option_type, q)
        price_high = black_scholes(S, K, T, r, high_sigma, option_type, q)
    except Exception as e:
        logger.error(f"Erro crítico verificando bounds de IV: {e}")
        return float('nan')

    p_min, p_max = min(price_low, price_high), max(price_low, price_high)

    if not (p_min - 1e-12 <= price <= p_max + 1e-12):
        logger.debug(f"IV Skip: Preço {price} fora do alcance da vol [{low_sigma}-{high_sigma}].")
        return float('nan')

    def objective(sigma_guess: float) -> float:
        return black_scholes(S, K, T, r, sigma_guess, option_type, q) - price

    try:
        iv = brentq(objective, low_sigma, high_sigma, xtol=xtol, maxiter=100)
        return float(iv)
    except Exception as e:
        # WARNING: Aqui sim vale o alerta, pois passou nas checagens mas o solver falhou
        logger.warning(f"IV Solver não convergiu para K={K}, Price={price}: {e}")
        return float('nan')


def adjust_spot_for_dividends(
    S: float,
    dividends_list: List[Tuple[float, int]],
    T_days: int,
    r: float = 0.0
) -> float:
    """
    Ajusta o preço Spot para dividendos em dinheiro.
    S_adj = S - VP(Dividendos que ocorrem antes do vencimento).
    """
    S_adj = float(S)
    for div_value, div_days in dividends_list:
        if div_days < T_days:
            t_years = div_days / 252.0
            pv = div_value * math.exp(-r * t_years)
            S_adj -= pv
            
    return max(0.0, S_adj)