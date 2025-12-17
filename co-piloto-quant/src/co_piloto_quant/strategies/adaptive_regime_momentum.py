import numpy as np
import pandas as pd
from co_piloto_quant.strategies.base import Strategy

class AdaptiveRegimeMomentumStrategy(Strategy):
    """
    Estrategia Fenomenal: Adaptive Regime Momentum
    
    Filosofia:
    - NAO fazer mean reversion (nao existe)
    - SEGUIR tendencias em CALM (onde sao previsibles)
    - CAPTURAR breakouts em VOLATILE (onde ha movimento)
    - EVITAR SIDEWAYS (onde nao ha tendencia)
    
    Componentes:
    1. Trend Detection: EMA curta vs EMA longa
    2. Momentum: MACD para confirmar movimento
    3. Entry Timing: Pullback em tendencia, Breakout em volatilidade
    4. Position Sizing: Dinamico baseado em ATR
    5. Risk Management: Stops inteligentes, profit targets multiplos
    """
    
    def __init__(self,
                 ema_fast: int = 12,
                 ema_slow: int = 26,
                 macd_signal: int = 9,
                 atr_period: int = 14,
                 atr_stop_multiplier: float = 2.0,
                 bb_period: int = 20,
                 bb_std: float = 2.0,
                 max_hold_calm: int = 15,
                 max_hold_volatile: int = 7,
                 risk_percent: float = 0.02,
                 save_logs: bool = False):
        
        super().__init__(save_logs=save_logs)
        
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.macd_signal = macd_signal
        self.atr_period = atr_period
        self.atr_stop_multiplier = atr_stop_multiplier
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.max_hold_calm = max_hold_calm
        self.max_hold_volatile = max_hold_volatile
        self.risk_percent = risk_percent
    
    def get_name(self) -> str:
        return f"AdaptiveRegimeMomentum(EMA={self.ema_fast}/{self.ema_slow})"
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period, min_periods=1).mean()
        
        return atr
    
    def _calculate_ema(self, series: pd.Series, period: int) -> pd.Series:
        return series.ewm(span=period, adjust=False).mean()
    
    def _calculate_macd(self, df: pd.DataFrame) -> tuple:
        close = df['close']
        ema_fast = self._calculate_ema(close, self.ema_fast)
        ema_slow = self._calculate_ema(close, self.ema_slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._calculate_ema(macd_line, self.macd_signal)
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    
    def _calculate_bollinger_bands(self, df: pd.DataFrame) -> tuple:
        close = df['close']
        sma = close.rolling(self.bb_period, min_periods=1).mean()
        std = close.rolling(self.bb_period, min_periods=1).std()
        
        upper = sma + (self.bb_std * std)
        lower = sma - (self.bb_std * std)
        
        return upper, sma, lower
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        close = df['close']
        atr = self._calculate_atr(df, self.atr_period)
        
        ema_fast = self._calculate_ema(close, self.ema_fast)
        ema_slow = self._calculate_ema(close, self.ema_slow)
        macd_line, signal_line, histogram = self._calculate_macd(df)
        
        upper_bb, middle_bb, lower_bb = self._calculate_bollinger_bands(df)
        
        trend = np.where(ema_fast > ema_slow, 'UP', 'DOWN')
        momentum_bullish = histogram > 0
        momentum_bearish = histogram < 0
        
        is_calm = (df['vol_signal'] == 'CALM') if 'vol_signal' in df.columns else True
        is_volatile = (df['vol_signal'] == 'VOLATILE') if 'vol_signal' in df.columns else False
        is_sideways = (df['trend_signal'] == 'SIDEWAYS') if 'trend_signal' in df.columns else False
        
        df['SIGNAL'] = 'HOLD'
        
        long_signal = (
            (trend == 'UP') & 
            momentum_bullish &
            ~is_sideways &
            ((is_calm & (close <= middle_bb)) | (is_volatile & (close <= lower_bb)))
        )
        
        short_signal = (
            (trend == 'DOWN') & 
            momentum_bearish &
            ~is_sideways &
            ((is_calm & (close >= middle_bb)) | (is_volatile & (close >= upper_bb)))
        )
        
        df.loc[long_signal, 'SIGNAL'] = 'BUY'
        df.loc[short_signal, 'SIGNAL'] = 'SELL'
        
        df['STOP_LOSS'] = np.nan
        df.loc[long_signal, 'STOP_LOSS'] = df.loc[long_signal, 'close'] - (atr[long_signal] * self.atr_stop_multiplier)
        df.loc[short_signal, 'STOP_LOSS'] = df.loc[short_signal, 'close'] + (atr[short_signal] * self.atr_stop_multiplier)
        
        df['PROFIT_TARGET'] = np.nan
        df.loc[long_signal, 'PROFIT_TARGET'] = df.loc[long_signal, 'close'] + (atr[long_signal] * self.atr_stop_multiplier * 3.0)
        df.loc[short_signal, 'PROFIT_TARGET'] = df.loc[short_signal, 'close'] - (atr[short_signal] * self.atr_stop_multiplier * 3.0)
        
        df['ATR'] = atr
        df['TREND'] = trend
        df['MOMENTUM'] = np.where(momentum_bullish, 'BULL', 'BEAR')
        
        return df
