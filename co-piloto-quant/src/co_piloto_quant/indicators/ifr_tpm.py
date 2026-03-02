import pandas as pd

from co_piloto_quant.indicators.names import IndicatorNames

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
    # Evita erros em bibliotecas como ta com dados de índice duplicado
    series_input = series_input[~series_input.index.duplicated(keep='first')]

    # Calcula o RSI usando a série sanitizada com a biblioteca 'ta'
    from ta.momentum import RSIIndicator
    rsi_indicator = RSIIndicator(close=series_input, window=period)
    ifr_series = rsi_indicator.rsi()

    # --- CORREÇÃO DE ROBUSTEZ ADICIONAL: Lidar com output Nulo ---
    # Se ta não puder calcular (e.g., dados insuficientes), pode retornar None.
    # Usa IndicatorNames para nomear a coluna.
    column_name = IndicatorNames.rsi(period)
    if ifr_series is None:
        ifr_series = pd.Series(index=data.index, dtype=float, name=column_name)
    else:
        ifr_series.name = column_name
    
    # Cria o DataFrame de resultado a partir da série (que agora garantidamente tem um índice)
    result_df = pd.DataFrame(ifr_series)
    # Corrige para usar o valor real do IFR calculado
    result_df['IFR_50'] = result_df[column_name]

    # --- CORREÇÃO DE ROBUSTEZ 3: Reindexação ---
    # Garante que o output tenha o mesmo índice que o input original, preenchendo NaNs onde necessário
    result_df = result_df.reindex(data.index)
    
    return result_df

ifr_tpm = calculate_ifr_tpm