import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA


csv_path = r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes.csv'
df = pd.read_csv(csv_path, index_col=0)

# Diagnóstico da coluna fator_expansao
exp_var = 'fator_expansao'
print('--- Estatísticas da variável fator_expansao ---')
if exp_var in df.columns:
    print(df[exp_var].describe())
    print(f'Proporção de NaNs: {df[exp_var].isna().mean():.2%}')
    plt.figure(figsize=(8, 3))
    sns.histplot(df[exp_var].dropna(), bins=50, kde=True)
    plt.title(f'Histograma de {exp_var}')
    plt.show()
else:
    print(f'{exp_var} não encontrada no arquivo.')

# Diagnóstico do PCA usando apenas fator_expansao (não faz sentido PCA com uma variável, mas mostra distribuição)
exp_data = df[[exp_var]].dropna()
if not exp_data.empty:
    print('\n--- Boxplot da variável fator_expansao ---')
    plt.figure(figsize=(8, 4))
    sns.boxplot(data=exp_data)
    plt.title('Boxplot de fator_expansao')
    plt.show()
else:
    print('Não há dados suficientes para análise de fator_expansao.')

print('\n--- Diagnóstico completo ---')
print('1. Verifique se as variáveis estão normalizadas (média ~0, std ~1, sem outliers extremos).')
print('2. Se alguma variável domina o PCA, ajuste a normalização ou revise o cálculo.')
print('3. Se houver muitos NaNs, revise o pipeline para garantir preenchimento dos dados.')
print('4. Após ajustes, reexecute o pipeline e reavalie a separação dos regimes.')
