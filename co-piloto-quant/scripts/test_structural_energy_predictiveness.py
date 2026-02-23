import pandas as pd
import numpy as np

# Caminhos dos arquivos
ENERGY_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_PETR4.SA.csv'
FACTORS_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_PETR4.SA.csv'

# Carregar dados
energy = pd.read_csv(ENERGY_PATH, index_col=0)
factors = pd.read_csv(FACTORS_PATH, index_col=0)

# Garantir alinhamento dos índices
energy = energy.loc[factors.index]
factors = factors.loc[energy.index]

# 1️⃣ Energia no exato dia da troca
regime = factors['regime_rolling'].fillna(method='ffill')
energy['transicao'] = regime.diff().ne(0).astype(int)
energia_troca = energy.loc[energy['transicao'] == 1, 'energia_estrutural']
energia_media_troca = energia_troca.mean()
energia_media_geral = energy['energia_estrutural'].mean()
print(f"Energia média no dia da troca: {energia_media_troca:.4f}")
print(f"Energia média geral: {energia_media_geral:.4f}")
if energia_media_troca > energia_media_geral:
    print("Energia é reativa (sobe no dia da troca)")
else:
    print("Energia não antecipa nem reage claramente no dia da troca")

# 2️⃣ Top 20% energia: probabilidade de troca futura
q80 = energy['energia_estrutural'].quantile(0.8)
top20 = energy['energia_estrutural'] >= q80
# Troca nos próximos N dias (ex: 5 dias)
N = 5
energy['troca_futura'] = energy['transicao'].shift(-N).fillna(0)
prob_troca_top20 = energy.loc[top20, 'troca_futura'].mean()
prob_troca_geral = energy['troca_futura'].mean()
print(f"Probabilidade de troca futura (top 20% energia): {prob_troca_top20:.2%}")
print(f"Probabilidade de troca futura (geral): {prob_troca_geral:.2%}")
if prob_troca_top20 > prob_troca_geral:
    print("Energia tem algum poder preditivo para trocas futuras.")
else:
    print("Energia NÃO tem poder preditivo para trocas futuras.")
