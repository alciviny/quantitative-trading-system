

import pandas as pd
import numpy as np
import logging
from typing import Dict, Callable, Any
from co_piloto_quant.indicators.special.path_elasticity import path_elasticity_index
from co_piloto_quant.indicators.special.directional_entropy import directional_entropy

def _path_elasticity_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Wrapper para path_elasticity_index que espera uma Série."""
    return path_elasticity_index(data['close'], **kwargs)

def _directional_entropy_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Wrapper para directional_entropy que espera uma Série."""
    return directional_entropy(data['close'], **kwargs)

# Imports dos indicadores - usando biblioteca 'ta' para análise técnica
import ta as ta_lib

from co_piloto_quant.indicators.special.ehlers_hilbert import ehlers_sinewave
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params

# --- IMPORTANTE: Importar o padronizador de nomes ---
from co_piloto_quant.indicators.names import IndicatorNames

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Funções de Indicadores  e Wrappers ---

def calculate_volatility(data: pd.DataFrame, period: int = 21) -> pd.DataFrame:
    """Calcula a volatilidade como o desvio padrão móvel dos log-retornos."""
    log_return = np.log(data['close'] / data['close'].shift(1))
    volatility = log_return.rolling(window=period).std() * np.sqrt(252) # Anualizado
    volatility_df = volatility.to_frame(name=IndicatorNames.volatility(period))
    return volatility_df

def _hurst_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Wrapper para a função hurst que espera uma Série."""
    return calculate_rolling_hurst(data['close'], **kwargs).to_frame()

def _entropy_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """Wrapper para a função entropy que espera uma Série."""
    return calculate_rolling_entropy(data['close'], **kwargs).to_frame()


def _halflife_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    # Retorna o DataFrame completo (beta, half_life, etc)
    return calculate_rolling_ou_params(data['close'], **kwargs)


def _ehlers_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    # O seu arquivo ehlers_hilbert.py já retorna um DataFrame rico com 'Hilbert_Status'
    return ehlers_sinewave(data, column='close')

def _chop_wrapper(data: pd.DataFrame, **kwargs) -> pd.DataFrame:
    # Choppiness Index manual
    window = kwargs.get('window', 14)
    high = data['high']
    low = data['low']
    # Range total da janela
    total_range = high.rolling(window).max() - low.rolling(window).min()
    # Soma dos ranges diários
    sum_range = (high - low).rolling(window).sum()
    # Fórmula clássica
    choppiness = 100 * np.log10(sum_range / total_range) / np.log10(window)
    return choppiness.to_frame(name=f'Choppiness_{window}')


class IndicatorEngine:
    """
    Classe para calcular e adicionar indicadores técnicos ao DataFrame,
    garantindo que os nomes das colunas sigam o padrão 'IndicatorNames'.
    """
    
    _indicator_registry: Dict[str, Callable[..., pd.DataFrame]] = {
        'bollinger_bands': bollinger_bands,
        'ifr': calculate_ifr_tpm,
        'ww_ma': ww_moving_average,
        'wwma': ww_moving_average,  # Alias
        'system_tpm': calculate_system_tpm,
        'stochastic': calculate_stochastic_custom,
        'hurst': _hurst_wrapper,
        'entropy': _entropy_wrapper,
        'directional_entropy': _directional_entropy_wrapper,
        'volatility': calculate_volatility,
        'path_elasticity': _path_elasticity_wrapper,
        'half_life': _halflife_wrapper,
        'ehlers_hilbert': _ehlers_wrapper,
        'choppiness': _chop_wrapper,
    }

    def __init__(self, data: pd.DataFrame):
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Input data must be a non-empty pandas DataFrame.")
        
        required_columns = {'high', 'low', 'close'}
        if not required_columns.issubset(data.columns):
            raise ValueError(f"Input DataFrame must contain: {required_columns}")

        self.data = data.copy()

    def add_indicator(self, name: str, **kwargs: Any) -> 'IndicatorEngine':
        indicator_func = self._indicator_registry.get(name)
        
        if not indicator_func:
            logging.warning(f"Indicador '{name}' não encontrado no registro.")
            return self
        
        try:
            logging.info(f"Calculando indicador '{name}' com params: {kwargs}")
            # 1. Calcula o indicador
            indicator_df = indicator_func(self.data, **kwargs)
            
            # --- Bloco de Padronização de Nomes ---
            # Garante que as colunas sigam o padrão de IndicatorNames,
            # independentemente de como a função de cálculo as nomeia.
            rename_map = {}
            
            if name == 'bollinger_bands':
                period = kwargs.get('period')
                std_devs = kwargs.get('std_devs', [])

                # Encontra a banda do meio (middle)
                middle_col = next((col for col in indicator_df.columns if 'middle' in col.lower()), None)
                if middle_col:
                    rename_map[middle_col] = IndicatorNames.bollinger_middle(period)

                # Encontra as bandas superior (upper) e inferior (lower)
                for dev in std_devs:
                    dev_str = str(float(dev))
                    upper_col = next((col for col in indicator_df.columns if 'upper' in col.lower() and dev_str in col), None)
                    if upper_col:
                        rename_map[upper_col] = IndicatorNames.bollinger_upper(period, dev)
                    
                    lower_col = next((col for col in indicator_df.columns if 'lower' in col.lower() and dev_str in col), None)
                    if lower_col:
                        rename_map[lower_col] = IndicatorNames.bollinger_lower(period, dev)

            elif name == 'stochastic':
                k_p = kwargs.get('k_period')
                k_s = kwargs.get('k_smooth')
                d_s = kwargs.get('d_smooth')
                
                k_col = next((col for col in indicator_df.columns if '_k' in col.lower() or 'slow_k' in col.lower()), None)
                if k_col:
                    rename_map[k_col] = IndicatorNames.stochastic_k(k_p, k_s)
                
                d_col = next((col for col in indicator_df.columns if '_d' in col.lower() or 'slow_d' in col.lower()), None)
                if d_col:
                    rename_map[d_col] = IndicatorNames.stochastic_d(k_p, k_s, d_s)

            elif name == 'ifr':
                period = kwargs.get('period')
                rsi_col = next((col for col in indicator_df.columns if 'rsi' in col.lower()), None)
                if rsi_col:
                    rename_map[rsi_col] = IndicatorNames.rsi(period)

            # 2. Aplica a renomeação se houver um mapa
            if rename_map:
                logging.info(f"Padronizando nomes de colunas: {rename_map}")
                indicator_df.rename(columns=rename_map, inplace=True)
            
            # --- Fim do Bloco de Padronização ---

            # 3. Faz o merge apenas das colunas que ainda não existem no DataFrame principal
            # O nome da coluna já deve vir correto da função de cálculo/wrapper
            cols_to_add = indicator_df.columns.difference(self.data.columns)
            if not cols_to_add.empty:
                self.data = self.data.merge(indicator_df[cols_to_add], left_index=True, right_index=True, how='left')

        except Exception as e:
            logging.error(f"Falha ao calcular ou padronizar o indicador '{name}': {e}", exc_info=True)
        
        return self

    def get_data(self) -> pd.DataFrame:
        return self.data
