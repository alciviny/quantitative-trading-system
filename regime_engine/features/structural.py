import numpy as np
import pandas as pd

def add_structural_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona features estruturais ao DataFrame.
    """
    def rolling_zscore(series, window=252):
        mean = series.shift(1).rolling(window).mean()
        std  = series.shift(1).rolling(window).std()
        return (series - mean) / (std + 1e-8)

    # Hurst e Half-life normalizados
    if 'hurst_72_returns' in df.columns and 'half_life_60' in df.columns:
        # Garante que são Series, não DataFrame
        hurst = df['hurst_72_returns']
        if isinstance(hurst, pd.DataFrame):
            hurst = hurst.iloc[:, 0]
        half_life = df['half_life_60']
        if isinstance(half_life, pd.DataFrame):
            half_life = half_life.iloc[:, 0]
        half_life_corr = pd.concat([hurst, half_life], axis=1).corr().iloc[0, 1]
        if half_life_corr < 0:
            half_life = -half_life
        df['hurst_norm']     = rolling_zscore(hurst)
        df['half_life_norm'] = rolling_zscore(half_life)
    # Fator de persistência via PCA
    from sklearn.decomposition import PCA
    persist_data = df[['hurst_norm', 'half_life_norm']].dropna()
    persist_factor = np.full(len(df), np.nan)
    if len(persist_data) > 0:
        pca_persist  = PCA(n_components=1)
        persist_factor[persist_data.index] = pca_persist.fit_transform(persist_data).ravel()
    df['fator_persistencia'] = persist_factor

    # Fator de estrutura
    chopp_col = None
    for c in df.columns:
        if c.lower() == 'choppiness_14':
            chopp_col = c
            break
    if 'entropy_20' in df.columns and chopp_col:
        entropy = df['entropy_20']
        if isinstance(entropy, pd.DataFrame):
            entropy = entropy.iloc[:, 0]
        choppiness = df[chopp_col]
        if isinstance(choppiness, pd.DataFrame):
            choppiness = choppiness.iloc[:, 0]
        df['entropy_norm']    = rolling_zscore(-entropy)
        df['choppiness_norm'] = rolling_zscore(-choppiness)
        df['fator_estrutura'] = (df['entropy_norm'] + df['choppiness_norm']) / 2

    # Fator de expansão
    window_vol = 63
    if 'volatility_21' in df.columns:
        df['vol_z'] = rolling_zscore(df['volatility_21'], window=window_vol)
        df['vol_of_vol']   = df['volatility_21'].rolling(21).std()
        df['vol_of_vol_z'] = rolling_zscore(df['vol_of_vol'], window=window_vol)
    if 'high' in df.columns and 'low' in df.columns:
        atr_period = 14
        df['range']              = df['high'] - df['low']
        df['atr']                = df['range'].rolling(atr_period).mean()
        df['amplitude_relativa'] = df['range'] / (df['atr'] + 1e-6)
        df['amplitude_relativa_z'] = rolling_zscore(df['amplitude_relativa'].fillna(0), window=window_vol)

    # Auditoria das variáveis antes do PCA
    exp_vars = ['vol_z', 'amplitude_relativa_z', 'vol_of_vol_z']
    print('--- Auditoria das variáveis do fator_expansao ---')
    for var in exp_vars:
        if var in df.columns:
            print(f'{var}: média={df[var].mean():.4f}, std={df[var].std():.4f}, min={df[var].min():.4f}, max={df[var].max():.4f}, NaNs={df[var].isna().sum()}')
        else:
            print(f'{var} não encontrada.')

    exp_data = df[exp_vars].dropna()
    # Normalização robusta das variáveis antes do PCA
    if not exp_data.empty:
        exp_data_norm = (exp_data - exp_data.mean()) / (exp_data.std() + 1e-8)
        print('--- Auditoria das variáveis NORMALIZADAS ---')
        for var in exp_data_norm.columns:
            print(f'{var}: média={exp_data_norm[var].mean():.4f}, std={exp_data_norm[var].std():.4f}, min={exp_data_norm[var].min():.4f}, max={exp_data_norm[var].max():.4f}')
        pca_exp = PCA(n_components=1)
        exp_factor_raw = np.full(len(df), np.nan)
        exp_factor_raw[exp_data_norm.index] = pca_exp.fit_transform(exp_data_norm).ravel()
        # Normalização final do fator_expansao
        fator_expansao = (exp_factor_raw - np.nanmean(exp_factor_raw)) / (np.nanstd(exp_factor_raw) + 1e-8)
        print(f'--- Auditoria do fator_expansao final ---')
        print(f'média={np.nanmean(fator_expansao):.4f}, std={np.nanstd(fator_expansao):.4f}, min={np.nanmin(fator_expansao):.4f}, max={np.nanmax(fator_expansao):.4f}, NaNs={np.isnan(fator_expansao).sum()}')
        df['fator_expansao'] = fator_expansao
    else:
        df['fator_expansao'] = np.nan

    # Fator de liquidez
    if 'volume' in df.columns and 'daily_return' in df.columns:
        df['volume_log']    = np.log(df['volume'] + 1e-6)
        df['amihud_proxy']  = np.abs(df['daily_return']) / (df['volume_log'] + 1e-6)
        df['amihud_z']      = rolling_zscore(df['amihud_proxy'].fillna(0), window=window_vol)
        df['fator_liquidez'] = df['amihud_z']

    return df
