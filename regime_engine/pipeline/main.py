# --- Política de Validação e Alinhamento de Labels ---
# Garante import do regime_engine ao rodar de qualquer diretório
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
# Este pipeline executa walk-forward validation com janelas móveis.
# Em cada janela:
# 1. Normaliza os fatores originais (z-score da janela)
# 2. Aplica PCA re-treinado
# 3. Fit do GMM
# 4. Calcula centroides dos clusters no espaço normalizado original
# 5. Alinha labels por distância dos centroides com a janela anterior
# 6. Na primeira janela, ordena por volatilidade realizada

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

def align_labels_by_centroid_distance(centroids_prev, centroids_curr):
    """
    Alinha labels do GMM atual com os da janela anterior por distância dos centroides.
    Retorna um mapeamento: label_novo -> label_antigo
    """
    from scipy.optimize import linear_sum_assignment
    dist_matrix = np.linalg.norm(centroids_curr[:, None, :] - centroids_prev[None, :, :], axis=2)
    row_ind, col_ind = linear_sum_assignment(dist_matrix)
    return dict(zip(row_ind, col_ind))

def walk_forward_regime_detection(df, fatores, window_train=500, window_test=100, n_regimes=3, n_components_pca=2):
    logging.info(f'Iniciando walk-forward regime detection: {len(df)} linhas, fatores={fatores}')
    logging.info(f'Config: window_train={window_train}, window_test={window_test}, n_regimes={n_regimes}, n_components_pca={n_components_pca}')
    labels_full = np.full(len(df), np.nan)
    pca1_full = np.full(len(df), np.nan)
    centroids_prev = None
    i = 0
    while i + window_train + window_test <= len(df):
        logging.info(f'Janela {i} - {i+window_train} (treino), {i+window_train} - {i+window_train+window_test} (teste)')
        idx_train = range(i, i + window_train)
        idx_test  = range(i + window_train, i + window_train + window_test)
        X_train = df.iloc[idx_train][fatores].values
        X_test  = df.iloc[idx_test][fatores].values
        scaler = StandardScaler()
        X_train_norm = scaler.fit_transform(X_train)
        X_test_norm  = scaler.transform(X_test)
        pca = PCA(n_components=n_components_pca)
        X_train_pca = pca.fit_transform(X_train_norm)
        X_test_pca  = pca.transform(X_test_norm)
        from regime_engine.models.gmm import RegimeGMM
        gmm = RegimeGMM(n_regimes=n_regimes)
        gmm.fit(X_train_pca)
        logging.info(f'GMM fit concluído. Labels únicos: {np.unique(gmm.predict(X_train_pca))}')
        labels_test = gmm.predict(X_test_pca)
        logging.info(f'Labels de teste únicos: {np.unique(labels_test)}')
        # Centroides dos clusters no espaço normalizado original
        centroids_curr = np.array([X_test_norm[labels_test == k].mean(axis=0) if np.any(labels_test == k) else np.zeros(X_test_norm.shape[1]) for k in range(n_regimes)])
        # Alinhamento de labels
        if centroids_prev is not None:
            logging.info('Alinhando labels por distância dos centroides...')
            mapping = align_labels_by_centroid_distance(centroids_prev, centroids_curr)
            labels_test_aligned = np.array([mapping.get(l, l) for l in labels_test])
        else:
            logging.info('Primeira janela: ordenando labels por volatilidade realizada.')
            vols = np.array([X_test_norm[labels_test == k][:, 0].std() if np.any(labels_test == k) else 0 for k in range(n_regimes)])
            order = np.argsort(vols)
            mapping = {k: order[k] for k in range(n_regimes)}
            labels_test_aligned = np.array([mapping.get(l, l) for l in labels_test])
        labels_full[idx_test] = labels_test_aligned
        pca1_full[idx_test] = X_test_pca[:, 0]
        centroids_prev = centroids_curr
        logging.info(f'Janela {i} - {i+window_train+window_test} concluída.')
        i += window_test
    logging.info('Walk-forward regime detection finalizado.')
    return labels_full, pca1_full

import pandas as pd
import numpy as np
from regime_engine.features.structural import add_structural_features
from regime_engine.features.market import add_market_features
from regime_engine.models.gmm import RegimeGMM
from regime_engine.filters.persistence import majority_filter, min_persistence_filter
from regime_engine.utils.normalization import rolling_zscore

# Exemplo de pipeline

def run_pipeline(df: pd.DataFrame):
    logging.info('Iniciando pipeline de regimes...')
    df = add_structural_features(df)
    df = add_market_features(df)
    logging.info('Features estruturais e de mercado adicionadas.')
    fatores = ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']
    window_smooth = 60
    fatores_smooth = df[fatores].rolling(window_smooth).mean()
    fatores_smooth_valid = fatores_smooth.dropna()
    logging.info(f'{len(fatores_smooth_valid)} linhas válidas após suavização.')
    # Walk-forward regime detection com alinhamento robusto de labels
    n_regimes = 3
    n_components_pca = 2
    window_train = 500
    window_test = 100
    logging.info('Detectando regimes com walk-forward...')
    labels_full, pca1_full = walk_forward_regime_detection(fatores_smooth_valid, fatores, window_train, window_test, n_regimes, n_components_pca)
    fatores_smooth_valid['regime_rolling'] = labels_full
    fatores_smooth_valid['pca1_rolling']   = pca1_full
    logging.info('Aplicando filtros de persistência...')
    logging.info('Chamando majority_filter...')
    labels = majority_filter(fatores_smooth_valid['regime_rolling'], window=5)
    logging.info('majority_filter concluído.')
    logging.info('Chamando min_persistence_filter...')
    labels = min_persistence_filter(labels, min_len=5)
    logging.info('min_persistence_filter concluído.')
    fatores_smooth_valid['regime_rolling'] = labels.values
    logging.info('Filtros de persistência aplicados.')
    # Validação: retorno futuro médio por regime
    if 'close' in df.columns:
        logging.info('Calculando estatísticas de retorno futuro por regime...')
        df_valid = df.loc[fatores_smooth_valid.index].copy()
        df_valid['regime_rolling'] = fatores_smooth_valid['regime_rolling']
        df_valid['ret_futuro_10']  = df_valid['close'].pct_change(10).shift(-10)
        regime_stats = df_valid.groupby('regime_rolling')['ret_futuro_10'].agg(['mean','std','count'])
        logging.info('Estatísticas de retorno futuro por regime calculadas.')
        print('Retorno futuro médio por regime (rolling):')
        print(regime_stats)
    logging.info('Pipeline de regimes finalizado.')

    return fatores_smooth_valid

# Bloco de execução direta para rodar pipeline e exibir logs
if __name__ == '__main__':
    # Exemplo: carregue o arquivo de dados real
    df = pd.read_csv(r'c:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/src/co_piloto_quant/data/results_regimes/resultados_regimes_binario.csv', index_col=0)
    # Converter fatores para float
    for col in ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    run_pipeline(df)
