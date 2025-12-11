import pandas as pd
from co_piloto_quant.indicators.names import IndicatorNames

def ww_moving_average(data: pd.DataFrame, column: str = 'close', period: int = 200) -> pd.DataFrame:
    """
    Calcula a Média Móvel de Welles Wilder (Wilder's Moving Average).

    Esta é uma média móvel exponencial com um fator de suavização de 1/período.

    Args:
        data (pd.DataFrame): DataFrame com os dados.
        column (str, optional): A coluna a ser usada para o cálculo. Defaults to 'close'.
        period (int, optional): O período da média móvel. Defaults to 200.

    Returns:
        pd.DataFrame: Um DataFrame contendo a WWMA.

    Raises:
        ValueError: Se a coluna especificada não for encontrada.
    """
    if column not in data.columns:
        raise ValueError(f"Column '{column}' not found in the input DataFrame. Found: {data.columns.tolist()}")

    
    wwma_series = data[column].ewm(alpha=1/period, adjust=False).mean()
    
    # Usa IndicatorNames para definir o nome da coluna
    column_name = IndicatorNames.wwma(period)
    wwma_series.name = column_name

    return wwma_series.to_frame()
