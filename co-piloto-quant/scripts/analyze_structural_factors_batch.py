import os
import glob
import multiprocessing as mp
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture

def process_ativo(features_path):
    ativo = os.path.basename(features_path).replace('_features.parquet','')
    output_path = f'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_{ativo}.csv'
    try:
        df = pd.read_parquet(features_path)

        # --- Helper: rolling zscore ---
        def rolling_zscore(series, window=252):
            mean = series.shift(1).rolling(window).mean()
            std  = series.shift(1).rolling(window).std()
            return (series - mean) / (std + 1e-8)

        # --- Persistência ---
        if 'hurst_72_returns' in df.columns and 'half_life_60' in df.columns:
            corr = df[['hurst_72_returns', 'half_life_60']].corr().iloc[0,1]
            if corr < 0:
                df['half_life_60'] = -df['half_life_60']

        df['hurst_norm']     = rolling_zscore(df.get('hurst_72_returns', pd.Series(np.nan, index=df.index)))
        df['half_life_norm'] = rolling_zscore(df.get('half_life_60', pd.Series(np.nan, index=df.index)))

        pca_persist = PCA(n_components=1)
        persist_data = df[['hurst_norm','half_life_norm']].dropna()
        persist_factor = np.full(len(df), np.nan)
        if len(persist_data) > 0:
            persist_factor[persist_data.index] = pca_persist.fit_transform(persist_data).ravel()
        df['fator_persistencia'] = persist_factor

        # --- Estrutura ---
        df['entropy_norm']    = rolling_zscore(-df.get('entropy_20', pd.Series(np.nan, index=df.index)))
        df['choppiness_norm'] = rolling_zscore(-df.get('Choppiness_14', pd.Series(np.nan, index=df.index)))
        df['fator_estrutura'] = (df['entropy_norm'] + df['choppiness_norm']) / 2

        # --- Expansão ---
        window_vol = 63
        df['vol_z'] = rolling_zscore(df.get('volatility_21', pd.Series(np.nan, index=df.index)), window=window_vol)

        atr_period = 14
        df['range'] = df.get('high', pd.Series(np.nan, index=df.index)) - df.get('low', pd.Series(np.nan, index=df.index))
        df['atr'] = df['range'].rolling(atr_period).mean()
        df['amplitude_relativa'] = df['range'] / (df['atr'] + 1e-6)
        df['amplitude_relativa_z'] = rolling_zscore(df['amplitude_relativa'].fillna(0), window=window_vol)
        df['vol_of_vol'] = df.get('volatility_21', pd.Series(np.nan, index=df.index)).rolling(21).std()
        df['vol_of_vol_z'] = rolling_zscore(df['vol_of_vol'], window=window_vol)

        exp_data = df[['vol_z','amplitude_relativa_z','vol_of_vol_z']].dropna()
        exp_factor = np.full(len(df), np.nan)
        if len(exp_data) > 0:
            pca_exp = PCA(n_components=1)
            exp_factor[exp_data.index] = pca_exp.fit_transform(exp_data).ravel()
        df['fator_expansao'] = exp_factor

        # --- Liquidez ---
        df['volume_log'] = np.log(df.get('volume', pd.Series(np.nan, index=df.index)) + 1e-6)
        df['amihud_proxy'] = np.abs(df.get('daily_return', pd.Series(np.nan, index=df.index))) / (df['volume_log'] + 1e-6)
        df['amihud_z'] = rolling_zscore(df['amihud_proxy'].fillna(0), window=window_vol)
        df['fator_liquidez'] = df['amihud_z']

        # --- Suavização ---
        fatores = df[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
        window_smooth = 60
        fatores_smooth = fatores.rolling(window_smooth).mean()
        fatores_smooth_valid = fatores_smooth.dropna()

        # --- Pipeline Rolling PCA + GMM ---
        window_rolling = 360
        n_components_pca = 2
        n_regimes = 3
        rolling_labels = [np.nan] * len(fatores_smooth_valid)
        rolling_pca_proj = [np.nan] * len(fatores_smooth_valid)

        for i in range(window_rolling, len(fatores_smooth_valid)):
            X_hist = fatores_smooth_valid.iloc[i - window_rolling:i].values
            scaler = StandardScaler()
            X_hist_scaled = scaler.fit_transform(X_hist)
            pca = PCA(n_components=n_components_pca)
            X_hist_pca = pca.fit_transform(X_hist_scaled)
            gmm = GaussianMixture(n_components=n_regimes, covariance_type='full', random_state=42)
            gmm.fit(X_hist_pca)
            x_t = fatores_smooth_valid.iloc[i].values.reshape(1,-1)
            x_t_scaled = scaler.transform(x_t)
            x_t_pca = pca.transform(x_t_scaled)
            rolling_labels[i] = gmm.predict(x_t_pca)[0]
            rolling_pca_proj[i] = x_t_pca[0]

        # --- Filtros de persistência ---
        def majority_filter(labels, window=5):
            s = pd.Series(labels)
            return s.rolling(window, min_periods=1).apply(lambda x: x.mode()[0] if len(x.mode())>0 else np.nan)
        def min_persistence_filter(labels, min_len=5):
            labels = pd.Series(labels)
            filtered = labels.copy()
            changed = True
            while changed:
                changed = False
                prev_label, count = labels.iloc[0], 1
                for i in range(1,len(labels)):
                    if labels.iloc[i]==prev_label:
                        count+=1
                    else:
                        if count<min_len:
                            filtered.iloc[i-count:i] = labels.iloc[i]
                            changed=True
                        count=1
                        prev_label=labels.iloc[i]
                if count<min_len:
                    filtered.iloc[len(labels)-count:] = prev_label
                    changed=True
                labels = filtered.copy()
            return filtered

        filtered_labels = majority_filter(rolling_labels, window=5)
        filtered_labels = min_persistence_filter(filtered_labels, min_len=5)
        fatores_smooth_valid['regime_rolling'] = filtered_labels.values
        fatores_smooth_valid['pca1_rolling'] = [p[0] if isinstance(p,np.ndarray) else np.nan for p in rolling_pca_proj]
        fatores_smooth_valid['pca2_rolling'] = [p[1] if isinstance(p,np.ndarray) else np.nan for p in rolling_pca_proj]


        # --- Adicionar coluna close e retorno futuro se possível ---
        if 'close' in df.columns:
            # Alinhar índices para garantir merge correto
            fatores_smooth_valid['close'] = df['close'].reindex(fatores_smooth_valid.index)
            fatores_smooth_valid['ret_futuro_10'] = fatores_smooth_valid['close'].pct_change(10).shift(-10)
        elif 'ret_futuro_10' in df.columns:
            fatores_smooth_valid['ret_futuro_10'] = df['ret_futuro_10'].reindex(fatores_smooth_valid.index)

        # Salvar todas as colunas relevantes para máxima utilidade futura
        # Inclui: fatores brutos, normalizados, intermediários, rolling PCA, regimes, preços, retornos, datas
        cols_to_save = []
        # Colunas do DataFrame original que são úteis
        base_cols = ['date','open','high','low','close','volume','daily_return']
        for col in base_cols:
            if col in df.columns:
                fatores_smooth_valid[col] = df[col].reindex(fatores_smooth_valid.index)
                cols_to_save.append(col)
        # Fatores brutos
        for col in ['hurst_72_returns','half_life_60','entropy_20','Choppiness_14','volatility_21']:
            if col in df.columns:
                fatores_smooth_valid[col] = df[col].reindex(fatores_smooth_valid.index)
                cols_to_save.append(col)
        # Fatores normalizados/intermediários
        for col in ['hurst_norm','half_life_norm','entropy_norm','choppiness_norm','vol_z','amplitude_relativa','amplitude_relativa_z','vol_of_vol','vol_of_vol_z','amihud_proxy','amihud_z']:
            if col in fatores_smooth_valid.columns:
                cols_to_save.append(col)
        # Fatores finais
        for col in ['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']:
            if col in fatores_smooth_valid.columns:
                cols_to_save.append(col)
        # Rolling PCA e regimes
        for col in ['regime_rolling','pca1_rolling','pca2_rolling']:
            if col in fatores_smooth_valid.columns:
                cols_to_save.append(col)
        # Retorno futuro
        if 'ret_futuro_10' in fatores_smooth_valid.columns:
            cols_to_save.append('ret_futuro_10')
        # Remove duplicatas mantendo ordem
        cols_to_save = list(dict.fromkeys(cols_to_save))
        fatores_final = fatores_smooth_valid[cols_to_save].copy()
        fatores_final.to_csv(output_path)
        print(f'✓ {ativo} processado com sucesso.')

    except Exception as e:
        print(f'Erro ao processar {ativo}: {e}')

if __name__ == '__main__':
    features_dir = 'co-piloto-quant/src/co_piloto_quant/data/features'
    # Filtrar apenas ativos brasileiros (.SA)
    files = [f for f in glob.glob(os.path.join(features_dir, '*_features.parquet')) if f.endswith('.SA_features.parquet')]
    print(f'Encontrados {len(files)} arquivos de ativos brasileiros.')
    
    # Multiprocessamento
    n_cpus = max(1, mp.cpu_count() - 1)  # deixar 1 CPU livre
    with mp.Pool(n_cpus) as pool:
        pool.map(process_ativo, files)

    print('Processamento batch concluído.')