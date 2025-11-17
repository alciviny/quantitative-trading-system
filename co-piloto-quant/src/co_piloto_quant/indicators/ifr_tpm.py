import pandas as pd
import pandas_ta as ta

def calculate_ifr_tpm(data: pd.DataFrame, column: str = 'close', period: int = 120) -> pd.DataFrame:
    col_lower = column.lower()
    if col_lower not in data.columns:
        raise ValueError(f"Coluna '{col_lower}' não encontrada no DataFrame. Colunas disponíveis: {data.columns.tolist()}")

   
    ifr_series = data.ta.rsi(close=col_lower, length=period)

    
    result_df = pd.DataFrame(index=data.index)
    result_df[f'IFR_{period}'] = ifr_series
    
    result_df['IFR_50'] = 50

    return result_df

ifr_tpm = calculate_ifr_tpm