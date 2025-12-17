import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.config import BB_PERIOD

class MeanReversionStrategy(Strategy):
    def __init__(self, 
                 bb_std_dev: float = 1.5,
                 bb_std_dev_volatile: float = 2.5,
                 rsi_period: int = 120,
                 adaptive_rsi: bool = True,
                 adaptive_bb: bool = True,
                 use_regime_filter: bool = True,
                 max_half_life: int = 25,
                 only_bull_market: bool = True, # <--- NOVO: Trava de segurança Bear Market
                 rsi_buy_percentile: float = 0.1,
                 rsi_sell_percentile: float = 0.9,
                 adaptive_window: int = 126,
                 save_logs: bool = False):
        
        super().__init__(save_logs=save_logs)
        # ... (atribuições anteriores) ...
        self.bb_std_dev = bb_std_dev
        self.bb_std_dev_volatile = bb_std_dev_volatile
        self.rsi_period = rsi_period
        self.adaptive_rsi = adaptive_rsi
        self.adaptive_bb = adaptive_bb
        self.use_regime_filter = use_regime_filter
        self.max_half_life = max_half_life
        self.only_bull_market = only_bull_market # Guarda a config
        self.rsi_buy_percentile = rsi_buy_percentile
        self.rsi_sell_percentile = rsi_sell_percentile
        self.adaptive_window = adaptive_window
    
    def get_name(self) -> str:
        trend_str = "+BullOnly" if self.only_bull_market else ""
        return f"MeanReversion_Adaptive{trend_str}"
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        
        # ... (Cálculos de RSI e Bandas mantidos iguais) ...
        col_rsi = f"rsi_{self.rsi_period}"
        if self.adaptive_rsi and col_rsi in df.columns:
            rsi_buy_thresh = df[col_rsi].rolling(self.adaptive_window, min_periods=30).quantile(self.rsi_buy_percentile)
            rsi_sell_thresh = df[col_rsi].rolling(self.adaptive_window, min_periods=30).quantile(self.rsi_sell_percentile)
            rsi_buy_thresh.fillna(35, inplace=True)
            rsi_sell_thresh.fillna(65, inplace=True)
            rsi_low = df[col_rsi] < rsi_buy_thresh
            rsi_high = df[col_rsi] > rsi_sell_thresh
        else:
            rsi_low = df[col_rsi] < 40
            rsi_high = df[col_rsi] > 60

        middle_band = df['close'].rolling(window=BB_PERIOD).mean()
        rolling_std = df['close'].rolling(window=BB_PERIOD).std()

        if self.adaptive_bb and 'vol_signal' in df.columns:
            current_std = np.where(df['vol_signal'] == 'VOLATILE', self.bb_std_dev_volatile, self.bb_std_dev)
        else:
            current_std = self.bb_std_dev
            
        lower_band = middle_band - (current_std * rolling_std)
        upper_band = middle_band + (current_std * rolling_std)
        
        # Sinais Base
        price_at_lower = df['close'] <= lower_band
        price_at_upper = df['close'] >= upper_band
        buy_signal = price_at_lower | rsi_low
        sell_signal = price_at_upper | rsi_high
        
        # --- FILTRO 1: TENDÊNCIA MACRO (Correção do Vazamento) ---
        if self.only_bull_market:
            # min_periods=1 garante que temos média desde o começo, igual ao Lab
            mm200 = df['close'].rolling(200, min_periods=1).mean()
            
            # Se não tiver dado suficiente (ex: dia 1), assume BEAR por segurança
            mm200.fillna(np.inf, inplace=True) 
            
            # Só permite compra se Preço > MA200
            is_bear = df['close'] < mm200
            buy_signal[is_bear] = False

        # --- FILTRO 2: REGIME DE QUALIDADE (Entropy, Vol, Half-Life) ---
        if self.use_regime_filter:
            is_toxic = pd.Series(False, index=df.index)

            if 'Entropy_20' in df.columns: is_toxic |= (df['Entropy_20'] > 3.2)
            if 'VolVol_Z' in df.columns: is_toxic |= (df['VolVol_Z'] > 3.0)
            if 'Entropy_Z' in df.columns: is_toxic |= (df['Entropy_Z'] < 0.2) # Entropia muito baixa (Grinding)

            # Filtro de Half-Life
            hl_col = next((c for c in ['half_life', 'half_life_60', 'HalfLife_60'] if c in df.columns), None)
            if hl_col:
                is_toxic |= (df[hl_col] > self.max_half_life)

            buy_signal[is_toxic] = False

        # Aplicação Final
        df['SIGNAL'] = 'HOLD'
        df.loc[buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[sell_signal, 'SIGNAL'] = 'SELL'
        
        df['STOP_LOSS'] = np.nan
        df.loc[buy_signal, 'STOP_LOSS'] = lower_band[buy_signal] * 0.98
        
        return df