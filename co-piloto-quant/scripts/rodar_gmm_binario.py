import pandas as pd
import numpy as np
from sklearn.mixture import GaussianMixture
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import kruskal
import scikit_posthocs as sp

# Carregar dados dos fatores
csv_path = r'co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes.csv'
df = pd.read_csv(csv_path, header=None)
colunas = ['idx','fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez','regime_rolling','pca1_rolling']
df.columns = colunas

# Selecionar features para clustering (ajuste conforme necessário)

features = ['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']
# Garante que todos os dados são numéricos
df_num = df[features].apply(pd.to_numeric, errors='coerce')
mask_validos = df_num.notnull().all(axis=1)
X = df_num[mask_validos].values

# Rodar GMM com 2 componentes
gmm = GaussianMixture(n_components=2, random_state=42)
labels = gmm.fit_predict(X)

# Adicionar novo regime ao DataFrame
idx_validos = df_num[mask_validos].index
df['regime_binario'] = np.nan
for i, idx in enumerate(idx_validos):
    df.at[idx, 'regime_binario'] = labels[i]

# Análise estatística dos regimes

# Converter pca1_rolling para float e filtrar apenas valores válidos
df['pca1_rolling'] = pd.to_numeric(df['pca1_rolling'], errors='coerce')

print('Estatísticas descritivas por regime (binário):')
for regime in sorted(df['regime_binario'].dropna().unique()):
    stats = df[(df['regime_binario']==regime) & (df['pca1_rolling'].notnull())]['pca1_rolling'].describe()
    print(f'Regime {regime}:\n{stats}\n')

# Boxplot
plt.figure(figsize=(10,6))
sns.boxplot(x='regime_binario', y='pca1_rolling', data=df)
plt.title('Distribuição do Retorno Futuro (PCA1) por Regime Binário')
plt.savefig('boxplot_retornos_binario.png')
plt.close()

# Histograma
plt.figure(figsize=(10,6))
sns.histplot(data=df, x='pca1_rolling', hue='regime_binario', kde=True, bins=40)
plt.title('Histograma do Retorno Futuro (PCA1) por Regime Binário')
plt.savefig('hist_retornos_binario.png')
plt.close()

# Teste estatístico
regimes = [df[df['regime_binario']==r]['pca1_rolling'].dropna().values for r in sorted(df['regime_binario'].dropna().unique())]
stat, p = kruskal(*regimes)
print(f'Teste Kruskal-Wallis (binário): stat={stat:.3f}, p={p:.4f}')
if p < 0.05:
    print('Diferença estatística significativa entre regimes!')
else:
    print('NÃO há diferença estatística significativa entre regimes.')

# Post-hoc de Dunn
print('\nPost-hoc de Dunn entre regimes binários:')
dunn = sp.posthoc_dunn(df.dropna(subset=['regime_binario','pca1_rolling']), val_col='pca1_rolling', group_col='regime_binario', p_adjust='bonferroni')
print(dunn)

# Exporta CSV com novo regime
out_path = 'co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes_binario.csv'
df.to_csv(out_path, index=False)
print(f'Resultados exportados para {out_path}')
