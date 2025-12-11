import numpy as np
import pandas as pd
import vectorbt as vbt
from pykalman import KalmanFilter


# ==============================================================================
# Função interna: Kalman 1D (processa 1 ativo por vez)
# ==============================================================================
def _apply_kalman_1d(close_array, transition_cov):
    """Aplica o filtro de Kalman em uma série 1D.

    Args:
        close_array (np.ndarray): preços (1D)
        transition_cov (float): variância do processo (quão rápido o filtro reage)

    Returns:
        np.ndarray: estado filtrado (nível estimado)
    """
    # Segurança: evitar erros com NaN iniciais
    first_valid = np.nanargmax(~np.isnan(close_array))
    if np.isnan(close_array[0]):
        close_array = close_array.copy()
        close_array[:first_valid] = close_array[first_valid]

    kf = KalmanFilter(
        transition_matrices=np.array([1]),
        observation_matrices=np.array([1]),
        initial_state_mean=close_array[0],
        initial_state_covariance=1,
        observation_covariance=1,
        transition_covariance=transition_cov
    )

    # Execução do filtro
    state_means, _ = kf.filter(close_array)
    return state_means.flatten()


# ==============================================================================
# Função de aplicação vetorizada para VectorBT
# ==============================================================================
def _kalman_bands_apply(close, transition_cov, std_dev):
    """Executa o filtro de Kalman coluna por coluna para o vectorbt.

    Args:
        close (np.ndarray): matriz (t x n)
        transition_cov (float or array): variância do processo
        std_dev (float): multiplicador das bandas

    Returns:
        tuple: middle, upper, lower bands
    """
    rows, cols = close.shape
    middle_band = np.empty_like(close)

    # Broadcast manual dos parâmetros
    if np.isscalar(transition_cov):
        t_covs = np.full(cols, transition_cov)
    else:
        t_covs = np.asarray(transition_cov)

    # Loop coluna a coluna (pykalman não é vetorizado)
    for i in range(cols):
        col = close[:, i]

        # Segurança: se a coluna for toda NaN ou vazia
        if np.all(np.isnan(col)):
            middle_band[:, i] = np.nan
            continue

        middle_band[:, i] = _apply_kalman_1d(col, t_covs[i])

    # ==========================================================================
    # Construção das bandas — usando volatilidade do resíduo
    # ==========================================================================
    residuals = close - middle_band

    # Rolling std muito rápido e leve com vbt
    rolling_std = vbt.pd_accel.rolling_std(residuals, window=20, min_periods=1)

    upper_band = middle_band + (rolling_std * std_dev)
    lower_band = middle_band - (rolling_std * std_dev)

    return middle_band, upper_band, lower_band


# ==============================================================================
# Fabricação do Indicador VectorBT
# ==============================================================================
KalmanBands = vbt.IndicatorFactory(
    class_name='KalmanBands',
    short_name='kb',
    input_names=['close'],
    param_names=['transition_cov', 'std_dev'],
    output_names=['middle', 'upper', 'lower']
).from_apply_func(
    _kalman_bands_apply,
    transition_cov=0.01,  # padrão suave
    std_dev=2.0,
    keep_pd=True,
    require_input_shape=True
)
