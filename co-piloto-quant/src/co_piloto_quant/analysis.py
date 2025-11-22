import pandas as pd
import pandas_ta as ta

from co_piloto_quant.config import PROCESSED_DATA_PATH
from co_piloto_quant.indicators.williams_ad import williams_ad

def load_processed_data(ticker: str) -> pd.DataFrame:
  
    file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
    if not file_path.exists():
        print(f"Arquivo de dados processados não encontrado para {ticker} em {file_path}")
        return pd.DataFrame()
    
    print(f"Carregando dados processados de {file_path}...")
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df

def calculate_indicators(df: pd.DataFrame, rsi_period: int = 14) -> pd.DataFrame:
  
    print(f"Calculando indicadores (MME 20, MME 50, RSI {rsi_period})...")
    df.ta.ema(length=20, append=True)
    df.ta.ema(length=50, append=True)
    
 
    rsi_series = df.ta.rsi(length=rsi_period)
    df['RSI'] = rsi_series

    print(f"Calculando Williams A/D (bruto)...")
    df['Williams_AD'] = williams_ad(df)
    
    print("Indicadores calculados.")
    return df

def check_rules(latest_data: pd.Series) -> dict:
  
    regras = {}


    regras["Preço > MME 20"] = latest_data['close'] > latest_data['EMA_20']

    
    regras["MME 20 > MME 50"] = latest_data['EMA_20'] > latest_data['EMA_50']

 
    regras["RSI > 50"] = latest_data['RSI'] > 50

  
    regras["Candle Positivo"] = latest_data['close'] > latest_data['open']

    return regras
    
def main(tickers: list[str]):
 
    print("Iniciando análise...")
    full_results = {}

    for ticker in tickers:
        print(f"\n--- Analisando {ticker} ---")
    
        data = load_processed_data(ticker)
        
        if data.empty:
            continue

       
        data_with_indicators = calculate_indicators(data)

       
        latest_data = data_with_indicators.iloc[-1]

      
        results = check_rules(latest_data)
        full_results[ticker] = results

   
    print("\n--- Resumo da Análise ---")
    for ticker, results in full_results.items():
        print(f"\nAtivo: {ticker}")
        for rule, result in results.items():
            status = "OK" if result else "NEGADO"
            print(f"  {status} {rule}")

if __name__ == '__main__':
    target_tickers = ['PETR4.SA', 'VALE3.SA'] 
    main(target_tickers)