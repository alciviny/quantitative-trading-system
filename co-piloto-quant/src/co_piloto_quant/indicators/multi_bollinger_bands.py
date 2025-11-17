import pandas as pd

def wilder_moving_average(data: pd.Series, period: int) -> pd.Series:
    """Calcula a Média Móvel de Wilder (Wilder's Moving Average)."""
    return data.ewm(alpha=1/period, adjust=False).mean()

def multi_bollinger_bands(
    data: pd.Series, 
    period: int = 200, 
    deviations: list = [0.45, 1.0, 1.5, 2.0]
) -> pd.DataFrame:
    """
    Calcula Bandas de Bollinger customizadas com múltiplos desvios e média de Welles Wilder.

    Args:
        data (pd.Series): A série de dados de entrada (geralmente o output de outro indicador).
        period (int, optional): O período para a média móvel e o desvio padrão. Default é 200.
        deviations (list, optional): Uma lista de multiplicadores de desvio padrão para as bandas.
                                      Default é [0.45, 1.0, 1.5, 2.0].

    Returns:
        pd.DataFrame: Um DataFrame contendo a média móvel (banda central) e todos os
                      pares de bandas superior e inferior.
    """
    if not isinstance(data, pd.Series):
        raise TypeError("O dado de entrada 'data' deve ser uma pandas Series.")

    # 1. Calcular a Banda Central (Média Móvel de Welles Wilder)
    middle_band = wilder_moving_average(data, period)
    middle_band.name = 'middle_band'

    # 2. Calcular o Desvio Padrão
    rolling_std = data.rolling(window=period).std()

    # 3. Criar o DataFrame de resultados
    results = pd.DataFrame(middle_band)

    # 4. Calcular e adicionar cada par de bandas
    for dev in sorted(deviations):
        upper_band = middle_band + (rolling_std * dev)
        lower_band = middle_band - (rolling_std * dev)
        
        # Formata o nome da coluna para ser claro e evitar pontos
        dev_str = str(dev).replace('.', '_')
        
        results[f'upper_band_{dev_str}'] = upper_band
        results[f'lower_band_{dev_str}'] = lower_band

    return results
