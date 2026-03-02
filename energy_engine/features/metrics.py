import numpy as np

def preditive_metrics(energy_col, fatores, n=5, verbose=True):
    """Calcula métricas preditivas para uma coluna de energia."""
    fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
    energias_antes = []
    for idx in fatores.index[n:]:
        if fatores.loc[idx, 'transicao'] == 1:
            energias_antes.append(fatores.loc[idx-n:idx-1, energy_col].mean())
    energia_dia_troca = fatores.loc[fatores['transicao']==1, energy_col].mean()
    energia_geral = fatores[energy_col].mean()
    top20 = fatores[energy_col] >= fatores[energy_col].quantile(0.8)
    prob_troca_top20 = fatores.loc[top20, 'transicao'].mean()*100
    prob_troca_geral = fatores['transicao'].mean()*100
    if verbose:
        print(f"\n--- Métricas preditivas para {energy_col} ---")
        print(f"Energia média {n} dias antes da troca: {np.nanmean(energias_antes):.4f}")
        print(f"Energia média no dia da troca: {energia_dia_troca:.4f}")
        print(f"Energia média geral: {energia_geral:.4f}")
        print(f"Probabilidade de troca (top 20% energia): {prob_troca_top20:.2f}%")
        print(f"Probabilidade de troca (geral): {prob_troca_geral:.2f}%")
    return {
        'energia_antes': np.nanmean(energias_antes),
        'energia_dia_troca': energia_dia_troca,
        'energia_geral': energia_geral,
        'prob_top20': prob_troca_top20,
        'prob_geral': prob_troca_geral
    }