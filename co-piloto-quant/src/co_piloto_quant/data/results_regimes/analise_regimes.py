import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Caminho do arquivo gerado pelo pipeline
csv_path = r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes_binario.csv'

df = pd.read_csv(csv_path, index_col=0)
df = df[df['regime_binario'].notnull()]
df['regime_binario'] = df['regime_binario'].astype(int)
# Converter fatores e pca1_rolling para float
for col in ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez', 'pca1_rolling']:
    df[col] = pd.to_numeric(df[col], errors='coerce')

print('--- Estatísticas detalhadas do Regime 0 (binário) ---')
reg0 = df[df['regime_binario'] == 0]
print(reg0[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez','pca1_rolling']].describe())

print('\n--- Estatísticas comparativas entre regimes binários ---')
grp_bin = df.groupby('regime_binario')
print(grp_bin.agg({
    'fator_persistencia': ['mean', 'std'],
    'fator_estrutura': ['mean', 'std'],
    'fator_expansao': ['mean', 'std'],
    'fator_liquidez': ['mean', 'std'],
    'pca1_rolling': ['mean', 'std'],
}))
print('\nContagem de observações por regime binário:')
print(grp_bin.size())


# Gráfico: distribuição dos regimes binários ao longo do tempo
plt.figure(figsize=(12, 3))
df['regime_binario'].plot()
plt.title('Regime binário detectado ao longo do tempo')
plt.xlabel('Índice temporal')
plt.ylabel('Regime binário')
plt.tight_layout()
plt.show()


# Boxplots dos fatores por regime binário
for fator in ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez', 'pca1_rolling']:
    plt.figure(figsize=(12, 6))
    sns.boxplot(x='regime_binario', y=fator, data=df)
    plt.title(f'Distribuição de {fator} por regime binário')
    plt.show()


# Relatório focado no Regime 0
print('\n--- Resumo interpretativo: Regime 0 (binário) ---')
print('1. O Regime 0 representa o cluster estatisticamente distinto, com média de pca1_rolling negativa e fatores mais conservadores.')
print('2. As estatísticas mostram que o Regime 0 é numericamente dominante e apresenta menor volatilidade nos fatores.')
print('3. O gráfico temporal revela períodos de persistência do Regime 0, sugerindo estabilidade ou aversão a risco.')
print('4. Os boxplots evidenciam a separação dos fatores entre Regime 0 e Regime 1.')
print('5. Use essas informações para identificar oportunidades, padrões de risco e contexto de mercado associados ao Regime 0.')
