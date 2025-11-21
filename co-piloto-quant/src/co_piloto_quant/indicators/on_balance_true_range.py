""" import pandas as pd
import numpy as np

def on_balance_true_range(data: pd.DataFrame) -> pd.DataFrame:
   
    if not all(col in data.columns for col in ['High', 'Low', 'Close']):
        raise ValueError("Input DataFrame must contain 'High', 'Low', and 'Close' columns.")

    high = data['High']
    low = data['Low']
    close = data['Close']
    prev_close = close.shift(1)

    
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    tr.iloc[0] = high.iloc[0] - low.iloc[0] 

 
    price_direction = np.sign(close.diff().fillna(0))

   
    obtr = (tr * price_direction).cumsum()

    return pd.DataFrame({'OBTR': obtr}, index=data.index) """

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

    return pd.DataFrame({'OBTR': obtr}, index=data.index)
calculate_obtr = on_balance_true_range
