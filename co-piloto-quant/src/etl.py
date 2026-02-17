"""
Módulo ETL: funções para ingestão, limpeza e transformação de dados.
"""
import pandas as pd
from pathlib import Path

def load_parquet(path):
    return pd.read_parquet(path)

def save_parquet(df, path):
    df.to_parquet(path)

# Adicione aqui funções de ETL específicas do seu projeto
