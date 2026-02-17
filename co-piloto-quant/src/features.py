"""
Módulo de features: cálculo e engenharia de variáveis.
"""
import pandas as pd

def add_features(df):
    # Exemplo: adicionar volatilidade realizada
    df['realized_volatility'] = df['returns'].rolling(21).std() * (252**0.5)
    # Adicione outros cálculos de features aqui
    return df
