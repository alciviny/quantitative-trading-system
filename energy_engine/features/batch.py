import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from energy_engine.utils.rolling import rolling_zscore, robust_zscore
from energy_engine.features.metrics import preditive_metrics
from energy_engine.features.energy import calcular_energia_estrutural, calcular_entropia_centroides, calcular_energia_v4

def processar_batch(factors_dir, results_dir, plot=True):
    files = glob.glob(os.path.join(factors_dir, 'structural_factors_*.csv'))
    ativos = [os.path.basename(f).replace('structural_factors_','').replace('.csv','') for f in files]
    resultados = []
    for ativo, path in zip(ativos, files):
        try:
            fatores = pd.read_csv(path, index_col=0)
            fatores = calcular_energia_estrutural(fatores)
            fatores = calcular_entropia_centroides(fatores)
            fatores = calcular_energia_v4(fatores)
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
            cols = [
                'compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll',
                'fatores_entropy','energia_v3','energia_v3_roll','energia_v4','energia_v4_roll','regime_rolling'
            ]
            export_cols = [col for col in cols if col in fatores.columns]
            fatores[export_cols].to_csv(os.path.join(results_dir, f'structural_energy_{ativo}.csv'))
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
        except Exception as e:
            print(f'Erro ao processar {ativo}: {e}')
    return resultados
