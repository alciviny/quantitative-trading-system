import pandas as pd
from typing import List

from co_piloto_quant.data.indicator_engine import IndicatorEngine
from co_piloto_quant import config

def process_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Processes the raw price data to add all required technical indicators.

    Args:
        df (pd.DataFrame): The raw DataFrame with OHLCV data.

    Returns:
        pd.DataFrame: The DataFrame enriched with indicator data.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Input must be a pandas DataFrame.")

    # Instantiate the engine with the raw data
    engine = IndicatorEngine(df)

    # Add indicators using the new engine and settings from config
    # The method chaining is possible thanks to the engine design
    engine.add_indicator(
        'bollinger_bands', 
        period=config.BB_PERIOD, 
        std_devs=config.PRICE_BB_DEVIATIONS
    ).add_indicator(
        'ifr',
        period=config.IFR_PERIOD
    ).add_indicator(
        'system_tpm',
        period=config.SYSTEM_PERIOD,
        deviations=config.SYSTEM_DEVIATIONS
    ).add_indicator(
        'stochastic',
        k_period=config.STOCH_K_PERIOD,
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=config.STOCH_D_SMOOTH
    )
    
    # We could add more indicators here in the future easily
    # Example:
    # .add_indicator('ww_ma', period=50)

    # Get the final DataFrame with all indicators
    processed_df = engine.get_data()

    return processed_df

if __name__ == '__main__':
    # Example Usage (demonstration purposes) 
    # This block will only run if the script is executed directly
    
    # Create a sample DataFrame 
    # In a real scenario, this data would be loaded from a file or an API
    sample_data = {
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 110],
        'high': [103, 104, 103, 105, 106, 106, 109, 110, 110, 112],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 109],
        'close': [102, 103, 102, 104, 105, 105, 108, 109, 109, 111],
        'volume': [1000, 1500, 1200, 1800, 2000, 1700, 2200, 2500, 2300, 2800]
    }
    # Create a date index for the sample data
    index = pd.to_datetime(pd.date_range(start='2023-01-01', periods=10, freq='D'))
    sample_df = pd.DataFrame(sample_data, index=index)
    
    print("--- Original DataFrame ---")
    print(sample_df.head())
    print("\n" + "="*50 + "\n")
    
    # Process the data to add indicators
    enriched_df = process_data(sample_df)
    
    print("--- Enriched DataFrame ---")
    # Displaying only the last few rows and all columns to see the indicator values
    print(enriched_df.tail()) 
    print("\nColumns added:")
    print(set(enriched_df.columns) - set(sample_df.columns))
