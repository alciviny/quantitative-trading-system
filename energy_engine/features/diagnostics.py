import numpy as np
import matplotlib.pyplot as plt

def diagnostico_regimes(energy, factors, ticker='TICKER', plot=True):
    # Alinhar pelo campo 'date'
    if 'date' in energy.columns:
        energy = energy.set_index('date')
    if 'date' in factors.columns:
        factors = factors.set_index('date')
    # Interseção dos índices
    idx_comum = energy.index.intersection(factors.index)
    energy = energy.loc[idx_comum]
    factors = factors.loc[idx_comum]
    regime = factors['regime_rolling'].fillna(method='ffill')
    energy['transicao'] = regime.diff().ne(0).astype(int)
    n_transicoes = energy['transicao'].sum()
    print(f'Número de transições de regime: {int(n_transicoes)}')
    energy['regime_change'] = energy['transicao']
    energy['block'] = energy['regime_change'].cumsum()
    duracoes = energy.groupby('block').size()
    print(f'Duração média dos regimes: {duracoes.mean():.2f} dias')
    print('Distribuição das durações (em dias):')
    print(duracoes.describe())
    print('Percentis das durações:', duracoes.quantile([0.25,0.5,0.75,0.9,0.99]))
    n_micro = (duracoes == 1).sum()
    print(f'Número de micro-trocas (blocos de 1 dia): {n_micro}')
    N = 5
    energias_antes = []
    energias_no_dia = []
    energias_depois = []
    idx_list = list(energy.index)
    for i in range(N, len(energy)-N):
        idx = idx_list[i]
        if energy.loc[idx, 'transicao'] == 1:
            # médias usando posições
            energias_antes.append(energy.iloc[i-N:i, energy.columns.get_loc('energia_estrutural')].mean())
            energias_no_dia.append(energy.iloc[i, energy.columns.get_loc('energia_estrutural')])
            energias_depois.append(energy.iloc[i+1:i+1+N, energy.columns.get_loc('energia_estrutural')].mean())
    print(f'Energia média 5 dias antes da troca: {np.nanmean(energias_antes):.4f}')
    print(f'Energia média no dia da troca: {np.nanmean(energias_no_dia):.4f}')
    print(f'Energia média 5 dias depois da troca: {np.nanmean(energias_depois):.4f}')
    if plot:
        plt.figure(figsize=(8,4))
        plt.hist(duracoes, bins=30, color='skyblue', edgecolor='k')
        plt.title(f'Distribuição das durações dos regimes ({ticker})')
        plt.xlabel('Duração (dias)')
        plt.ylabel('Frequência')
        plt.tight_layout()
        plt.show()
    return {
        'n_transicoes': int(n_transicoes),
        'duracoes': duracoes,
        'n_micro': int(n_micro),
        'energias_antes': np.nanmean(energias_antes),
        'energias_no_dia': np.nanmean(energias_no_dia),
        'energias_depois': np.nanmean(energias_depois)
    }
