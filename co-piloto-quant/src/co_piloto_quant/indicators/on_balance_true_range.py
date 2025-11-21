import pandas as pd
import numpy as np

def on_balance_true_range(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o On-Balance True Range (OBTR).
    
    O OBTR é um indicador que acumula True Range ponderado pela direção do preço,
    funcionando como um OBV baseado em volatilidade ao invés de volume.
    
    Args:
        data: DataFrame com colunas 'High', 'Low', 'Close'
        
    Returns:
        DataFrame com coluna 'OBTR'
        
    Raises:
        ValueError: Se colunas necessárias não existirem
    """
    required_cols = ['high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"Input DataFrame must contain {required_cols} columns.")

    high = data['high']
    low = data['low']
    close = data['close']
    prev_close = close.shift(1)

   
    tr = np.maximum.reduce([
        high - low,                    # Range normal
        (high - prev_close).abs(),     # Gap de alta
        (low - prev_close).abs()       # Gap de baixa
    ])
    
   
    price_direction = np.sign(close.diff().fillna(0))

   
    obtr = (tr * price_direction).cumsum()

    return pd.DataFrame({'obtr': obtr}, index=data.index)
calculate_obtr = on_balance_true_range
