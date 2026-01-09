import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
import os

# Importamos as configurações e o novo registry de nomes
from co_piloto_quant.config import (
    BB_PERIOD, 
    STOCH_K_PERIOD, 
    STOCH_K_SMOOTH,
    HURST_WINDOW
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

        # --- SANITIZAÇÃO GLOBAL ---
        df = df.copy()
        df = df.sort_index()
        df = df.loc[~df.index.duplicated()]

        # Garante que tudo seja float quando possível
        for col in df.columns:
            if pd.api.types.is_integer_dtype(df[col]):
                df[col] = df[col].astype(float)

        def safe_series(col, default):
            if col in df.columns:
                return df[col]
            return pd.Series(default, index=df.index)

        # --- NOMES DAS COLUNAS ---
        col_bb_upper = IndicatorNames.bollinger_upper(BB_PERIOD, self.bb_entry_std_dev)
        col_bb_lower = IndicatorNames.bollinger_lower(BB_PERIOD, self.bb_entry_std_dev)
        col_bb_upper_exit = IndicatorNames.bollinger_upper(BB_PERIOD, self.bb_exit_std_dev)

        col_stoch_k = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
        col_wwma = IndicatorNames.wwma(200)
        col_hurst_raw = IndicatorNames.hurst_z(HURST_WINDOW) # Nome original da coluna é hurst_z, mas é o valor bruto
        col_entropy_z = IndicatorNames.entropy_z(20)

        df['SIGNAL'] = 'HOLD'

        required_cols = [col_bb_upper, col_bb_lower, col_stoch_k, col_hurst_raw, col_entropy_z, col_bb_upper_exit]
        if any(c not in df.columns for c in required_cols):
            # Adicionado log para clareza
            missing = [c for c in required_cols if c not in df.columns]
            print(f"Alerta [AdaptiveSniper]: Faltando colunas essenciais: {missing}. Nenhum sinal será gerado.")
            return df

        # --- REGIME ---
        hurst_raw = safe_series(col_hurst_raw, 0.5)
        entropy = safe_series(col_entropy_z, 10.0)

        # AJUSTE CRÍTICO: Correção do uso do Hurst.
        # O valor bruto (0-1) não deve ser comparado com -0.5. Calculamos o Z-Score para normalizá-lo.
        # Um Z-Score > 0.5 indica que o mercado está estatisticamente mais em tendência do que sua média recente.
        hurst_mean = hurst_raw.rolling(252, min_periods=30).mean()
        hurst_std = hurst_raw.rolling(252, min_periods=30).std()
        hurst_z_score = (hurst_raw - hurst_mean) / hurst_std
        
        # O filtro de regime agora busca períodos com tendência estatisticamente relevante e baixa entropia (não-caótico).
        mask_regime_ok = (hurst_z_score > 0.5) & (entropy <= self.entropy_chaos_threshold)


        # --- BUY ---
        close = df['close']
        bb_lower = df[col_bb_lower]
        stoch = df[col_stoch_k]

        # AJUSTE LÓGICO: Mudança para uma entrada "Sniper" verdadeira.
        # Em vez de comprar DENTRO das bandas (reversão à média), compramos no EXTREMO (toque na banda inferior).
        # Isso alinha a entrada com a ideia de "sniper", pegando o ponto de possível virada.
        mask_buy_zone = close <= bb_lower
        mask_stoch_buy = stoch < 30

        mask_flow_buy = pd.Series(True, index=df.index)

        if 'obtr' in df.columns:
            obtr_mid = next((c for c in df.columns if c.startswith('obtr_') and '_middle' in c), None)
            if obtr_mid:
                mask_flow_buy &= df['obtr'] > df[obtr_mid]

        if 'wad' in df.columns:
            wad_mid = next((c for c in df.columns if c.startswith('wad_') and '_middle' in c), None)
            if wad_mid:
                mask_flow_buy |= df['wad'] > df[wad_mid]

        final_buy_signal = mask_regime_ok & mask_buy_zone & mask_stoch_buy & mask_flow_buy

        # --- SELL ---
        wwma = safe_series(col_wwma, np.inf)

        mask_trend_down = close < wwma
        mask_sell_zone = close >= df[col_bb_upper_exit]
        mask_stoch_sell = stoch > 70

        mask_flow_sell = pd.Series(True, index=df.index)

        if 'obtr' in df.columns:
            obtr_mid = next((c for c in df.columns if c.startswith('obtr_') and '_middle' in c), None)
            if obtr_mid:
                mask_flow_sell &= df['obtr'] < df[obtr_mid]

        final_sell_signal = mask_regime_ok & mask_trend_down & mask_sell_zone & mask_stoch_sell & mask_flow_sell

        # --- APLICAÇÃO ---
        df.loc[final_buy_signal, 'SIGNAL'] = 'BUY'
        df.loc[final_sell_signal, 'SIGNAL'] = 'SELL'

        df['STOP_LOSS'] = np.nan
        df.loc[final_buy_signal, 'STOP_LOSS'] = bb_lower
        df.loc[final_sell_signal, 'STOP_LOSS'] = df[col_bb_upper_exit]

        # Adiciona os valores calculados para análise e logging
        df['hurst_z_score'] = hurst_z_score

        return df