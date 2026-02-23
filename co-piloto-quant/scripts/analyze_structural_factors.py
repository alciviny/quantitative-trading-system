import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture
import matplotlib.pyplot as plt

FEATURES_PATH = 'co-piloto-quant/src/co_piloto_quant/data/features/VALE3.SA_features.parquet'
OUTPUT_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_VALE3.SA.csv'

# ── 1. Carregar dados ────────────────────────────────────────────────────────
print('Carregando features...')
df = pd.read_parquet(FEATURES_PATH)

# ── 2. Helper ────────────────────────────────────────────────────────────────
def rolling_zscore(series, window=252):
    mean = series.shift(1).rolling(window).mean()
    std  = series.shift(1).rolling(window).std()
    return (series - mean) / (std + 1e-8)

# ── 3. Verificação Hurst x Half-life ────────────────────────────────────────
print('Correlação Hurst x Half-life:')
print(df[['hurst_72_returns', 'half_life_60']].corr())

half_life_corr = df[['hurst_72_returns', 'half_life_60']].corr().iloc[0, 1]
if half_life_corr < 0:
    print('Invertendo half-life para alinhar com Hurst (persistência).')
    df['half_life_60'] = -df['half_life_60']

# ── 4. Fator de Persistência ─────────────────────────────────────────────────
df['hurst_norm']     = rolling_zscore(df['hurst_72_returns'])
df['half_life_norm'] = rolling_zscore(df['half_life_60'])

pca_persist  = PCA(n_components=1)
persist_data = df[['hurst_norm', 'half_life_norm']].dropna()
persist_factor = np.full(len(df), np.nan)
if len(persist_data) > 0:
    persist_factor[persist_data.index] = pca_persist.fit_transform(persist_data).ravel()
df['fator_persistencia'] = persist_factor

# ── 5. Fator de Estrutura ─────────────────────────────────────────────────────
df['entropy_norm']    = rolling_zscore(-df['entropy_20'])
df['choppiness_norm'] = rolling_zscore(-df['Choppiness_14'])
df['fator_estrutura'] = (df['entropy_norm'] + df['choppiness_norm']) / 2

# ── 6. Fator de Expansão ──────────────────────────────────────────────────────
window_vol = 63
df['vol_z'] = rolling_zscore(df['volatility_21'], window=window_vol)

atr_period = 14
df['range']              = df['high'] - df['low']
df['atr']                = df['range'].rolling(atr_period).mean()
df['amplitude_relativa'] = df['range'] / (df['atr'] + 1e-6)
df['amplitude_relativa_z'] = rolling_zscore(df['amplitude_relativa'].fillna(0), window=window_vol)

df['vol_of_vol']   = df['volatility_21'].rolling(21).std()
df['vol_of_vol_z'] = rolling_zscore(df['vol_of_vol'], window=window_vol)

exp_data   = df[['vol_z', 'amplitude_relativa_z', 'vol_of_vol_z']].dropna()
exp_factor = np.full(len(df), np.nan)
if len(exp_data) > 0:
    pca_exp = PCA(n_components=1)
    exp_factor[exp_data.index] = pca_exp.fit_transform(exp_data).ravel()
df['fator_expansao'] = exp_factor

# ── 7. Fator de Liquidez ──────────────────────────────────────────────────────
df['volume_log']    = np.log(df['volume'] + 1e-6)
df['amihud_proxy']  = np.abs(df['daily_return']) / (df['volume_log'] + 1e-6)
df['amihud_z']      = rolling_zscore(df['amihud_proxy'].fillna(0), window=window_vol)
df['fator_liquidez'] = df['amihud_z']

# ── 8. Campo Estrutural Contínuo (Camadas 1-3) ───────────────────────────────
print("\n[INFO] Calculando campo estrutural contínuo...")
window_state = 126

for col in ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']:
    df[col + '_state'] = rolling_zscore(df[col], window_state)

state_cols = [c for c in df.columns if c.endswith('_state')]
df['state_magnitude'] = np.sqrt(sum(df[c]**2 for c in state_cols))

state_data = df[state_cols].dropna()
pca_state  = PCA(n_components=1)
df.loc[state_data.index, 'state_direction'] = pca_state.fit_transform(state_data).ravel()

df['state_velocity']    = df['state_magnitude'].diff()
df['state_acceleration'] = df['state_velocity'].diff()
df['direction_change']  = df['state_direction'].diff()

window_stability = 63
df['state_instability'] = df['state_magnitude'].rolling(window_stability).std()
print("[INFO] Campo estrutural contínuo calculado com sucesso!")

# ── 9. Suavização dos fatores ─────────────────────────────────────────────────
fatores      = df[['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']].copy()
window_smooth = 60
fatores_smooth       = fatores.rolling(window_smooth).mean()
fatores_smooth_valid = fatores_smooth.dropna()   # ← DEFINIDO AQUI, ANTES DE QUALQUER USO

