import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score

def calc_momentum(close, window=10):
    return close.pct_change(window)

def calc_volatility(close, window=10):
    return close.pct_change().rolling(window).std()

def calc_volume(df, window=10):
    if 'volume' in df.columns:
        return df['volume'].rolling(window).mean()
    return pd.Series(np.nan, index=df.index)

def filtro_composto(df, energy_col, momentum_col, vol_col, quantil, momentum_thresh=0, vol_thresh=None):
    q = df[energy_col].quantile(quantil)
    filtro_energy = (df[energy_col] >= q)
    filtro_mom = df[momentum_col] > momentum_thresh
    if vol_thresh is not None:
        filtro_vol = df[vol_col] < vol_thresh
    else:
        filtro_vol = pd.Series(True, index=df.index)
    return filtro_energy & filtro_mom & filtro_vol

def calc_metrics(df, energy_col, regime_col, ret_col, sinal, horizonte):
    regime = df[regime_col].diff().ne(0).astype(int)
    regime = regime.shift(-horizonte).fillna(0).astype(int)
    try:
        auc = roc_auc_score(regime, df[energy_col].fillna(0))
    except Exception:
        auc = np.nan
    precision = precision_score(regime, sinal, zero_division=0)
    recall = recall_score(regime, sinal, zero_division=0)
    f1 = f1_score(regime, sinal, zero_division=0)
    alpha_top = df.loc[sinal, ret_col].mean()
    alpha_geral = df[ret_col].mean()
    return auc, precision, recall, f1, alpha_top, alpha_geral
