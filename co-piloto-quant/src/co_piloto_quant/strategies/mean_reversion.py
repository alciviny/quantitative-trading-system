import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.config import BB_PERIOD

class MeanReversionStrategy(Strategy):
    """
    Estratégia de Mean Reversion (Reversão à Média) com parâmetros dinâmicos e filtro de regime.
    
    Lógica Adaptativa:
    - FILTRO: Proíbe compras se o regime de mercado for "tóxico" (alta volatilidade/entropia).
    - COMPRA:
        - RSI abaixo de um limiar dinâmico (percentil histórico).
        - OU Preço toca uma Banda de Bollinger que se alarga com a volatilidade.
    - VENDA:
        - RSI acima de um limiar dinâmico (percentil histórico).
        - OU Preço toca a banda superior.
    """
    
    def __init__(self, 
                 bb_std_dev: float = 1.5,
                 bb_std_dev_volatile: float = 2.5,
                 rsi_period: int = 120,
                 adaptive_rsi: bool = True,
                 adaptive_bb: bool = True,
                 use_regime_filter: bool = True,
                 max_half_life: int = 25,  # <--- NOVO PARÂMETRO (Default: 25 dias)
                 rsi_buy_percentile: float = 0.1,
                 rsi_sell_percentile: float = 0.9,
                 adaptive_window: int = 126, # Aprox. 6 meses
                 save_logs: bool = False):
        """
        Args:
            bb_std_dev: Desvio padrão base das Bandas de Bollinger.
            bb_std_dev_volatile: Desvio padrão em regimes de alta volatilidade.
            rsi_period: Período do RSI.
            adaptive_rsi: Se True, usa limiares de RSI baseados em percentil.
            adaptive_bb: Se True, alarga as bandas com a volatilidade.
            use_regime_filter: Se True, proíbe compras em regimes de mercado tóxicos.
            max_half_life: Limite máximo para o half-life de um ativo ser considerado em reversão à média.
            rsi_buy_percentile: Percentil para o limiar de compra do RSI.
            rsi_sell_percentile: Percentil para o limiar de venda do RSI.
            adaptive_window: Janela (dias) para calcular os parâmetros adaptativos.
            save_logs: Se True, salva snapshots da estratégia.
        """
        super().__init__(save_logs=save_logs)
        self.bb_std_dev = bb_std_dev
        self.bb_std_dev_volatile = bb_std_dev_volatile
        self.rsi_period = rsi_period
        self.adaptive_rsi = adaptive_rsi
        self.adaptive_bb = adaptive_bb
        self.use_regime_filter = use_regime_filter
        self.max_half_life = max_half_life # Guarda o valor na classe
        self.rsi_buy_percentile = rsi_buy_percentile
        self.rsi_sell_percentile = rsi_sell_percentile
        self.adaptive_window = adaptive_window
    
    def get_name(self) -> str:
        adaptive_str = "Adaptive" if self.adaptive_bb or self.adaptive_rsi else "Fixed"
        filter_str = "+RegimeFilter" if self.use_regime_filter else ""
        return f"MeanReversion_{adaptive_str}{filter_str}"
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula sinais baseado na reversão à média com parâmetros adaptativos e filtro de regime."""
        
        df = df.copy()
        col_rsi = f"rsi_{self.rsi_period}"
        
        # --- 1. Limiares de RSI (Adaptativo ou Fixo) ---
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

        # --- 2. Bandas de Bollinger (Adaptativa ou Fixa) ---
        middle_band = df['close'].rolling(window=BB_PERIOD).mean()
        rolling_std = df['close'].rolling(window=BB_PERIOD).std()

        if self.adaptive_bb and 'vol_signal' in df.columns:
            current_std = np.where(df['vol_signal'] == 'VOLATILE', self.bb_std_dev_volatile, self.bb_std_dev)
        else:
            current_std = self.bb_std_dev
            
        lower_band = middle_band - (current_std * rolling_std)
        upper_band = middle_band + (current_std * rolling_std)
        
        # --- 3. Lógica de Compra e Venda ---
        price_at_lower = df['close'] <= lower_band
        price_at_upper = df['close'] >= upper_band
        
        buy_signal = price_at_lower | rsi_low
        sell_signal = price_at_upper | rsi_high
        
        # --- 4. FILTRO DE REGIME (ATUALIZADO - Lógica Goldilocks) ---
        if self.use_regime_filter:
            is_toxic = pd.Series(False, index=df.index)

            # --- PROTEÇÃO SUPERIOR (Contra Crises) ---
            if 'Entropy_20' in df.columns:
                is_toxic |= (df['Entropy_20'] > 3.2) # Teto Absoluto
            
            if 'VolVol_Z' in df.columns:
                is_toxic |= (df['VolVol_Z'] > 3.0) # Instabilidade

            # --- PROTEÇÃO INFERIOR (Contra Tendências Lisas - O NOVO FILTRO) ---
            # Se a Entropia Z-Score for negativa, o mercado está "ordenado demais".
            # Reversão à média falha aqui porque o preço não repica.
            if 'Entropy_Z' in df.columns:
                # Bloqueia se a entropia estiver abaixo da média histórica (Z < 0)
                # Os seus dados mostram que Wins ocorrem em +0.67 e Losses em -0.16.
                # Vamos ser conservadores e bloquear tudo abaixo de 0.2
                is_toxic |= (df['Entropy_Z'] < 0.2) 

            # --- FILTRO DE ELASTICIDADE (Half-Life) ---
            # Se o Half-Life for muito alto, o ativo perdeu a memória de preço.
            if 'HalfLife_60' in df.columns:
                is_toxic |= (df['HalfLife_60'] > self.max_half_life)

            # Aplica a vacina
            buy_signal[is_toxic] = False

        # --- 5. Aplicação dos Sinais e Stop Loss ---
        df['SIGNAL'] = 'HOLD'
        df.loc[buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[sell_signal, 'SIGNAL'] = 'SELL'
        
        df['STOP_LOSS'] = np.nan
        df.loc[buy_signal, 'STOP_LOSS'] = lower_band[buy_signal] * 0.98
        
        return df
