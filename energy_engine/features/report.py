import os
import pandas as pd
import matplotlib.pyplot as plt
from energy_engine.utils.rolling import rolling_zscore
from energy_engine.features.metrics import preditive_metrics

def gerar_relatorio_comparativo(ativos, factors_dir, results_dir, plot=True):
    resultados = []
    for ativo in ativos:
        FACTORS_PATH = os.path.join(factors_dir, f'structural_factors_{ativo}.csv')
        try:
            fatores = pd.read_csv(FACTORS_PATH, index_col=0)
        except Exception as e:
            print(f'Erro ao carregar {ativo}: {e}')
            continue
        # Cálculos principais (pode ser ajustado para usar funções já modularizadas)
        window_compressao = 21
        window_instab = 21
        window_zscore_robusto = 60
        window_entropy = 21
        window_v2 = 21
        window_v3 = 21
        fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)
        regime = fatores['regime_rolling'].ffill()
        fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
        fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()
        fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
        fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
        fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']
        fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)
        fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
        regimes = fatores['regime_rolling'].ffill()
        centroides = fatores_v.groupby(regimes).transform('mean')
        fatores_v = fatores_v.loc[centroides.index]
        fatores['energia_v2'] = ((fatores_v - centroides)**2).sum(axis=1)**0.5
        fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()
        fatores['energia_v3'] = (
            fatores['energia_estrutural'] +
            fatores['energia_v2'] +
            fatores['fatores_entropy']
        )
        fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()
        fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
        met_v1 = preditive_metrics('energia_estrutural', fatores)
        met_v2 = preditive_metrics('energia_v2_roll', fatores)
        met_v3 = preditive_metrics('energia_v3_roll', fatores)
        met_v4 = preditive_metrics('energia_v4_roll', fatores) if 'energia_v4_roll' in fatores.columns else None
        resultados.append({
            'ativo': ativo,
            'v0.1': met_v1,
            'v0.2': met_v2,
            'v0.3': met_v3,
            'v0.4': met_v4
        })
        if plot:
            plt.figure(figsize=(12,6))
            fatores['energia_estrutural'].plot(label='Energia v0.1')
            fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
            fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
            if 'energia_v4_roll' in fatores.columns:
                fatores['energia_v4_roll'].plot(label='Energia v0.4 (robusta, não-linear)', linestyle='--')
            plt.title(f'Comparativo Energias — {ativo}')
            plt.legend()
            plt.grid(True)
            plt.savefig(os.path.join(results_dir, f'energy_comparative_{ativo}.png'))
            plt.close()
    return resultados
