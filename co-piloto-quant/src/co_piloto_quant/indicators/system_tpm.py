
import pandas as pd
from .multi_bollinger_bands import multi_bollinger_bands
from .on_balance_true_range import on_balance_true_range
from .williams_ad import williams_ad

def calculate_system_tpm(
    data: pd.DataFrame, 
    indicator: str = 'obtr', 
    period: int = 200, 
    deviations: list = [0.45, 1.0, 1.5, 2.0]
) -> pd.DataFrame:
    """
    Calcula o "System TPM", que consiste em aplicar as Bandas de Bollinger Múltiplas
    sobre um indicador base (OBTR ou Williams A/D).

    Args:
        data (pd.DataFrame): O DataFrame contendo os dados de preço (OHLC).
        indicator (str, optional): O indicador base a ser usado. 
                                   Pode ser 'obtr' ou 'wad'. Default é 'obtr'.
        period (int, optional): O período para as bandas. Default é 200.
        deviations (list, optional): A lista de desvios para as bandas. 
                                      Default é [0.45, 1.0, 1.5, 2.0].

    Returns:
        pd.DataFrame: Um DataFrame contendo o indicador base e suas respectivas
                      bandas de Bollinger múltiplas.
    """
    if indicator not in ['obtr', 'wad']:
        raise ValueError("O indicador deve ser 'obtr' ou 'wad'.")

    # Calcula o indicador base
    if indicator == 'obtr':
        indicator_series = on_balance_true_range(data)['OBTR']
        indicator_series.name = 'obtr'
    elif indicator == 'wad':
        indicator_series = williams_ad(data)
        indicator_series.name = 'wad'

    # Calcula as bandas de Bollinger múltiplas sobre o indicador
    bb_df = multi_bollinger_bands(
        data=indicator_series,
        period=period,
        deviations=deviations
    )

    # Renomeia as colunas para evitar conflitos e adicionar clareza
    bb_df = bb_df.rename(columns=lambda col: f"{indicator}_bb_{col}")

    # Combina o indicador original com suas bandas
    result_df = pd.concat([indicator_series, bb_df], axis=1)

    return result_df
