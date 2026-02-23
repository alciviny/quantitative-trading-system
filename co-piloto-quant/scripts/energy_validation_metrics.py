import sys
import os
import pandas as pd
import numpy as np
from sklearn.metrics import roc_auc_score, precision_score, recall_score, f1_score, roc_curve
import matplotlib.pyplot as plt


import argparse

# Argumentos de linha de comando
parser = argparse.ArgumentParser(description='Validação quantitativa dos sinais de energy.')

parser.add_argument('--ativos', nargs='+', default=['BPAC11.SA', 'ELET6.SA', 'AXIA6.SA'], help='Lista de ativos')
parser.add_argument('--versoes', nargs='+', default=['v0.1', 'v0.2', 'v0.3'], help='Versões de energy')
parser.add_argument('--quantil', type=float, default=0.8, help='Quantil para sinal de energy (ex: 0.8 para top 20%)')
parser.add_argument('--horizonte', type=int, default=1, help='Horizonte de previsão (dias à frente para troca de regime)')
parser.add_argument('--output', default='co-piloto-quant/docs/validacao_energy/metricas_quantitativas.csv', help='Arquivo de saída das métricas')
parser.add_argument('--plots', default='co-piloto-quant/docs/validacao_energy/', help='Diretório para salvar gráficos')
parser.add_argument('--janela', type=int, default=None, help='Tamanho da janela rolling para recalcular energias (opcional)')
args = parser.parse_args()

ATIVOS = args.ativos
VERSOES = args.versoes
QUANTIL = args.quantil
HORIZONTE = args.horizonte
RESULTS_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/'
OUTPUT_METRICAS = args.output
OUTPUT_PLOTS = args.plots

# Função para calcular métricas

def calc_metrics(df, energy_col, regime_col, ret_col, ativo, versao, quantil=0.8, horizonte=1):
    # Filtrar NaNs
    df = df[[energy_col, regime_col, ret_col]].dropna()
    # Sinal: top quantil de energy
    q = df[energy_col].quantile(quantil)
    sinal = (df[energy_col] >= q).astype(int)
    # Troca de regime no horizonte desejado
    regime = df[regime_col].diff().ne(0).astype(int)
    regime = regime.shift(-horizonte).fillna(0).astype(int)
    # Métricas de classificação
    try:
        auc = roc_auc_score(regime, df[energy_col].fillna(0))
    except Exception:
        auc = np.nan
    precision = precision_score(regime, sinal, zero_division=0)
    recall = recall_score(regime, sinal, zero_division=0)
    f1 = f1_score(regime, sinal, zero_division=0)
    # Alpha futuro
    alpha_top = df.loc[sinal == 1, ret_col].mean()
    alpha_geral = df[ret_col].mean()
    # Plots
    fpr, tpr, _ = roc_curve(regime, df[energy_col].fillna(0))
    plt.figure(figsize=(6,4))
    plt.plot(fpr, tpr, label=f'AUC={auc:.2f}')
    plt.plot([0,1],[0,1],'--',color='gray')
    plt.title(f'ROC - {ativo} {versao} (h={horizonte}, q={quantil})')
    plt.xlabel('FPR')
    plt.ylabel('TPR')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PLOTS, f'roc_{ativo}_{versao}_h{horizonte}_q{int(quantil*100)}.png'))
    plt.close()
    # Alpha distrib
    plt.figure(figsize=(6,4))
    df[ret_col].hist(bins=50, alpha=0.5, label='Alpha geral')
    df.loc[sinal==1, ret_col].hist(bins=30, alpha=0.7, label=f'Alpha top{int((1-quantil)*100)}%')
    plt.title(f'Alpha futuro - {ativo} {versao} (h={horizonte}, q={quantil})')
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_PLOTS, f'alpha_{ativo}_{versao}_h{horizonte}_q{int(quantil*100)}.png'))
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

# Execução principal
metricas = []
for ativo in ATIVOS:
    for versao in VERSOES:
        path = os.path.join(RESULTS_PATH, f'structural_energy_{ativo}.csv')
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path)
        # Se --janela for informado, recalcula as colunas de energia com a nova janela
        if args.janela is not None:
            window = args.janela
            # Recalcula energia_estrutural
            if 'compressao' in df.columns and 'instabilidade' in df.columns:
                def rolling_zscore(series, window):
                    mean = series.rolling(window).mean()
                    std = series.rolling(window).std()
                    z = (series - mean) / (std + 1e-8)
                    return z
                df['compressao_z'] = rolling_zscore(df['compressao'], window)
                df['instabilidade_z'] = rolling_zscore(df['instabilidade'], window)
                df['energia_estrutural'] = df['compressao_z'] + df['instabilidade_z']
            # Recalcula energia_v2_roll
            if 'energia_v2' in df.columns:
                df['energia_v2_roll'] = df['energia_v2'].rolling(window).mean()
            # Recalcula energia_v3_roll
            if 'energia_v3' in df.columns:
                df['energia_v3_roll'] = df['energia_v3'].rolling(window).mean()
        # Mapeamento correto das colunas de energia
        if versao == 'v0.1':
            energy_col = 'energia_estrutural'
        elif versao == 'v0.2':
            energy_col = 'energia_v2_roll'
        elif versao == 'v0.3':
            energy_col = 'energia_v3_roll'
        else:
            energy_col = f'energia_{versao}'
        if energy_col not in df.columns or 'ret_futuro_10' not in df.columns or 'regime_rolling' not in df.columns:
            continue
        m = calc_metrics(df, energy_col, 'regime_rolling', 'ret_futuro_10', ativo, versao, quantil=QUANTIL, horizonte=HORIZONTE)
        metricas.append(m)

# Salvar métricas
pd.DataFrame(metricas).to_csv(OUTPUT_METRICAS, index=False)
print(f'Métricas salvas em {OUTPUT_METRICAS}')
