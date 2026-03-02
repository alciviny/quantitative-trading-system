import numpy as np
import pandas as pd
import os
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, roc_curve
import matplotlib.pyplot as plt
from energy_engine.utils.rolling import rolling_zscore

def calc_metrics(df, energy_col, regime_col, ret_col, ativo, versao, quantil=0.8, horizonte=1, output_plots=None):
    df = df[[energy_col, regime_col, ret_col]].dropna()
    q = df[energy_col].quantile(quantil)
    sinal = (df[energy_col] >= q).astype(int)
    regime = df[regime_col].diff().ne(0).astype(int)
    regime = regime.shift(-horizonte).fillna(0).astype(int)
    try:
        auc = roc_auc_score(regime, df[energy_col].fillna(0))
    except Exception:
        auc = np.nan
    precision = precision_score(regime, sinal, zero_division=0)
    recall = recall_score(regime, sinal, zero_division=0)
    f1 = f1_score(regime, sinal, zero_division=0)
    alpha_top = df.loc[sinal == 1, ret_col].mean()
    alpha_geral = df[ret_col].mean()
    if output_plots:
        fpr, tpr, _ = roc_curve(regime, df[energy_col].fillna(0))
        plt.figure(figsize=(6,4))
        plt.plot(fpr, tpr, label=f'AUC={auc:.2f}')
        plt.plot([0,1],[0,1],'--',color='gray')
        plt.title(f'ROC - {ativo} {versao} (h={horizonte}, q={quantil})')
        plt.xlabel('FPR')
        plt.ylabel('TPR')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_plots, f'roc_{ativo}_{versao}_h{horizonte}_q{int(quantil*100)}.png'))
        plt.close()
        plt.figure(figsize=(6,4))
        df[ret_col].hist(bins=50, alpha=0.5, label='Alpha geral')
        df.loc[sinal==1, ret_col].hist(bins=30, alpha=0.7, label=f'Alpha top{int((1-quantil)*100)}%')
        plt.title(f'Alpha futuro - {ativo} {versao} (h={horizonte}, q={quantil})')
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(output_plots, f'alpha_{ativo}_{versao}_h{horizonte}_q{int(quantil*100)}.png'))
        plt.close()
    return {
        'ativo': ativo,
        'versao': versao,
        'horizonte': horizonte,
        'quantil': quantil,
        'auc': auc,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'alpha_top': alpha_top,
        'alpha_geral': alpha_geral
    }

def recalc_energies(df, window):
    if 'compressao' in df.columns and 'instabilidade' in df.columns:
        df['compressao_z'] = rolling_zscore(df['compressao'], window)
        df['instabilidade_z'] = rolling_zscore(df['instabilidade'], window)
        df['energia_estrutural'] = df['compressao_z'] + df['instabilidade_z']
    if 'energia_v2' in df.columns:
        df['energia_v2_roll'] = df['energia_v2'].rolling(window).mean()
    if 'energia_v3' in df.columns:
        df['energia_v3_roll'] = df['energia_v3'].rolling(window).mean()
    return df
