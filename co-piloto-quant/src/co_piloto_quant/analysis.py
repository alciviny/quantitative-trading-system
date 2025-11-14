import pandas as pd
import pandas_ta as ta

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
  
    print("Calculando indicadores (MME 20, MME 50, RSI)...")
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    df.ta.rsi(length=14, append=True)
    print("Indicadores calculados.")
    return df

def check_rules(latest_data: pd.Series) -> dict:
  
    regras = {}

    # Tendência (Preço > MME 20)
    regras["Preço > MME 20"] = latest_data['close'] > latest_data['EMA_20']

    # Contexto (MME 20 > MME 50)
    regras["MME 20 > MME 50"] = latest_data['EMA_20'] > latest_data['EMA_50']

    # Momentum (RSI > 50)
    regras["RSI > 50"] = latest_data['RSI_14'] > 50

    # Price Action (Último candle foi positivo?)
    regras["Candle Positivo"] = latest_data['close'] > latest_data['open']

    return regras