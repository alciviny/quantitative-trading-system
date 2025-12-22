import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.indicators.names import IndicatorNames


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
        df = self._calculate_regime_features(df)

        col_bb_lower = IndicatorNames.bollinger_lower(self.bb_period, self.bb_dev)
        col_bb_mid = IndicatorNames.bollinger_middle(self.bb_period)

        # Alinhamento seguro criando um dataframe temporário
        safe_df = df[["close", col_bb_lower, col_bb_mid, "regime_ok"]].copy()
        safe_df["regime_ok"] = safe_df["regime_ok"].fillna(False)
        safe_df.dropna(inplace=True)

        buy_signal = (safe_df["close"] <= safe_df[col_bb_lower]) & safe_df["regime_ok"]
        sell_signal = safe_df["close"] >= safe_df[col_bb_mid]

        df["SIGNAL"] = "HOLD"
        df.loc[buy_signal.index[buy_signal], "SIGNAL"] = "BUY"
        df.loc[sell_signal.index[sell_signal], "SIGNAL"] = "SELL"

        if self.save_logs:
            df["debug_regime_score"] = df["regime_score"]
            df["debug_regime_persistence"] = df["regime_persistence"]
            df["debug_regime_ok"] = df["regime_ok"].astype(int)

        return df
