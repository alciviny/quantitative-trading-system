import pandas as pd
import numpy as np
import pandera as pa
from pandera.errors import SchemaError
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average

def bollinger_bands(data: pd.DataFrame, column: str = 'close', period: int = 200, std_devs: list = [2.0]) -> pd.DataFrame:
    """
    Calcula as Bandas de Bollinger usando a Média Móvel de Wilder para a banda central.

    Args:
        data (pd.DataFrame): DataFrame com os dados de preço.
        column (str, optional): A coluna de preço a ser usada. Defaults to 'close'.
        period (int, optional): O período para a média móvel e o desvio padrão. Defaults to 200.
        std_devs (list, optional): Lista de multiplicadores de desvio padrão para as bandas. 
                                   Defaults to [2.0].

    Returns:
        pd.DataFrame: DataFrame com a banda média, e as bandas superiores e inferiores.

    Raises:
        ValueError: Se a coluna de preço não for encontrada ou os dados forem inválidos.
    """
    try:
        schema = pa.DataFrameSchema(
            {
                column: pa.Column(float, required=True, coerce=True)
            },
            strict=False,  # Permite outras colunas no DataFrame
        )
        schema.validate(data)
    except SchemaError as e:
        raise ValueError(f"A validação dos dados de entrada falhou para a coluna '{column}'. Verifique se a coluna existe e contém dados numéricos. Erro original: {e}")

    
    middle_band = ww_moving_average(data, column=column, period=period)
    
   
    squared_diff = (data[column] - middle_band)**2
    variance = squared_diff.ewm(alpha=1/period, adjust=False).mean()
    rolling_std = np.sqrt(variance)

    
    bands_df = pd.DataFrame({f'BB_Middle_{period}': middle_band})

    
    for std_dev_multiplier in std_devs:
        upper_band = middle_band + (rolling_std * std_dev_multiplier)
        lower_band = middle_band - (rolling_std * std_dev_multiplier)
        bands_df[f'BB_Upper_{period}_{std_dev_multiplier}'] = upper_band
        bands_df[f'BB_Lower_{period}_{std_dev_multiplier}'] = lower_band
        
    return bands_df