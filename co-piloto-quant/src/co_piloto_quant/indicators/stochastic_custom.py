import pandas as pd

def calculate_stochastic_custom(data: pd.DataFrame, k_period: int = 80, k_smooth: int = 3, d_smooth: int = 3) -> pd.DataFrame:
    """
    Calcula o Oscilador Estocástico Lento com parâmetros customizáveis.

    Args:
        data (pd.DataFrame): DataFrame com colunas 'high', 'low', 'close'.
        k_period (int): Período de lookback para o %K Bruto.
        k_smooth (int): Período da Média Móvel Simples para suavizar o %K Bruto, criando o %K Lento.
        d_smooth (int): Período da Média Móvel Simples para a linha de sinal (%D).

    Returns:
        pd.DataFrame: DataFrame com as colunas do estocástico ('stoch_k' e 'stoch_d')
                      com nomes dinâmicos baseados nos parâmetros.
    """
    required_cols = ['high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"O DataFrame de entrada precisa conter as colunas: {required_cols}")

    # 1. Cálculo do %K Bruto (Raw %K)
    lowest_low = data['low'].rolling(window=k_period).min()
    highest_high = data['high'].rolling(window=k_period).max()

    # Proteção contra divisão por zero
    denominator = highest_high - lowest_low
    denominator = denominator.replace(0, float('nan'))

    raw_k = ((data['close'] - lowest_low) / denominator) * 100

    # 2. Cálculo do %K Lento (Slow %K)
    slow_k = raw_k.rolling(window=k_smooth).mean()
    slow_k.name = f'stoch_k_{k_period}_{k_smooth}'

    # 3. Cálculo do %D (Linha de Sinal)
    slow_d = slow_k.rolling(window=d_smooth).mean()
    slow_d.name = f'stoch_d_{k_period}_{k_smooth}_{d_smooth}'

    result_df = pd.concat([slow_k, slow_d], axis=1)

    return result_df