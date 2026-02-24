import pandas as pd
import numpy as np

# Caminho do arquivo de resultados
df = pd.read_csv('co-piloto-quant/docs/validacao_pei/validacao_pei.csv')

# 1. Top 20% PEI → alpha futuro?
pei = df[df['modelo'] == 'pei_puro']
passou_1 = (pei['alpha_top'] > pei['alpha_geral']).all() and (pei['alpha_top'] > 0).all()

# 2. Energy alta + PEI alto → alpha melhora?
energy = df[df['modelo'] == 'energy_puro']
energy_pei = df[df['modelo'] == 'energy_pei']
passou_2 = (energy_pei['alpha_top'] > energy['alpha_top']).all()

# 3. PEI alto reduz drawdown?
passou_3 = (pei['max_drawdown'] > energy['max_drawdown']).all()  # menos negativo = melhor

# 4. PEI alto melhora consistência entre ativos?
std_pei = pei.groupby('ativo')['alpha_top'].mean().std()
std_energy = energy.groupby('ativo')['alpha_top'].mean().std()
passou_4 = std_pei < std_energy

# Resultado final
resultados = [passou_1, passou_2, passou_3, passou_4]
print(f"Resultados dos testes: {resultados} (True = passou)")
if sum(resultados) >= 2:
    print("Teoria APROVADA (passou em pelo menos 2 de 4)")
else:
    print("Matamos a teoria (não passou em pelo menos 2 de 4)")
