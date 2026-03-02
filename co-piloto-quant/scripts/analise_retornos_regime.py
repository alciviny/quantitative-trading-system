import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal

# Carregar o CSV
csv_path = r'co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes.csv'
df = pd.read_csv(csv_path, header=None)

 # Ajustar nomes das colunas conforme o CSV real
colunas = ['idx','fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez','regime_rolling','pca1_rolling']
df.columns = colunas

# Filtrar linhas com regime e retorno futuro válidos
filtros = (~df['regime_rolling'].isna()) & (~df['pca1_rolling'].isna())
df = df[filtros].copy()

# Converter para numérico (ignorar erros)
df['regime_rolling'] = pd.to_numeric(df['regime_rolling'], errors='coerce')
df['pca1_rolling'] = pd.to_numeric(df['pca1_rolling'], errors='coerce')
df = df.dropna(subset=['regime_rolling','pca1_rolling'])
df['regime_rolling'] = df['regime_rolling'].astype(int)

# Estatísticas descritivas
stats = df.groupby('regime_rolling')['pca1_rolling'].describe()
print('Estatísticas descritivas por regime:')
print(stats)

# Boxplot
plt.figure(figsize=(10,6))
sns.boxplot(x='regime_rolling', y='pca1_rolling', data=df)
plt.title('Distribuição do Retorno Futuro (PCA1) por Regime')
plt.savefig('boxplot_retornos_regime.png')
plt.close()

# Post-hoc de Dunn
import scikit_posthocs as sp
print('\nPost-hoc de Dunn entre regimes:')
dunn = sp.posthoc_dunn(df, val_col='pca1_rolling', group_col='regime_rolling', p_adjust='bonferroni')
print(dunn)

# Histograma
plt.figure(figsize=(10,6))
sns.histplot(data=df, x='pca1_rolling', hue='regime_rolling', kde=True, bins=40)
plt.title('Histograma do Retorno Futuro (PCA1) por Regime')
plt.savefig('hist_retornos_regime.png')
plt.close()

# Teste estatístico
regimes = [df[df['regime_rolling']==r]['pca1_rolling'].values for r in sorted(df['regime_rolling'].unique())]
stat, p = kruskal(*regimes)
print(f'Teste Kruskal-Wallis: stat={stat:.3f}, p={p:.4f}')
if p < 0.05:
    print('Diferença estatística significativa entre regimes!')
else:
    print('NÃO há diferença estatística significativa entre regimes.')

# Post-hoc de Dunn
import scikit_posthocs as sp
print('\nPost-hoc de Dunn entre regimes:')
dunn = sp.posthoc_dunn(df, val_col='pca1_rolling', group_col='regime_rolling', p_adjust='bonferroni')
print(dunn)
