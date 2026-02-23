import pandas as pd
import numpy as np
from scipy.stats import zscore
import matplotlib.pyplot as plt

# Caminho para o CSV de fatores estruturais suavizados (output do analyze_structural_factors.py)
FACTORS_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_VALE3.SA.csv'

# Parâmetros
window_compressao = 21  # dias para compressão estrutural
window_instab = 21      # dias para instabilidade recente
window_zscore = 21      # janela para zscore rolling

# 1. Carregar fatores estruturais
fatores = pd.read_csv(FACTORS_PATH, index_col=0)

# 2. Componente A — Compressão Estrutural (inverso do desvio padrão rolling do fator_expansao)
fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)

# 3. Componente B — Instabilidade Recente (média rolling das mudanças de regime)
regime = fatores['regime_rolling'].fillna(method='ffill')
fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()

# 4. Energia Estrutural v0.1 (zscore rolling dos dois componentes)
def rolling_zscore(series, window):
    mean = series.rolling(window).mean()
    std = series.rolling(window).std()
    z = (series - mean) / (std + 1e-8)
    return z

# Rolling zscore robusto (janela 60 dias)
window_zscore_robusto = 60
fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']

# 5. Visualização simples
titulo = 'Energia Estrutural v0.1 — ITUB4.SA'
plt.figure(figsize=(12,6))
fatores['energia_estrutural'].plot(label='Energia Estrutural')
plt.title(titulo)
plt.legend()
plt.grid(True)
plt.show()

# 6. Diagnóstico: energia antes das transições de regime
# Marcar pontos de transição de regime
fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)

# Energia média antes das transições (N dias antes)
N = 5
energias_antes = []
for idx in fatores.index[N:]:
    if fatores.loc[idx, 'transicao'] == 1:
        energias_antes.append(fatores.loc[idx-N:idx-1, 'energia_estrutural'].mean())
print(f'Energia média nos {N} dias antes das transições:', np.nanmean(energias_antes))
print('Energia média geral:', fatores['energia_estrutural'].mean())

# 7. Salvar resultado

# 8. Energia v0.2 — Distância ao centroide do regime
# 8b. Entropia/dispersão dos fatores (rolling std dos fatores)
window_entropy = 21
fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)

fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
regimes = fatores['regime_rolling'].fillna(method='ffill')
centroides = fatores_v.groupby(regimes).transform('mean')
# Garantir alinhamento de índices
fatores_v = fatores_v.loc[centroides.index]
fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
# Rolling mean para acumular tensão pré-evento
window_v2 = 21
fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()

# 9. Salvar resultado com ambas energias
# 14. Energia v0.3 — Combinação
window_v3 = 21
fatores['energia_v3'] = (
    fatores['energia_estrutural'] +
    fatores['energia_v2'] +
    fatores['fatores_entropy']
)
fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()


# 10. Função de métricas preditivas
def preditive_metrics(energy_col, fatores, n=5):
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
    print(f"\n--- Métricas preditivas para {energy_col} ---")
    print(f"Energia média {n} dias antes da troca: {np.nanmean(energias_antes):.4f}")
    print(f"Energia média no dia da troca: {energia_dia_troca:.4f}")
    print(f"Energia média geral: {energia_geral:.4f}")
    print(f"Probabilidade de troca (top 20% energia): {prob_troca_top20:.2f}%")
    print(f"Probabilidade de troca (geral): {prob_troca_geral:.2f}%")

# 11. Visualização comparativa
plt.figure(figsize=(12,6))
fatores['energia_estrutural'].plot(label='Energia v0.1')
fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
plt.title('Comparativo Energia Estrutural v0.1 vs v0.2 vs v0.3')
plt.legend()
plt.grid(True)
plt.show()

# 12. Salvar resultado
fatores[['compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll','fatores_entropy','energia_v3','energia_v3_roll']].to_csv('co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_PETR4.SA.csv')
print('Arquivo de energia estrutural salvo com energias v0.1, v0.2, v0.3 e rolling.')

# 13. Rodar métricas preditivas para ambas energias
preditive_metrics('energia_estrutural', fatores)
preditive_metrics('energia_v2_roll', fatores)
preditive_metrics('energia_v3_roll', fatores)
