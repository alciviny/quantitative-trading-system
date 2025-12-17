import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.config import BB_PERIOD

class MeanReversionSwingStrategy(Strategy):
    """
    Mean Reversion para Swing Trading (1-10 dias)
    
    Melhorias vs MeanReversionStrategy:
    1. RSI curto (30-40) para detectar reversões rápidas
    2. Stop loss dinâmico baseado em ATR (não fixo 5%)
    3. Profit target fixo (2:1 risk-reward)
    4. Regime filter ESTRITO (CALM only)
    5. Max 10 dias holding
    6. Sem only_bull_market (funciona em bear também)
    """
    
    def __init__(self, 
                 bb_std_dev: float = 1.5,
                 rsi_period: int = 40,
                 atr_multiplier: float = 2.0,
                 max_days_hold: int = 10,
                 profit_target_multiple: float = 2.0,
                 use_regime_filter: bool = True,
                 save_logs: bool = False):
        
        super().__init__(save_logs=save_logs)
        self.bb_std_dev = bb_std_dev
        self.rsi_period = rsi_period
        self.atr_multiplier = atr_multiplier
        self.max_days_hold = max_days_hold
        self.profit_target_multiple = profit_target_multiple
        self.use_regime_filter = use_regime_filter
    
    def get_name(self) -> str:
        return f"MeanReversionSwing(RSI={self.rsi_period},ATR={self.atr_multiplier}x)"
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula ATR (Average True Range)"""
        high = df['high'] if 'high' in df.columns else df['close']
        low = df['low'] if 'low' in df.columns else df['close']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period, min_periods=1).mean()
        
        return atr
    
    def _calculate_rsi(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calcula RSI"""
        close = df['close']
        delta = close.diff()
        
        gain = delta.clip(lower=0)
        loss = (-delta).clip(lower=0)
        
        avg_gain = gain.rolling(window=period, min_periods=1).mean()
        avg_loss = loss.rolling(window=period, min_periods=1).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # RSI customizado (período curto)
        rsi = self._calculate_rsi(df, period=self.rsi_period)
        
        # Bandas de Bollinger
        middle_band = df['close'].rolling(window=BB_PERIOD).mean()
        rolling_std = df['close'].rolling(window=BB_PERIOD).std()
        lower_band = middle_band - (self.bb_std_dev * rolling_std)
        upper_band = middle_band + (self.bb_std_dev * rolling_std)
        
        # ATR para stops dinâmicos
        atr = self._calculate_atr(df, period=14)
        
        # Sinais base
        price_at_lower = df['close'] <= lower_band
        price_at_upper = df['close'] >= upper_band
        rsi_oversold = rsi < 30
        rsi_overbought = rsi > 70
        
        # Confirmação com RSI
        buy_signal = (price_at_lower | rsi_oversold)
        sell_signal = (price_at_upper | rsi_overbought)
        
        # Regime filter: APENAS em CALM
        if self.use_regime_filter and 'vol_signal' in df.columns:
            is_calm = df['vol_signal'] == 'CALM'
            buy_signal = buy_signal & is_calm
        
        # Aplicação de sinais
        df['SIGNAL'] = 'HOLD'
        df.loc[buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[sell_signal, 'SIGNAL'] = 'SELL'
        
        # Stop loss dinâmico: RSI curto = entrada, ATR = stop
        df['STOP_LOSS'] = np.nan
        df.loc[buy_signal, 'STOP_LOSS'] = df.loc[buy_signal, 'close'] - (atr[buy_signal] * self.atr_multiplier)
        
        # Profit target: 2x do risco
        df['PROFIT_TARGET'] = np.nan
        risk = df.loc[buy_signal, 'close'] - (atr[buy_signal] * self.atr_multiplier)
        reward = (df.loc[buy_signal, 'close'] - risk) * self.profit_target_multiple
        df.loc[buy_signal, 'PROFIT_TARGET'] = df.loc[buy_signal, 'close'] + reward
        
        return df
