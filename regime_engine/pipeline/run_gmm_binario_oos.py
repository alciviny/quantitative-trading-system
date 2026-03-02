
import sys
from pathlib import Path
import pandas as pd
import logging
# Adiciona o diretório raiz do projeto ao sys.path para garantir import escalável
sys.path.append(str(Path(__file__).resolve().parent.parent))
from regime_engine.pipeline.main import walk_forward_regime_detection

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Carregue seu DataFrame aqui (exemplo: CSV, Parquet, etc)
df = pd.read_csv(r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes_binario.csv', index_col=0)

# Fatores usados no clustering
fatores = ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']
for col in fatores:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Separar período OOS (exemplo: últimos 20%)
n_total = len(df)
n_oos = int(n_total * 0.2)
df_oos = df.tail(n_oos).copy()

# Parâmetros do GMM binário
n_regimes = 2
n_components_pca = 2
window_train = int(n_oos * 0.6)
window_test = int(n_oos * 0.2)

logging.info('Rodando GMM binário em dados OOS...')
labels_oos, pca1_oos = walk_forward_regime_detection(df_oos, fatores, window_train, window_test, n_regimes, n_components_pca)
df_oos['regime_binario_oos'] = labels_oos
df_oos['pca1_rolling_oos'] = pca1_oos

# Estatísticas por regime OOS
print('--- Estatísticas OOS por regime binário ---')
grp = df_oos.groupby('regime_binario_oos')
print(grp.agg({
    'fator_persistencia': ['mean', 'std'],
    'fator_estrutura': ['mean', 'std'],
    'fator_expansao': ['mean', 'std'],
    'fator_liquidez': ['mean', 'std'],
    'pca1_rolling_oos': ['mean', 'std'],
}))
print('\nContagem de observações por regime OOS:')
print(grp.size())

# Exporta resultados OOS
output_path = r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/regime_engine/pipeline/resultados_regimes_binario_oos.csv'
df_oos.to_csv(output_path)
logging.info(f'Resultados OOS exportados para {output_path}')
