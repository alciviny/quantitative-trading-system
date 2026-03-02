from energy_engine.utils.rolling import robust_zscore
def calcular_energia_v4(fatores, window_zscore_robusto=60, window_v4=21):
    '''Calcula energia v0.4 e sua média móvel.'''
    fatores = fatores.copy()
    missing = []
    for col in ['energia_estrutural', 'energia_v2', 'fatores_entropy']:
        if col not in fatores.columns:
            missing.append(col)
    if missing:
        print(f'[energy.py] Não é possível calcular energia_v4: faltam as colunas {missing}')
        return fatores
    # Preencher NaNs dos insumos
    for col in ['energia_estrutural', 'energia_v2', 'fatores_entropy']:
        n_before = fatores[col].isnull().sum()
        fatores[col] = fatores[col].ffill().bfill()
        n_after = fatores[col].isnull().sum()
        print(f'[energy.py] Preenchendo NaNs em {col}: antes={n_before}, depois={n_after}')
        if fatores[col].isnull().all():
            print(f'[energy.py] Atenção: coluna {col} está totalmente vazia mesmo após preenchimento!')
    print('[energy.py] Calculando energia_v4...')
    print(f"[energy.py] energia_estrutural head: {fatores['energia_estrutural'].head()}")
    print(f"[energy.py] energia_v2 head: {fatores['energia_v2'].head()}")
    print(f"[energy.py] fatores_entropy head: {fatores['fatores_entropy'].head()}")
    fatores['energia_v4'] = (
        robust_zscore(fatores['energia_estrutural'], window_zscore_robusto) *
        robust_zscore(fatores['energia_v2'], window_zscore_robusto) +
        robust_zscore(fatores['fatores_entropy'], window_zscore_robusto)
    )
    fatores['energia_v4_roll'] = fatores['energia_v4'].rolling(window_v4).mean()
    return fatores
import numpy as np
import pandas as pd
from energy_engine.utils.rolling import rolling_zscore

def calcular_energia_estrutural(fatores, window_compressao=21, window_instab=21, window_zscore_robusto=60):
    '''Calcula energia estrutural, compressão, instabilidade e zscores.'''
    fatores = fatores.copy()
    fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)
    regime = fatores['regime_rolling'].fillna(method='ffill')
    fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
    fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()
    fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
    fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
    fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']
    return fatores

def calcular_entropia_centroides(fatores, window_entropy=21, window_v2=21, window_v3=21):
    '''Calcula entropia, centroides, energia_v2, energia_v3 e suas médias móveis.'''
    fatores = fatores.copy()
    fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)
    fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
    regimes = fatores['regime_rolling'].fillna(method='ffill')
    centroides = fatores_v.groupby(regimes).transform('mean')
    fatores_v = fatores_v.loc[centroides.index]
    fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
    fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()
    fatores['energia_v3'] = (
        fatores['energia_estrutural'] +
        fatores['energia_v2'] +
        fatores['fatores_entropy']
    )
    fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()
    return fatores
