import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ativos = ['ITUB4.SA', 'VALE3.SA', 'PETR4.SA']
resultados = []

for ativo in ativos:
    FACTORS_PATH = f'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_{ativo}.csv'
    try:
        fatores = pd.read_csv(FACTORS_PATH, index_col=0)
    except Exception as e:
        print(f'Erro ao carregar {ativo}: {e}')
        continue

    # Parâmetros
    window_compressao = 21
    window_instab = 21
    window_zscore_robusto = 60
    window_entropy = 21
    window_v2 = 21
    window_v3 = 21

    # Compressão
    fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)
    regime = fatores['regime_rolling'].fillna(method='ffill')
    fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
    fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()

    def rolling_zscore(series, window):
        mean = series.rolling(window).mean()
        std = series.rolling(window).std()
        z = (series - mean) / (std + 1e-8)
        return z

    fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
    fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
    fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']

    # Entropia/dispersão dos fatores
    fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)

    # Energia v0.2
    fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
    regimes = fatores['regime_rolling'].fillna(method='ffill')
    centroides = fatores_v.groupby(regimes).transform('mean')
    fatores_v = fatores_v.loc[centroides.index]
    fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
    fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()

    # Energia v0.3
    fatores['energia_v3'] = (
        fatores['energia_estrutural'] +
        fatores['energia_v2'] +
        fatores['fatores_entropy']
    )
    fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()

    # Métricas preditivas
    fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
    def preditive_metrics(energy_col, fatores, n=5):
        energias_antes = []
        for idx in fatores.index[n:]:
            if fatores.loc[idx, 'transicao'] == 1:
                energias_antes.append(fatores.loc[idx-n:idx-1, energy_col].mean())
        energia_dia_troca = fatores.loc[fatores['transicao']==1, energy_col].mean()
        energia_geral = fatores[energy_col].mean()
        top20 = fatores[energy_col] >= fatores[energy_col].quantile(0.8)
        prob_troca_top20 = fatores.loc[top20, 'transicao'].mean()*100
        prob_troca_geral = fatores['transicao'].mean()*100
        return {
            'energia_antes': np.nanmean(energias_antes),
            'energia_dia_troca': energia_dia_troca,
            'energia_geral': energia_geral,
            'prob_top20': prob_troca_top20,
            'prob_geral': prob_troca_geral
        }

    met_v1 = preditive_metrics('energia_estrutural', fatores)
    met_v2 = preditive_metrics('energia_v2_roll', fatores)
    met_v3 = preditive_metrics('energia_v3_roll', fatores)

    resultados.append({
        'ativo': ativo,
        'v0.1': met_v1,
        'v0.2': met_v2,
        'v0.3': met_v3
    })

    # Gráfico comparativo
    plt.figure(figsize=(12,6))
    fatores['energia_estrutural'].plot(label='Energia v0.1')
    fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
    fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
    plt.title(f'Comparativo Energias — {ativo}')
    plt.legend()
    plt.grid(True)
    plt.savefig(f'co-piloto-quant/src/co_piloto_quant/data/results/energy_comparative_{ativo}.png')
    plt.close()

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
print('Relatório comparativo salvo em energy_comparative_report.csv')
print(df_report)
