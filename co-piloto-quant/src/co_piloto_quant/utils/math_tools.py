import pandas as pd

def calculate_z_score(series: pd.Series, window: int = 252) -> pd.Series:
    """
    Calcula o Z-Score (Desvio Padrão da Média) de uma série temporal.

    Args:
        series (pd.Series): A série de dados.
        window (int): A janela móvel para cálculo da média e desvio padrão.

    Returns:
        pd.Series: A série de dados do Z-Score.
    """
    if not isinstance(series, pd.Series):
        raise TypeError("Input must be a pandas Series.")
        
    roll_mean = series.rolling(window=window).mean()
    roll_std = series.rolling(window=window).std()
    
    # Adiciona um epsilon para evitar divisão por zero
    z_score = (series - roll_mean) / (roll_std + 1e-9)
    
    return z_score

def safe_join(df_original: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """
    Faz o join de um novo DataFrame ao original, mas apenas com as colunas
    que ainda não existem no original para evitar sobreposição.

    Args:
        df_original (pd.DataFrame): O DataFrame principal.
        df_new (pd.DataFrame): O DataFrame com novas colunas.

    Returns:
        pd.DataFrame: O DataFrame original com as novas colunas.
    """
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

