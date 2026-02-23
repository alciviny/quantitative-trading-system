import os
import glob
import pandas as pd
import numpy as np

def rolling_zscore(series, window):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    z = (series - mean) / (std + 1e-8)
    return z

def calc_alpha_metrics(fatores, energy_col, ret_col, n=5):
    fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
    top20 = fatores[energy_col] >= fatores[energy_col].quantile(0.8)
    alpha_top20 = fatores.loc[top20, ret_col].mean()
    alpha_geral = fatores[ret_col].mean()
    return {
        'alpha_top20': alpha_top20,
        'alpha_geral': alpha_geral
    }

# Diretório dos fatores estruturais
factors_dir = 'co-piloto-quant/src/co_piloto_quant/data/results'
files = glob.glob(os.path.join(factors_dir, 'structural_factors_*.csv'))
ativos = [os.path.basename(f).replace('structural_factors_','').replace('.csv','') for f in files]

resultados = []
for ativo, path in zip(ativos, files):
    try:
        fatores = pd.read_csv(path, index_col=0)
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
        # Retorno futuro (ex: 10 dias)
        if 'close' in fatores.columns:
            fatores['ret_futuro_10'] = fatores['close'].pct_change(10).shift(-10)
        elif 'ret_futuro_10' not in fatores.columns:
            fatores['ret_futuro_10'] = np.nan
        # Métricas alpha
        met_v1 = calc_alpha_metrics(fatores, 'energia_estrutural', 'ret_futuro_10')
        met_v2 = calc_alpha_metrics(fatores, 'energia_v2_roll', 'ret_futuro_10')
        met_v3 = calc_alpha_metrics(fatores, 'energia_v3_roll', 'ret_futuro_10')
        resultados.append({
            'ativo': ativo,
            'v0.1': met_v1,
            'v0.2': met_v2,
            'v0.3': met_v3
        })
    except Exception as e:
        print(f'Erro ao processar {ativo}: {e}')

# Relatório final
report_rows = []
for r in resultados:
    for v, met in r.items():
        if v == 'ativo': continue
        report_rows.append({
            'ativo': r['ativo'],
            'versao': v,
            'alpha_top20': met['alpha_top20'],
            'alpha_geral': met['alpha_geral']
        })

df_report = pd.DataFrame(report_rows)
df_report.to_csv('co-piloto-quant/src/co_piloto_quant/data/results/energy_vs_alpha_report.csv', index=False)
print('Relatório energy_vs_alpha_report.csv gerado!')
print(df_report)
