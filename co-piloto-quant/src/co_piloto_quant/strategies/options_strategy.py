# -*- coding: utf-8 -*-
"""
options_strategy.py

Estratégia que gera um sinal direcional para um ativo-objeto e,
em seguida, seleciona uma opção de compra (CALL) ou venda (PUT) baseada nesse sinal.
"""
import pandas as pd
import numpy as np

# Imports de outros módulos do projeto
from co_piloto_quant.strategies.base import Strategy
from co_piloto_quant.strategies.rules import check_rules
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy


# TODO: Mover esta função para um local central, como 'src/co_piloto_quant/indicators/factory.py'
def calculate_required_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula os indicadores que não vêm pré-calculados nos arquivos Parquet.
    Esta é uma versão adaptada da função 'calculate_missing_indicators' de 'walk_forward_validation.py'.
    """
    df = df.copy()
    
    # Garante que a série de preços de fechamento não tenha NaNs para os cálculos
    # CRITICAL: Only ffill used to prevent lookahead bias.
    close_s = df['close'].ffill()
    df.dropna(subset=['close'], inplace=True) # Remove linhas iniciais se o ffill não for suficiente

    # --- Hurst ---
    try:
        hurst_window = 72
        hurst_col_name = IndicatorNames.hurst_z(hurst_window)
        # Previne erro se a coluna já existir
        if hurst_col_name not in df.columns:
            hurst_series = calculate_rolling_hurst(close_s, window=hurst_window, kind='returns')
            hurst_series = hurst_series.replace([np.inf, -np.inf], np.nan)
            rolling_mean_h = hurst_series.rolling(252, min_periods=1).mean()
            rolling_std_h = hurst_series.rolling(252, min_periods=1).std().replace(0, np.nan)
            df[hurst_col_name] = ((hurst_series - rolling_mean_h) / rolling_std_h).fillna(0.5)
    except Exception:
        if hurst_col_name not in df.columns:
            df[hurst_col_name] = 0.5

    # --- Entropy ---
    try:
        entropy_window = 20
        entropy_col_name = IndicatorNames.entropy_z(entropy_window)
        if entropy_col_name not in df.columns:
            entropy_series = calculate_rolling_entropy(close_s, window=entropy_window)
            entropy_series = entropy_series.replace([np.inf, -np.inf], np.nan)
            
            rolling_mean_e = entropy_series.rolling(252, min_periods=1).mean()
            rolling_std_e = entropy_series.rolling(252, min_periods=1).std().replace(0, np.nan)
            df[entropy_col_name] = ((entropy_series - rolling_mean_e) / rolling_std_e).fillna(0.5)
    except Exception:
        if entropy_col_name not in df.columns:
            df[entropy_col_name] = 0.5
            
    # TODO: Adicionar outros indicadores que sejam necessários e não estejam no dataset base.
    # Ex: df.ta.bbands(..., append=True)

    return df


class OptionsStrategy(Strategy):
    """
    Estratégia de Opções baseada em Análise Direcional do Ativo-Objeto.
    """
    def __init__(self, save_logs: bool = False):
        super().__init__(save_logs=save_logs)

    def get_name(self) -> str:
        return "OptionsStrategy"

    def _calculate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcula o sinal direcional para o ativo-objeto.
        Esta implementação ainda não lida com a parte de seleção de opções,
        focando apenas na geração do sinal direcional (Compra/Venda/Neutro).
        """
        # 1. Calcula os indicadores necessários
        df_indicators = calculate_required_indicators(df)
        
        # 2. Verifica as regras de forma vetorial (para backtesting)
        # O resultado é um dicionário com pd.Series booleanas para 'entries' e 'exits'.
        rules_result = check_rules(df_indicators, mode='vectorized')

        # 3. Traduz os sinais vetoriais para uma única coluna 'SIGNAL'
        df_indicators['SIGNAL'] = 'NEUTRO'
        df_indicators.loc[rules_result['entries'], 'SIGNAL'] = 'COMPRA'
        df_indicators.loc[rules_result['exits'], 'SIGNAL'] = 'SAIR_COMPRA' # Exemplo
        df_indicators.loc[rules_result['short_entries'], 'SIGNAL'] = 'VENDA'
        df_indicators.loc[rules_result['short_exits'], 'SIGNAL'] = 'SAIR_VENDA' # Exemplo
        
        # Adiciona o motivo do bloqueio para análise
        # Esta parte é mais complexa de vetorizar e pode ser feita de forma mais simples
        # ou apenas para o último valor em um cenário "live".
        
        return df_indicators
