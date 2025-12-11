
import pandas as pd
import logging
from typing import Dict, Callable, Any

# Imports explícitos para evitar confusão entre módulos e funções
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class IndicatorEngine:
    """
    A class to calculate and add technical indicators to a given price DataFrame.
    """
    
    _indicator_registry: Dict[str, Callable[..., pd.DataFrame]] = {
        'bollinger_bands': bollinger_bands,
        'ifr': calculate_ifr_tpm,
        'ww_ma': ww_moving_average,
        'system_tpm': calculate_system_tpm,
        'stochastic': calculate_stochastic_custom,
    }

    def __init__(self, data: pd.DataFrame):
        """
        Initializes the IndicatorEngine with price data.

        Args:
            data (pd.DataFrame): DataFrame with at least 'high', 'low', 'close', 'volume' columns.
        """
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Input data must be a non-empty pandas DataFrame.")
        
        required_columns = {'high', 'low', 'close'}
        if not required_columns.issubset(data.columns):
            raise ValueError(f"Input DataFrame must contain the following columns: {required_columns}")

        self.data = data.copy()

    def add_indicator(self, name: str, **kwargs: Any) -> 'IndicatorEngine':
        """
        Adds an indicator to the DataFrame.

        Args:
            name (str): The name of the indicator to add (must exist in the registry).
            **kwargs: Arbitrary keyword arguments to pass to the indicator calculation function.

        Returns:
            IndicatorEngine: The instance itself to allow for method chaining.
        """
        indicator_func = self._indicator_registry.get(name)
        
        if not indicator_func:
            logging.warning(f"Indicator '{name}' not found in registry. Skipping.")
            return self
        
        try:
            logging.info(f"Calculating indicator '{name}' with params: {kwargs}")
            indicator_df = indicator_func(self.data, **kwargs)
            
            # Merge the results back into the main DataFrame
            self.data = self.data.merge(indicator_df, left_index=True, right_index=True, how='left')

        except Exception as e:
            logging.error(f"Failed to calculate indicator '{name}': {e}", exc_info=True)
            # Continue processing even if one indicator fails
        
        return self

    def get_data(self) -> pd.DataFrame:
        """
        Returns the DataFrame with all the added indicators.

        Returns:
            pd.DataFrame: The processed DataFrame.
        """
        return self.data