# ── 10. Pipeline Rolling (Scaler → PCA → GMM) ────────────────────────────────
window_rolling    = 360
n_components_pca  = 2
n_regimes         = 3

rolling_labels   = [np.nan] * len(fatores_smooth_valid)
rolling_pca_proj = [np.nan] * len(fatores_smooth_valid)

for i in range(window_rolling, len(fatores_smooth_valid)):
    X_hist        = fatores_smooth_valid.iloc[i - window_rolling:i].values
    scaler        = StandardScaler()
    X_hist_scaled = scaler.fit_transform(X_hist)
    pca           = PCA(n_components=n_components_pca)
    X_hist_pca    = pca.fit_transform(X_hist_scaled)

    gmm = GaussianMixture(n_components=n_regimes, covariance_type='full', random_state=42)
    gmm.fit(X_hist_pca)

    x_t       = fatores_smooth_valid.iloc[i].values.reshape(1, -1)
    x_t_scaled = scaler.transform(x_t)
    x_t_pca   = pca.transform(x_t_scaled)

    rolling_labels[i]   = gmm.predict(x_t_pca)[0]
    rolling_pca_proj[i] = x_t_pca[0]

# ── 11. Filtros de persistência ───────────────────────────────────────────────
def majority_filter(labels, window=5):
    s = pd.Series(labels)
    return s.rolling(window, min_periods=1).apply(
        lambda x: x.mode()[0] if len(x.mode()) > 0 else np.nan
    )

def min_persistence_filter(labels, min_len=2):
    labels = pd.Series(labels)
    filtered = labels.copy()
    changed = True
    while changed:
        changed = False
        prev_label, count = labels.iloc[0], 1
        for i in range(1, len(labels)):
            if labels.iloc[i] == prev_label:
                count += 1
            else:
                if count < min_len:
                    filtered.iloc[i - count:i] = labels.iloc[i]
                    changed = True
                count = 1
                prev_label = labels.iloc[i]
        if count < min_len:
            filtered.iloc[len(labels) - count:] = prev_label
            changed = True
        labels = filtered.copy()
    return filtered

filtered_labels = majority_filter(rolling_labels, window=5)
filtered_labels = min_persistence_filter(filtered_labels, min_len=5)

fatores_smooth_valid['regime_rolling'] = filtered_labels.values
fatores_smooth_valid['pca1_rolling']   = [p[0] if isinstance(p, np.ndarray) else np.nan for p in rolling_pca_proj]
fatores_smooth_valid['pca2_rolling']   = [p[1] if isinstance(p, np.ndarray) else np.nan for p in rolling_pca_proj]

# ── 12. Salvamento ────────────────────────────────────────────────────────────
fatores_final = fatores_smooth_valid[
    ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez', 'regime_rolling']
].copy()

print('Correlação entre fatores estruturais:')
print(fatores_final.corr())
fatores_final.to_csv(OUTPUT_PATH)
print(f'Fatores estruturais salvos em {OUTPUT_PATH}')

# ── 13. Validação ─────────────────────────────────────────────────────────────
df_valid = df.loc[fatores_smooth_valid.index].copy()
df_valid['regime_rolling'] = fatores_smooth_valid['regime_rolling']
df_valid['ret_futuro_10']  = df_valid['close'].pct_change(10).shift(-10)

print('\nRetorno futuro médio por regime (rolling):')
print(df_valid.groupby('regime_rolling')['ret_futuro_10'].mean())
print('\nVolatilidade futura por regime (rolling):')
print(df_valid.groupby('regime_rolling')['ret_futuro_10'].std())

df_valid['regime_change'] = df_valid['regime_rolling'].diff().ne(0)
df_valid['block']         = df_valid['regime_change'].cumsum()
duracoes = df_valid.groupby('block').size()
print('\nDuração dos regimes (em candles, rolling):')
print(duracoes.describe())

print('\nSkew e Kurtosis dos retornos futuros por regime (rolling):')
for r in sorted(df_valid['regime_rolling'].dropna().unique()):
    s = df_valid[df_valid['regime_rolling'] == r]['ret_futuro_10'].dropna()
    print(f'Regime {r}: Skew={s.skew():.4f}  Kurtosis={s.kurt():.4f}')

print("\nAssinatura média dos fatores por regime (rolling):")
print(fatores_smooth_valid.groupby('regime_rolling')[
    ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']
].mean())

print("\nMatriz de transição de Markov dos regimes (rolling):")
regimes        = fatores_smooth_valid['regime_rolling'].dropna().astype(int)
regimes_shifted = regimes.shift(1)
markov = pd.crosstab(regimes_shifted, regimes, normalize='index')
print(markov)

# ── 14. Visualização ──────────────────────────────────────────────────────────
fatores_smooth.plot(subplots=True, figsize=(12, 8),
                    title='Fatores Estruturais Suavizados ao Longo do Tempo')
plt.tight_layout()
plt.show()