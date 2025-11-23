import pandas as pd
from .ww_moving_average import ww_moving_average

def calculate_stochastic_custom(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o Estocástico Lento Customizado.

    1. %K Bruto (Raw %K): Janela de 80 períodos.
    2. %K Lento (Slow %K): SMA de 3 períodos do Raw %K.
    3. %D (Linha de Sinal): WWMA de 14 períodos do Slow %K.

    Args:
        data (pd.DataFrame): DataFrame com colunas 'high', 'low', 'close'.

    Returns:
        pd.DataFrame: DataFrame com as colunas 'stoch_k_80_3' e 'stoch_d_14'.
    """
    stoch_period = 80
    k_smooth = 3
    d_smooth = 14

    required_cols = ['high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"O DataFrame de entrada precisa conter as colunas: {required_cols}")

    # 1. Cálculo do %K Bruto (Raw %K)
    lowest_low = data['low'].rolling(window=stoch_period).min()
    highest_high = data['high'].rolling(window=stoch_period).max()
    raw_k = ((data['close'] - lowest_low) / (highest_high - lowest_low)) * 100

    # 2. Cálculo do %K Lento (Slow %K)
    slow_k = raw_k.rolling(window=k_smooth).mean()
    slow_k.name = 'stoch_k_80_3'

    # 3. Cálculo do %D (Linha de Sinal)
    # A função ww_moving_average espera um DataFrame e o nome da coluna
    slow_k_df = pd.DataFrame(slow_k)
    slow_d = ww_moving_average(slow_k_df, column='stoch_k_80_3', period=d_smooth)
    slow_d.name = 'stoch_d_14'

    # Monta o DataFrame final
    result_df = pd.concat([slow_k, slow_d], axis=1)

    return result_df
