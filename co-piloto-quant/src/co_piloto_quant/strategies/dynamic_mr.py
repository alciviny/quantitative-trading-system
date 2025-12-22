import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.indicators.names import IndicatorNames
from src.co_piloto_quant.indicators.special.frac_diff import fractional_diff_fixed_window


class DynamicRegimeMeanReversion(Strategy):

    def __init__(
        self,
        lookback_regime: int = 252,
        hurst_window: int = 72,
        entropy_window: int = 20,
        regime_score_threshold: float = 0.65,
        regime_persistence_window: int = 5,
        regime_persistence_min: float = 0.6,
        bb_period: int = 20,
        bb_dev: float = 2.0,
        save_logs: bool = False
    ):
        super().__init__(save_logs=save_logs)

        self.lookback_regime = lookback_regime
        self.hurst_window = hurst_window
        self.entropy_window = entropy_window
        self.regime_score_threshold = regime_score_threshold
        self.regime_persistence_window = regime_persistence_window
        self.regime_persistence_min = regime_persistence_min
        self.bb_period = bb_period
        self.bb_dev = bb_dev

    def get_name(self) -> str:
        return f"DynamicMR_Daily_S{self.regime_score_threshold}_P{self.regime_persistence_window}"

    # ======================================================
    # REGIME ENGINE (SAFE)
    # ======================================================

    def _calculate_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        col_hurst = IndicatorNames.hurst_z(self.hurst_window)
        col_entropy = IndicatorNames.entropy_z(self.entropy_window)

        # Rolling ranks
        hurst_rank = df[col_hurst].rolling(self.lookback_regime).rank(pct=True)
        entropy_rank = df[col_entropy].rolling(self.lookback_regime).rank(pct=True)

        # 🔐 Alinhamento explícito
        hurst_rank, entropy_rank = hurst_rank.align(entropy_rank, join="inner")

        regime_score = (1 - hurst_rank) * 0.6 + (1 - entropy_rank) * 0.4

        df = df.join(regime_score.rename("regime_score"), how="left")

        favorable_day = (df["regime_score"] >= self.regime_score_threshold).astype(float)

        regime_persistence = (
            favorable_day
            .rolling(self.regime_persistence_window)
            .mean()
        )

        df["regime_persistence"] = regime_persistence
        df["regime_ok"] = df["regime_persistence"] >= self.regime_persistence_min

        return df

    # ======================================================
    # SIGNAL ENGINE
    # ======================================================

    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._calculate_regime_features(df) # Mantém o cálculo de regime original

        # --- A MÁGICA ACONTECE AQUI ---
        # 1. Calcula o Preço Fracionado
        df['close_frac'] = fractional_diff_fixed_window(df['close'], d=0.4, window=50)

        # 2. Calcula Bandas de Bollinger sobre o PREÇO FRACIONADO (Estacionário)
        # Como o close_frac oscila perto de zero, as bandas serão canais de volatilidade pura
        rolling_mean = df['close_frac'].rolling(self.bb_period).mean()
        rolling_std = df['close_frac'].rolling(self.bb_period).std()

        df['bb_lower_frac'] = rolling_mean - (rolling_std * self.bb_dev)
        df['bb_upper_frac'] = rolling_mean + (rolling_std * self.bb_dev)

        # 3. Ajuste do Sinal de Compra
        # Lógica: Se o Preço Fracionado (que já remove a tendência) cair abaixo da banda
        # significa um desvio estatístico REAL, não apenas uma queda de mercado.

        # Removemos NaNs gerados pelo FracDiff para evitar erros
        safe_mask = df['close_frac'].notna() & df['regime_ok']

        df["SIGNAL"] = "HOLD"

        # Compra: Preço Fracionado < Banda Inferior Fracionada E Regime OK
        buy_condition = (df['close_frac'] <= df['bb_lower_frac']) & safe_mask
        df.loc[buy_condition, "SIGNAL"] = "BUY"

        # Venda: Preço Fracionado volta à média (zero ou média móvel do frac)
        sell_condition = (df['close_frac'] >= rolling_mean) & safe_mask
        df.loc[sell_condition, "SIGNAL"] = "SELL"


        if self.save_logs:
            df["debug_regime_score"] = df["regime_score"]
            df["debug_regime_persistence"] = df["regime_persistence"]
            df["debug_regime_ok"] = df["regime_ok"].astype(int)
            df["debug_close_frac"] = df["close_frac"]
            df["debug_bb_lower_frac"] = df["bb_lower_frac"]


        return df
