"""
Script: build_market_data_for_hmm.py
Gera um dataset consolidado com as features necessárias para o pipeline HMM a partir de um arquivo enriched.parquet.
"""
import pandas as pd
import numpy as np

def realized_volatility(close, window=21):
    return close.pct_change().rolling(window).std() * np.sqrt(window)

def volatility_of_volatility(vol, window=21):
    return vol.rolling(window).std()

def rolling_trend_strength(close, window=21):
    returns = close.pct_change()
    trend = returns.rolling(window).mean()
    noise = returns.rolling(window).std()
    return np.abs(trend / noise)

def drift_t_stat(close, window=21):
    returns = close.pct_change()
    mean = returns.rolling(window).mean()
    std = returns.rolling(window).std()
    n = window
    return mean / (std / np.sqrt(n))

def efficiency_ratio(close, window=21):
    change = close.diff(window).abs()
    volatility = close.diff().abs().rolling(window).sum()
    return change / volatility

def main():
    # Escolha o ativo desejado
    input_path = 'src/co_piloto_quant/data/features/VALE3_SA_enriched.parquet'
    output_path = 'src/co_piloto_quant/data/processed/market_data.parquet'
    df = pd.read_parquet(input_path)
    
    # Calcula as features
    df['realized_volatility'] = realized_volatility(df['close'])
    df['volatility_of_volatility'] = volatility_of_volatility(df['realized_volatility'])
    df['rolling_trend_strength'] = rolling_trend_strength(df['close'])
    df['drift_t_stat'] = drift_t_stat(df['close'])
    df['efficiency_ratio'] = efficiency_ratio(df['close'])
    # Adaptações para colunas já existentes
    df['hurst'] = df['hurst_72_returns'] if 'hurst_72_returns' in df.columns else np.nan
    df['market_entropy'] = df['entropy_20'] if 'entropy_20' in df.columns else np.nan
    df['returns'] = df['close'].pct_change()
    # Preencher NaNs das features calculadas com o valor mais próximo (forward fill, depois backward fill)
    for col in ['realized_volatility','volatility_of_volatility','rolling_trend_strength','drift_t_stat','efficiency_ratio','hurst','market_entropy','returns']:
        df[col] = df[col].ffill().bfill()
    # Seleciona apenas as colunas necessárias
    features = [
        'realized_volatility',
        'volatility_of_volatility',
        'rolling_trend_strength',
        'drift_t_stat',
        'efficiency_ratio',
        'hurst',
        'market_entropy',
        'returns',
        'close',
        'volume',
    ]
    df_out = df[features]
    print(df_out.isna().sum())
    df_out.to_parquet(output_path)
    print(f'Dataset salvo em {output_path} com shape {df_out.shape}')

if __name__ == '__main__':
    main()
