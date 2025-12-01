import pandas as pd
import pandas_ta as ta

def calculate_ifr_tpm(data: pd.DataFrame, column: str = 'close', period: int = 120) -> pd.DataFrame:
    """
    Calcula o IFR (Índice de Força Relativa) com sanitização de dados para robustez.
    """
    col_lower = column.lower()
    if col_lower not in data.columns:
        raise ValueError(f"Coluna '{col_lower}' não encontrada no DataFrame. Colunas disponíveis: {data.columns.tolist()}")

    # --- CORREÇÃO DE ROBUSTEZ 1: Sanitização do Input ---
    # Garante que a entrada seja uma Series, mesmo que o slicing retorne um DataFrame
    series_input = data[col_lower]
    if isinstance(series_input, pd.DataFrame):
        series_input = series_input.iloc[:, 0]

    # --- CORREÇÃO DE ROBUSTEZ 2: Remoção de Duplicatas no Índice ---
    # Evita erros em bibliotecas como pandas_ta com dados de índice duplicado
    series_input = series_input[~series_input.index.duplicated(keep='first')]

    # Calcula o RSI usando a série sanitizada
    ifr_series = ta.rsi(close=series_input, length=period)
    
    # Cria o DataFrame de resultado
    result_df = pd.DataFrame({f'IFR_{period}': ifr_series, 'IFR_50': 50})

    # --- CORREÇÃO DE ROBUSTEZ 3: Reindexação ---
    # Garante que o output tenha o mesmo índice que o input original, preenchendo NaNs onde necessário
    result_df = result_df.reindex(data.index)
    
    return result_df

ifr_tpm = calculate_ifr_tpm