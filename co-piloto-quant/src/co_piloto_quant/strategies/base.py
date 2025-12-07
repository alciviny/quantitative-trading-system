import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

# Importamos as configurações para garantir que os nomes das colunas batam com o analysis.py
from co_piloto_quant.config import (
    BB_PERIOD, 
    STOCH_K_PERIOD, 
    STOCH_K_SMOOTH
)

class Strategy(ABC):
    """
    Classe base abstrata para todas as estratégias de trading.
    Define a interface que todas as estratégias concretas devem seguir.
    """

    @abstractmethod
    def evaluate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Avalia a estratégia com base nos dados de mercado fornecidos.
        Args:
            df (pd.DataFrame): DataFrame contendo dados de OHLCV e indicadores técnicos.
        Returns:
            pd.DataFrame: O DataFrame original com uma coluna adicional 'SIGNAL'
                          contendo 'BUY', 'SELL' ou 'HOLD'.
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome único da estratégia."""
        pass

class AdaptiveSniperStrategy(Strategy):
    """
    Implementação da estratégia 'Sniper Adaptativo'.
    Utiliza Z-Scores de Hurst e Entropia para filtrar regimes, 
    e Bandas de Bollinger + Estocástico para gatilhos precisos.
    """

    def get_name(self) -> str:
        return "AdaptiveSniperStrategy"

    def evaluate(self, df: pd.DataFrame) -> pd.DataFrame:
        # Trabalhamos com uma cópia para não afetar o DF original fora da função
        df = df.copy()
        
        # 1. Definição dos nomes das colunas (devem bater com analysis.py)
        # O desvio de entrada 'sniper' é 0.45 conforme sua lógica original
        bb_dev_entry = 0.45 
        
        col_bb_upper = f'BB_Upper_{BB_PERIOD}_{bb_dev_entry}'
        col_bb_lower = f'BB_Lower_{BB_PERIOD}_{bb_dev_entry}'
        col_bb_mid   = f'BB_Middle_{BB_PERIOD}'
        col_stoch_k  = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
        col_wwma     = 'WWMA_200'
        
        # 2. Inicializa coluna de Sinal como 'HOLD' (Neutro)
        df['SIGNAL'] = 'HOLD'
        
        # Verificação de segurança: se faltar indicador crítico, retorna neutro
        required_cols = [col_bb_upper, col_stoch_k, 'Hurst_Z', 'Entropy_Z']
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            # Em produção, você pode querer logar isso
            return df

        # --- LÓGICA VETORIZADA (Aplica as regras em todas as linhas de uma vez) ---

        # 3. Filtros de Regime (Forensics / Adaptativo)
        # Regra: Hurst > -0.5 (Tendência existe) E Entropia <= 1.0 (Sem caos excessivo)
        # Usamos fillna(0) para garantir que dias sem dados de regime não gerem erro
        mask_regime_ok = (df['Hurst_Z'].fillna(0) >= -0.5) & (df['Entropy_Z'].fillna(10) <= 1.0)
        
        # 4. Lógica de COMPRA
        # Gatilho: Preço "espremido" dentro das bandas de 0.45 (Squeeze)
        mask_buy_zone = (df['close'] >= df[col_bb_lower]) & (df['close'] <= df[col_bb_upper])
        # Gatilho: Estocástico sobrevendido
        mask_stoch_buy = df[col_stoch_k] < 30
        
        # Gatilho: Fluxo (OBTR ou WAD acima da média)
        mask_flow_buy = pd.Series(False, index=df.index)
        if 'obtr' in df.columns and 'obtr_bb_middle_band' in df.columns:
             mask_flow_buy = (df['obtr'] > df['obtr_bb_middle_band'])
        if 'wad' in df.columns and 'wad_bb_middle_band' in df.columns:
             mask_flow_buy = mask_flow_buy | (df['wad'] > df['wad_bb_middle_band'])

        # SINAL FINAL DE COMPRA: Regime OK + Zona + Estocástico + Fluxo
        final_buy_signal = mask_regime_ok & mask_buy_zone & mask_stoch_buy & mask_flow_buy
        
        # 5. Lógica de VENDA
        # Filtro: Preço abaixo da Média Ponderada de 200 (Tendência de Baixa)
        mask_trend_down = df['close'] < df.get(col_wwma, np.inf)
        # Gatilho: Preço entre a Banda Inferior e a Média (Pullback de baixa)
        mask_sell_zone = (df['close'] >= df[col_bb_lower]) & (df['close'] <= df[col_bb_mid])
        # Gatilho: Estocástico sobrecomprado
        mask_stoch_sell = df[col_stoch_k] > 70
        
        # Gatilho: Fluxo Vendedor
        mask_flow_sell = pd.Series(False, index=df.index)
        if 'obtr' in df.columns and 'obtr_bb_middle_band' in df.columns:
             mask_flow_sell = df['obtr'] < df['obtr_bb_middle_band']
             
        # SINAL FINAL DE VENDA
        final_sell_signal = mask_regime_ok & mask_trend_down & mask_sell_zone & mask_stoch_sell & mask_flow_sell
        
        # 6. Aplicação dos Sinais no DataFrame
        df.loc[final_buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[final_sell_signal, 'SIGNAL'] = 'SELL'
        
        # Opcional: Adicionar colunas de Stop Loss Sugerido no DF para uso posterior
        df['STOP_LOSS'] = np.nan
        df.loc[final_buy_signal, 'STOP_LOSS'] = df.loc[final_buy_signal, col_bb_lower]
        df.loc[final_sell_signal, 'STOP_LOSS'] = df.loc[final_sell_signal, col_bb_upper]

        return df