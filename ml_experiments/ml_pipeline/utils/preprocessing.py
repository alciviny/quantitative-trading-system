import pandas as pd
import numpy as np

def generate_signal(df, n_dias_futuro=5, threshold_compra=0.05, threshold_venda=-0.10):
    """
    Gera coluna SIGNAL baseada no retorno futuro.
    """
    df = df.copy()
    df['retorno_futuro'] = (df['close'].shift(-n_dias_futuro) - df['close']) / df['close']
    novo_signal = []
    for ret in df['retorno_futuro']:
        if pd.isna(ret):
            novo_signal.append('HOLD')
        elif ret > threshold_compra:
            novo_signal.append('BUY')
        elif ret < threshold_venda:
            novo_signal.append('SELL')
        else:
            novo_signal.append('HOLD')
    df['SIGNAL'] = novo_signal
    return df

def select_features(df, exclude=None):
    if exclude is None:
        exclude = ['SIGNAL', 'retorno_futuro', 'open', 'close', 'high', 'low', 'wad']
    features = [col for col in df.select_dtypes(include=[float, int]).columns if col not in exclude]
    return features
