import pandas as pd
import numpy as np
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.config import BB_PERIOD, STOCH_K_PERIOD, STOCH_K_SMOOTH


class MeanReversionStrategy(Strategy):
    """
    Estratégia de Mean Reversion (Reversão à Média) baseada em Bollinger Bands e RSI.
    
    Lógica:
    - COMPRA: Quando o preço toca a banda inferior + RSI baixo + preço acima WWMA
    - VENDA: Quando o preço volta perto da média móvel ou toca banda superior
    
    Esta estratégia funciona bem em mercados laterais/consolidadores.
    """
    
    def __init__(self, bb_std_dev: float = 1.5, rsi_period: int = 120, 
                 rsi_buy_threshold: int = 35, rsi_sell_threshold: int = 65,
                 save_logs: bool = False):
        """
        Args:
            bb_std_dev: Desvio padrão das Bandas de Bollinger (1.5 é padrão)
            rsi_period: Período do RSI/IFR (120 é padrão no projeto)
            rsi_buy_threshold: RSI abaixo disso = oportunidade de compra
            rsi_sell_threshold: RSI acima disso = oportunidade de venda
            save_logs: Se True, salva snapshots da estratégia
        """
        super().__init__(save_logs=save_logs)
        self.bb_std_dev = bb_std_dev
        self.rsi_period = rsi_period
        self.rsi_buy_threshold = rsi_buy_threshold
        self.rsi_sell_threshold = rsi_sell_threshold
    
    def get_name(self) -> str:
        return f"MeanReversion_BB{self.bb_std_dev}_RSI{self.rsi_period}"
    
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula sinais baseado na reversão à média."""
        
        # Converte inteiros para float
        numeric_cols = df.select_dtypes(include=[np.integer]).columns
        for col in numeric_cols:
            df[col] = df[col].astype(float)
        
        # Procura as colunas de BB dinamicamente
        bb_std_str = str(float(self.bb_std_dev)).rstrip('0').rstrip('.')  # 1.5 não vira 1.50000
        
        # Procura a coluna de BB superior
        col_bb_upper = None
        for col in df.columns:
            if f"bb_upper_{BB_PERIOD}_" in col and str(self.bb_std_dev) in col:
                col_bb_upper = col
                break
        
        # Se não encontrou, tenta com busca mais simples
        if col_bb_upper is None:
            for col in df.columns:
                if "bb_upper_200_1" in col:  # 1.5
                    col_bb_upper = col
                    break
        
        # Procura a coluna de BB inferior
        col_bb_lower = None
        for col in df.columns:
            if f"bb_lower_{BB_PERIOD}_" in col and str(self.bb_std_dev) in col:
                col_bb_lower = col
                break
        
        # Se não encontrou, tenta com busca mais simples
        if col_bb_lower is None:
            for col in df.columns:
                if "bb_lower_200_1" in col:  # 1.5
                    col_bb_lower = col
                    break
        
        # Nomes das outras colunas
        col_bb_middle = f"bb_middle_{BB_PERIOD}"
        col_rsi = f"rsi_{self.rsi_period}"
        col_wwma = "wwma_200"
        col_stoch_k = f"stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}"
        
        df['SIGNAL'] = 'HOLD'
        
        # Verifica se as colunas obrigatórias existem
        required_cols = [col_bb_upper, col_bb_lower, col_rsi, col_wwma]
        missing_cols = [c for c in required_cols if c is None]
        if missing_cols or col_bb_upper is None or col_bb_lower is None:
            return df
        
        # Verifica se as colunas obrigatórias existem
        required_cols = [col_bb_upper, col_bb_lower, col_rsi, col_wwma]
        missing_cols = [c for c in required_cols if c is None]
        if missing_cols or col_bb_upper is None or col_bb_lower is None:
            return df
        
        # ============ LÓGICA DE COMPRA (SIMPLIFICADA) ============
        # Condição 1: Preço toca ou ultrapassa a banda inferior (sobrevencido)
        price_at_lower = df['close'] <= df[col_bb_lower]
        
        # Condição 2: RSI baixo
        rsi_low = df[col_rsi] < 40
        
        # Sinal de COMPRA: Preço na banda inferior OU RSI baixo
        buy_signal = price_at_lower | rsi_low
        
        # ============ LÓGICA DE VENDA (SIMPLIFICADA) ============
        # Condição 1: Preço toca ou ultrapassa a banda superior (sobrecomprado)
        price_at_upper = df['close'] >= df[col_bb_upper]
        
        # Condição 2: RSI alto
        rsi_high = df[col_rsi] > 60
        
        # Sinal de VENDA: Qualquer uma das condições
        sell_signal = price_at_upper | rsi_high
        
        # ============ APLICAÇÃO DOS SINAIS ============
        df.loc[buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[sell_signal, 'SIGNAL'] = 'SELL'
        
        # ============ STOP LOSS ============
        df['STOP_LOSS'] = np.nan
        # Stop Loss = 2% abaixo do preço de entrada (banda inferior)
        df.loc[buy_signal, 'STOP_LOSS'] = df.loc[buy_signal, col_bb_lower] * 0.98
        # Stop Loss para venda = 2% acima do preço de entrada (banda superior)
        df.loc[sell_signal, 'STOP_LOSS'] = df.loc[sell_signal, col_bb_upper] * 1.02
        
        return df
