import pandas as pd

def ww_moving_average(data: pd.DataFrame, column: str = 'close', period: int = 200) -> pd.Series:
    """
    Calcula a Média Móvel de Welles Wilder (Wilder's Moving Average).

    Esta é uma média móvel exponencial com um fator de suavização de 1/período.

    Args:
        data (pd.DataFrame): DataFrame com os dados.
        column (str, optional): A coluna a ser usada para o cálculo. Defaults to 'close'.
        period (int, optional): O período da média móvel. Defaults to 200.

    Returns:
        pd.Series: Uma série contendo os valores da média móvel.

    Raises:
        ValueError: Se a coluna especificada não for encontrada.
    """
    if column not in data.columns:
        raise ValueError(f"Column '{column}' not found in the input DataFrame. Found: {data.columns.tolist()}")

    
    wwma = data[column].ewm(alpha=1/period, adjust=False).mean()
    wwma.name = f'WWMA_{period}'

    return wwma
