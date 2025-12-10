import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import os

# Importamos as configurações e o novo registry de nomes
from co_piloto_quant.config import (
    BB_PERIOD, 
    STOCH_K_PERIOD, 
    STOCH_K_SMOOTH
)
from co_piloto_quant.indicators.names import IndicatorNames

class Strategy(ABC):
    """
    Classe base abstrata para todas as estratégias de trading.
    Define a interface que todas as estratégias concretas devem seguir,
    incluindo um pipeline de logging para persistência de dados.
    """

    def __init__(self, save_logs: bool = False):
        """
        Inicializa a estratégia.
        Args:
            save_logs (bool): Se True, salva o snapshot completo da estratégia em cada avaliação.
        """
        self.save_logs = save_logs

    @abstractmethod
    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Método central que contém a lógica de cálculo de sinais da estratégia.
        Deve ser implementado por cada subclasse.
        Args:
            df (pd.DataFrame): DataFrame contendo dados de OHLCV e todos os indicadores.
        Returns:
            pd.DataFrame: O DataFrame com as colunas de decisão (ex: 'SIGNAL').
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Retorna o nome único da estratégia."""
        pass

    def evaluate(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """
        Orquestrador: avalia a estratégia e salva um snapshot se o logging estiver habilitado.
        Args:
            df (pd.DataFrame): DataFrame de entrada com indicadores.
            ticker (str): O ticker do ativo sendo avaliado, usado para nomear o arquivo de log.
        Returns:
            pd.DataFrame: O DataFrame final com os sinais calculados.
        """
        # 1. Calcula os sinais usando a implementação da subclasse
        # Usamos uma cópia para garantir que o DataFrame original não seja modificado
        df_evaluated = self._calculate_signals(df.copy())

        # 2. Salva o "Deep Log" se a opção estiver habilitada
        if self.save_logs:
            self._save_strategy_snapshot(df_evaluated, ticker)

        return df_evaluated

    def _save_strategy_snapshot(self, df: pd.DataFrame, ticker: str):
        """
        Salva o DataFrame do estado completo da estratégia em um arquivo Parquet.
        Este método contém toda a granularidade necessária para análises de ML futuras.
        """
        try:
            output_dir = "data/strategy_logs"
            os.makedirs(output_dir, exist_ok=True)
            file_path = os.path.join(output_dir, f"{ticker}_deep_log.parquet")
            
            # Salva em formato Parquet, que é eficiente para grandes DataFrames
            df.to_parquet(file_path, index=True, engine='pyarrow')
            
        except Exception as e:
            # Não quebra a execução principal se o log falhar, apenas avisa.
            print(f"Alerta [Deep Logging]: Não foi possível salvar o log para o ticker {ticker}. Erro: {e}")


class AdaptiveSniperStrategy(Strategy):
    """
    Implementação da estratégia 'Sniper Adaptativo'.
    Utiliza Z-Scores de Hurst e Entropia para filtrar regimes, 
    e Bandas de Bollinger + Estocástico para gatilhos precisos.
    """
    def __init__(self, bb_entry_std_dev: float = 0.45, bb_exit_std_dev: float = 2.0, entropy_chaos_threshold: float = 1.0, save_logs: bool = False):
        # Passa o controle do logging para a classe pai
        super().__init__(save_logs=save_logs)
        self.bb_entry_std_dev = bb_entry_std_dev
        self.bb_exit_std_dev = bb_exit_std_dev
        self.entropy_chaos_threshold = entropy_chaos_threshold

    def get_name(self) -> str:
        return "AdaptiveSniperStrategy"

    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """ Lógica de cálculo de sinais, antes contida em 'evaluate'. """
        
        # 1. Definição centralizada dos nomes das colunas via IndicatorNames
        col_bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, self.bb_entry_std_dev)
        col_bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, self.bb_entry_std_dev)
        
        # A banda de saída agora é configurável
        col_bb_upper_exit = IndicatorNames.bollinger_upper(BB_PERIOD, self.bb_exit_std_dev)
        
        col_stoch_k  = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
        col_wwma     = IndicatorNames.wwma(200)
        col_hurst_z  = IndicatorNames.hurst_z()
        # A janela de entropia é 20 em analysis.py
        col_entropy_z = IndicatorNames.entropy_z(20) 

        df['SIGNAL'] = 'HOLD'
        
        required_cols = [col_bb_upper, col_stoch_k, col_hurst_z, col_entropy_z, col_bb_upper_exit]
        missing_cols = [c for c in required_cols if c not in df.columns]
        if missing_cols:
            return df

        # 3. Filtros de Regime, agora usando o threshold de entropia configurável
        mask_regime_ok = (df.get(col_hurst_z, pd.Series(0, index=df.index)).fillna(0) >= -0.5) & \
                         (df.get(col_entropy_z, pd.Series(10, index=df.index)).fillna(10) <= self.entropy_chaos_threshold)
        
        # 4. Lógica de COMPRA
        mask_buy_zone = (df['close'] >= df[col_bb_lower]) & (df['close'] <= df[col_bb_upper])
        mask_stoch_buy = df[col_stoch_k] < 30
        
        col_obtr_mid = IndicatorNames.tpm_band('obtr', 'middle_band')
        col_wad_mid = IndicatorNames.tpm_band('wad', 'middle_band')
        
        mask_flow_buy = pd.Series(False, index=df.index)
        if 'obtr' in df.columns and col_obtr_mid in df.columns:
             mask_flow_buy = (df['obtr'] > df[col_obtr_mid])
        if 'wad' in df.columns and col_wad_mid in df.columns:
             mask_flow_buy = mask_flow_buy | (df['wad'] > df[col_wad_mid])

        final_buy_signal = mask_regime_ok & mask_buy_zone & mask_stoch_buy & mask_flow_buy
        
        # 5. Lógica de VENDA, agora usando a banda de saída configurável
        mask_trend_down = df['close'] < df.get(col_wwma, np.inf)
        mask_sell_zone = df['close'] >= df[col_bb_upper_exit]
        mask_stoch_sell = df[col_stoch_k] > 70
        
        mask_flow_sell = pd.Series(False, index=df.index)
        if 'obtr' in df.columns and col_obtr_mid in df.columns:
             mask_flow_sell = df['obtr'] < df[col_obtr_mid]
             
        final_sell_signal = mask_regime_ok & mask_trend_down & mask_sell_zone & mask_stoch_sell & mask_flow_sell
        
        # 6. Aplicação dos Sinais
        df.loc[final_buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[final_sell_signal, 'SIGNAL'] = 'SELL'
        
        df['STOP_LOSS'] = np.nan
        df.loc[final_buy_signal, 'STOP_LOSS'] = df.loc[final_buy_signal, col_bb_lower]
        df.loc[final_sell_signal, 'STOP_LOSS'] = df.loc[final_sell_signal, col_bb_upper_exit]

        return df