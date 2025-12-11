"""
Módulo central para a geração de sinais de trading de forma vetorizada.

Este módulo contém a "inteligência" da estratégia, separada da execução
do backtest. Ele utiliza vectorbt para processar eficientemente os dados
e gerar sinais de entrada e saída com base em múltiplos parâmetros.
"""

import vectorbt as vbt
import numpy as np
import pandas as pd

from co_piloto_quant.config import BB_PERIOD, STOCH_K_PERIOD, STOCH_K_SMOOTH
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.indicators.special.kalman_bands import KalmanBands


def generate_signals_vectorized(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    bb_dev_range: np.ndarray,
    vol_max_range: np.ndarray,
    bb_exit_std_dev: float
):
    """
    Gera sinais usando KALMAN BANDS (Reativo) em vez de Bollinger (Atrasado).
    """
    # ===================== LÓGICA DA ESTRATÉGIA (ATUALIZADA) =====================
    price = close
    # --- Cálculo das KALMAN BANDS para ENTRADA ---
    # Substituímos BBANDS por KalmanBands.
    # transition_cov=0.05 torna a média 'inteligente' (foge rápido de quedas)
    # bb_dev_range agora controla o desvio do Kalman (std_dev)
    kb_indicator = KalmanBands.run(
        price,
        transition_cov=0.05,
        std_dev=bb_dev_range
    )

    # A lógica booleana permanece a mesma: Preço < Banda Inferior
    # Mas agora a banda inferior 'desce' junto com o crash, evitando compra prematura
    entry_bb = price.vbt <= kb_indicator.lower  # (num_rows, num_bb_params)

    # --- Filtro de Volatilidade (Regime-Aware) ---
    # (Mantém igual ao original)
    ret = price.pct_change()
    vol_fast = ret.rolling(10).std()
    vol_slow = ret.rolling(60).std()
    regime_vol = vol_fast / (vol_slow + 1e-6)
    vol_mask = regime_vol.values[:, None] <= vol_max_range[None, :]

    # --- Combinação 3D das condições de entrada ---
    entries_3d = entry_bb.values[:, :, None] & vol_mask[:, None, :]

    # --- Filtro de Estocástico Suave ---
    # (Mantém igual ao original)
    stoch_k_series = vbt.STOCH.run(
        high,
        low,
        close,
        k_window=STOCH_K_PERIOD,
        d_window=STOCH_K_SMOOTH,
    ).percent_k
    stoch_k = stoch_k_series.values
    stoch_weight = np.clip((30 - stoch_k) / 30, 0, 1)

    weighted_entries_3d = entries_3d * stoch_weight[:, None, None]
    final_entries = weighted_entries_3d > 0.5

    # --- Reshape para 2D ---
    n_rows, n_bb, n_vol = final_entries.shape
    num_combinations = n_bb * n_vol
    entries_2d = final_entries.reshape(n_rows, num_combinations)

    # --- Lógica de SAÍDA (Também Atualizada para Kalman) ---
    # Usar Kalman na saída protege o lucro. Se o preço subir rápido e virar,
    # a banda Kalman vira junto e garante a saída antes da devolução tudo.
    kb_exit_indicator = KalmanBands.run(
        price,
        transition_cov=0.05,
        std_dev=bb_exit_std_dev
    )

    # Preço tocou na banda superior do Kalman
    exits_2d = (price.vbt >= kb_exit_indicator.upper).vbt.tile(num_combinations)

    return entries_2d, exits_2d
