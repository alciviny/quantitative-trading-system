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


def generate_signals_vectorized(
    price: pd.Series,
    bb_dev_range: np.ndarray,
    vol_max_range: np.ndarray,
    bb_exit_std_dev: float
):
    """
    Gera sinais de entrada e saída para uma estratégia de cruzamento de Bandas de Bollinger
    com filtro de volatilidade, de forma totalmente vetorizada.

    Args:
        price (pd.Series): Série de preços de fechamento.
        bb_dev_range (np.ndarray): Array de desvios padrão para as bandas de entrada.
        vol_max_range (np.ndarray): Array de thresholds para o filtro de volatilidade.
        bb_exit_std_dev (float): Desvio padrão para a banda de saída.

    Returns:
        tuple: Uma tupla contendo (entries, exits), onde ambos são DataFrames
               booleanos prontos para serem usados pelo `vbt.Portfolio`.
    """
    # ===================== LÓGICA DA ESTRATÉGIA =====================

    # --- Cálculo das Bandas de Bollinger para ENTRADA ---
    # Cria uma matriz de bandas, uma para cada parâmetro em bb_dev_range
    bb_indicator = vbt.BBANDS.run(price, window=BB_PERIOD, alpha=bb_dev_range)
    entry_bb = price.vbt <= bb_indicator.lower  # (num_rows, num_bb_params)

    # --- Filtro de Volatilidade (Regime-Aware) ---
    ret = price.pct_change()
    vol_fast = ret.rolling(10).std()
    vol_slow = ret.rolling(60).std()
    regime_vol = vol_fast / (vol_slow + 1e-6)  # Adiciona epsilon para evitar divisão por zero

    # Cria uma máscara de volatilidade, uma para cada parâmetro em vol_max_range
    vol_mask = regime_vol.values[:, None] <= vol_max_range[None, :]  # (num_rows, num_vol_params)

    # --- Combinação 3D das condições de entrada ---
    # Usa broadcasting do NumPy para criar uma matriz 3D de sinais
    # (num_rows, num_bb_params, num_vol_params)
    entries_3d = entry_bb.values[:, :, None] & vol_mask[:, None, :]

    # --- Filtro de Estocástico Suave ---
    # Um estocástico baixo aumenta a "convicção" da entrada
    stoch_col = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    # Precisamos recalcular o estocástico para a série de preços pura
    stoch_k_series = vbt.STOCH.run(
        price,
        k_window=STOCH_K_PERIOD,
        d_window=STOCH_K_SMOOTH # d_window acts as smoothing for %K
    ).k

    stoch_k = stoch_k_series.values
    # Pondera o sinal: stoch < 30 -> peso >= 0, stoch=0 -> peso=1
    stoch_weight = np.clip((30 - stoch_k) / 30, 0, 1)

    # Aplica o peso. Entradas ponderadas > 0.5 são consideradas válidas
    weighted_entries_3d = entries_3d * stoch_weight[:, None, None]
    final_entries = weighted_entries_3d > 0.5

    # --- Reshape para 2D ---
    # Transforma a matriz 3D em 2D para o portfolio do vectorbt
    n_rows, n_bb, n_vol = final_entries.shape
    num_combinations = n_bb * n_vol
    entries_2d = final_entries.reshape(n_rows, num_combinations)

    # --- Lógica de SAÍDA ---
    # A saída é mais simples: cruzar a banda superior com um desvio padrão fixo
    bb_exit_indicator = vbt.BBANDS.run(price, window=BB_PERIOD, alpha=bb_exit_std_dev)
    # Replica a condição de saída para todas as combinações de parâmetros de entrada
    exits_2d = (price.vbt >= bb_exit_indicator.upper).vbt.tile(num_combinations)

    return entries_2d, exits_2d
