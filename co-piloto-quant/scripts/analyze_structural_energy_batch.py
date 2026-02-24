from scipy.stats import median_abs_deviation

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime

# Logging simples
# Logging simples
def log(msg):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

# Z-score robusto
def robust_zscore(series, window):
    median = series.rolling(window).median()
    mad = series.rolling(window).apply(median_abs_deviation)
    return (series - median) / (mad + 1e-8)

def rolling_zscore(series, window):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    z = (series - mean) / (std + 1e-8)
    return z

def preditive_metrics(energy_col, fatores, n=5):
    fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
    energias_antes = []
    for i in range(n, len(fatores)):
        if fatores.iloc[i]['transicao'] == 1:
            energias_antes.append(fatores.iloc[i-n:i][energy_col].mean())
    energia_dia_troca = fatores.loc[fatores['transicao']==1, energy_col].mean()
    energia_geral = fatores[energy_col].mean()
    top20 = fatores[energy_col] >= fatores[energy_col].quantile(0.8)
    prob_troca_top20 = fatores.loc[top20, 'transicao'].mean()*100
    prob_geral = fatores['transicao'].mean()*100  # Mantido para retorno, pois é usado no dict
    return {
        'energia_antes': np.nanmean(energias_antes),
        'energia_dia_troca': energia_dia_troca,
        'energia_geral': energia_geral,
        'prob_top20': prob_troca_top20,
        'prob_geral': prob_geral
    }

# Diretório dos fatores estruturais

factors_dir = 'co-piloto-quant/src/co_piloto_quant/data/results'
files = glob.glob(os.path.join(factors_dir, 'structural_factors_*.csv'))
ativos = [os.path.basename(f).replace('structural_factors_','').replace('.csv','') for f in files]
log(f'Encontrados {len(files)} arquivos de fatores estruturais.')

resultados = []
for ativo, path in zip(ativos, files):
    try:
        log(f'Processando ativo: {ativo}')
        fatores = pd.read_csv(path, index_col=0)
        log('Arquivo de fatores lido com sucesso.')
        # Parâmetros
        window_compressao = 21
        window_instab = 21
        window_zscore_robusto = 60
        window_entropy = 21
        window_v2 = 21
        window_v3 = 21
        # Energia v0.1
        fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)
        regime = fatores['regime_rolling'].fillna(method='ffill')
        fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
        fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()
        fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
        fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
        fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']
        log('Energia v0.1 calculada.')
        # Entropia/dispersão dos fatores
        fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)
        # Energia v0.2
        fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
        regimes = fatores['regime_rolling'].fillna(method='ffill')
        centroides = fatores_v.groupby(regimes).transform('mean')
        fatores_v = fatores_v.loc[centroides.index]
        fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
        fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()
        log('Energia v0.2 calculada.')
        # Energia v0.3
        fatores['energia_v3'] = (
            fatores['energia_estrutural'] +
            fatores['energia_v2'] +
            fatores['fatores_entropy']
        )
        fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()
        # Energia v0.4 — combinação não-linear e robusta
        fatores['energia_v4'] = (
            robust_zscore(fatores['energia_estrutural'], window_zscore_robusto) *
            robust_zscore(fatores['energia_v2'], window_zscore_robusto) +
            robust_zscore(fatores['fatores_entropy'], window_zscore_robusto)
        )
        fatores['energia_v4_roll'] = fatores['energia_v4'].rolling(window_v3).mean()
        log('Energia v0.4 calculada.')
        log('Energia v0.3 calculada.')
        # Métricas preditivas
        met_v1 = preditive_metrics('energia_estrutural', fatores)
        met_v2 = preditive_metrics('energia_v2_roll', fatores)
        met_v3 = preditive_metrics('energia_v3_roll', fatores)
        resultados.append({
            'ativo': ativo,
            'v0.1': met_v1,
            'v0.2': met_v2,
            'v0.3': met_v3
        })
        # Salvar CSV de energia para cada ativo
        energy_cols = [
            'date' if 'date' in fatores.columns else None,
            'compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll','fatores_entropy','energia_v3','energia_v3_roll','energia_v4','energia_v4_roll','regime_rolling','ret_futuro_10','close'
        ]
        # Filtra apenas colunas existentes
        energy_cols = [col for col in energy_cols if col and col in fatores.columns]
        fatores[energy_cols].to_csv(f'co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_{ativo}.csv', index=False)
        log(f'Arquivo de energia salvo para {ativo}.')
        # Gráfico comparativo
        plt.figure(figsize=(12,6))
        fatores['energia_estrutural'].plot(label='Energia v0.1')
        fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
        fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
        fatores['energia_v4_roll'].plot(label='Energia v0.4 (robusta, não-linear)', linestyle='--')
        plt.title(f'Comparativo Energias — {ativo}')
        plt.legend()
        plt.grid(True)
        plt.savefig(f'co-piloto-quant/src/co_piloto_quant/data/results/energy_comparative_{ativo}.png')
        plt.close()
        log(f'Gráfico comparativo salvo para {ativo}.')
    except Exception as e:
        log(f'Erro ao processar {ativo}: {e}')

# Relatório final
report_rows = []
for r in resultados:
    for v, met in r.items():
        if v == 'ativo': continue
        report_rows.append({
            'ativo': r['ativo'],
            'versao': v,
            'energia_antes': met['energia_antes'],
            'energia_dia_troca': met['energia_dia_troca'],
            'energia_geral': met['energia_geral'],
            'prob_top20': met['prob_top20'],
            'prob_geral': met['prob_geral']
        })

df_report = pd.DataFrame(report_rows)
df_report.to_csv('co-piloto-quant/src/co_piloto_quant/data/results/energy_comparative_report.csv', index=False)
log('Relatório comparativo salvo em energy_comparative_report.csv')
log(df_report)
