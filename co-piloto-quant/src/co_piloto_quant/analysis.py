import pandas as pd
import pandas_ta as ta

def calculate_indicators(df: pd.DataFrame, rsi_period: int = 14) -> pd.DataFrame:
  
    print(f"Calculando indicadores (MME 20, MME 50, RSI {rsi_period})...")
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    
    # Calcula o RSI com o período configurável e o adiciona em uma coluna chamada 'RSI'
    rsi_series = df.ta.rsi(length=rsi_period)
    df['RSI'] = rsi_series
    
    print("Indicadores calculados.")
    return df

def check_rules(latest_data: pd.Series) -> dict:
  
    regras = {}

    # Tendência (Preço > MME 20)
    regras["Preço > MME 20"] = latest_data['close'] > latest_data['EMA_20']

    # Contexto (MME 20 > MME 50)
    regras["MME 20 > MME 50"] = latest_data['EMA_20'] > latest_data['EMA_50']

    # Momentum (RSI > 50)
    regras["RSI > 50"] = latest_data['RSI'] > 50

    # Price Action (Último candle foi positivo?)
    regras["Candle Positivo"] = latest_data['close'] > latest_data['open']

    return regras