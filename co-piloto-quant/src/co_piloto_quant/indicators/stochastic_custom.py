import pandas as pd

def calculate_stochastic_custom(data: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula o Estocástico Lento Padrão (Normal).
    
    Configuração:
    1. %K Bruto: Janela de 80 períodos (conforme solicitado).
    2. %K Lento (Slow %K): SMA de 3 períodos do Raw %K.
    3. %D (Linha de Sinal): SMA de 3 períodos do Slow %K (Padrão de mercado).

    Args:
        data (pd.DataFrame): DataFrame com colunas 'high', 'low', 'close'.

    Returns:
        pd.DataFrame: DataFrame com as colunas 'stoch_k_80_3' e 'stoch_d_3'.
    """
    stoch_period = 80  # Período longo solicitado
    k_smooth = 3       # Suavização padrão do %K
    d_smooth = 3       # Suavização padrão do %D (Linha de Sinal)

    required_cols = ['high', 'low', 'close']
    if not all(col in data.columns for col in required_cols):
        raise ValueError(f"O DataFrame de entrada precisa conter as colunas: {required_cols}")

    # 1. Cálculo do %K Bruto (Raw %K)
    lowest_low = data['low'].rolling(window=stoch_period).min()
    highest_high = data['high'].rolling(window=stoch_period).max()
    
    # Proteção contra divisão por zero (caso High == Low)
    denominator = highest_high - lowest_low
    denominator = denominator.replace(0, float('nan')) 
    
    raw_k = ((data['close'] - lowest_low) / denominator) * 100

    # 2. Cálculo do %K Lento (Slow %K) - Usando Média Simples (SMA)
    slow_k = raw_k.rolling(window=k_smooth).mean()
    slow_k.name = 'stoch_k_80_3'

    # 3. Cálculo do %D (Linha de Sinal) - Usando Média Simples (SMA)
    # AQUI ESTÁ A MUDANÇA: Usamos .mean() (SMA) com período 3, em vez de WWMA 14.
    slow_d = slow_k.rolling(window=d_smooth).mean()
    slow_d.name = 'stoch_d_3'

    # Monta o DataFrame final
    result_df = pd.concat([slow_k, slow_d], axis=1)

    return result_df