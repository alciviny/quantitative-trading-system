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
from co_piloto_quant.indicators.special.kalman_bands import KalmanBands

class SignalEngine:
    @staticmethod
    def generate_signals(
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

        # ===================== PREÇO =====================
        price = close

        # ===================== KALMAN BANDS (ENTRADA) =====================
        kb_indicator = KalmanBands.run(
            close=price,
            transition_cov=0.05,
            std_dev=bb_dev_range
        )

        # Preço abaixo da banda inferior (entrada)
        entry_bb = price.vbt <= kb_indicator.lower  # Series ou DataFrame

        # Garante 2D para broadcasting (grid / app)
        if entry_bb.ndim == 1:
            entry_bb = entry_bb.to_frame()

        # ===================== FILTRO DE VOLATILIDADE (REGIME) =====================
        ret = price.pct_change()
        vol_fast = ret.rolling(10).std()
        vol_slow = ret.rolling(60).std()
        regime_vol = vol_fast / (vol_slow + 1e-6)

        # Usa apenas o primeiro valor (app ou grid)
        vol_condition = regime_vol <= vol_max_range[0]

        # Combinação inicial
        entries = entry_bb & vol_condition

        # ===================== FILTRO ESTOCÁSTICO =====================
        stoch_k_series = vbt.STOCH.run(
            high,
            low,
            close,
            k_window=STOCH_K_PERIOD,
            d_window=STOCH_K_SMOOTH,
        ).percent_k

        stoch_condition = stoch_k_series <= 30  # Oversold

        # Combinação final de entrada
        final_entries = entries & stoch_condition

        # ===================== KALMAN BANDS (SAÍDA) =====================
        kb_exit_indicator = KalmanBands.run(
            close=price,
            transition_cov=0.05,
            std_dev=bb_exit_std_dev
        )

        # ===== CORREÇÃO CRÍTICA: Series vs DataFrame =====
        upper = kb_exit_indicator.upper
        if isinstance(upper, pd.DataFrame):
            upper = upper.iloc[:, 0]

        exits = price >= upper

        return final_entries, exits

    @staticmethod
    def generate_single_signals(
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        bb_dev: float,
        vol_max: float,
        bb_exit_std_dev: float
    ) -> Tuple[pd.Series, pd.Series]:
        """
        Gera sinais para um único conjunto de parâmetros, adequado para simulações
        com parâmetros fixos (e.g., walk-forward validation).
        Retorna Series 1D com os sinais de entrada e saída.
        """
        price = close

        # Kalman Bands (Entrada) - usa bb_dev único
        kb_indicator = KalmanBands.run(
            close=price,
            transition_cov=0.05,
            std_dev=bb_dev # Single value
        )
        entry_bb = (price <= kb_indicator.lower).rename("entry_bb")

        # Filtro de Volatilidade (Regime) - usa vol_max único
        ret = price.pct_change()
        vol_fast = ret.rolling(10).std()
        vol_slow = ret.rolling(60).std()
        regime_vol = vol_fast / (vol_slow + 1e-6)
        vol_condition = (regime_vol <= vol_max).rename("vol_condition")

        # Combinação inicial
        entries = entry_bb & vol_condition

        # Filtro Estocástico
        stoch_k_series = vbt.STOCH.run(
            high,
            low,
            close,
            k_window=STOCH_K_PERIOD,
            d_window=STOCH_K_SMOOTH,
        ).percent_k
        stoch_condition = (stoch_k_series <= 30).rename("stoch_condition")

        # Combinação final de entrada
        final_entries = (entries & stoch_condition).rename("final_entries")

        # Kalman Bands (Saída) - usa bb_exit_std_dev único
        kb_exit_indicator = KalmanBands.run(
            close=price,
            transition_cov=0.05,
            std_dev=bb_exit_std_dev
        )
        # Garante que 'upper' é uma Series 1D
        upper = kb_exit_indicator.upper
        if isinstance(upper, pd.DataFrame):
            upper = upper.iloc[:, 0]
        
        exits = (price >= upper).rename("exits")

        return final_entries, exits