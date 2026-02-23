import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ENERGY_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_PETR4.SA.csv'
FACTORS_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_PETR4.SA.csv'

energy = pd.read_csv(ENERGY_PATH, index_col=0)
factors = pd.read_csv(FACTORS_PATH, index_col=0)

# Alinhar índices
energy = energy.loc[factors.index]
factors = factors.loc[energy.index]

# Transições de regime
regime = factors['regime_rolling'].fillna(method='ffill')
energy['transicao'] = regime.diff().ne(0).astype(int)

# 1. Quantas transições existem?
n_transicoes = energy['transicao'].sum()
print(f'Número de transições de regime: {int(n_transicoes)}')

# 2. Duração dos regimes (tamanho dos blocos)
energy['regime_change'] = energy['transicao']
energy['block'] = energy['regime_change'].cumsum()
duracoes = energy.groupby('block').size()
print(f'Duração média dos regimes: {duracoes.mean():.2f} dias')
print('Distribuição das durações (em dias):')
print(duracoes.describe())
print('Percentis das durações:', duracoes.quantile([0.25,0.5,0.75,0.9,0.99]))

# 3. Trocas abruptas ou graduais?
# (Aqui, abrupta = mudança de regime de um dia para o outro)
# Se houver blocos de duração 1, são micro-trocas
n_micro = (duracoes == 1).sum()
print(f'Número de micro-trocas (blocos de 1 dia): {n_micro}')

# 4. Energia antes, no dia e depois da troca
N = 5
energias_antes = []
energias_no_dia = []
energias_depois = []
for idx in energy.index[N:-N]:
    if energy.loc[idx, 'transicao'] == 1:
        energias_antes.append(energy.loc[idx-N:idx-1, 'energia_estrutural'].mean())
        energias_no_dia.append(energy.loc[idx, 'energia_estrutural'])
        energias_depois.append(energy.loc[idx+1:idx+N, 'energia_estrutural'].mean())
print(f'Energia média 5 dias antes da troca: {np.nanmean(energias_antes):.4f}')
print(f'Energia média no dia da troca: {np.nanmean(energias_no_dia):.4f}')
print(f'Energia média 5 dias depois da troca: {np.nanmean(energias_depois):.4f}')

# 5. Visualização: histograma das durações
plt.figure(figsize=(8,4))
plt.hist(duracoes, bins=30, color='skyblue', edgecolor='k')
plt.title('Distribuição das durações dos regimes (PETR4)')
plt.xlabel('Duração (dias)')
plt.ylabel('Frequência')
plt.tight_layout()
plt.show()
