import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.mixture import GaussianMixture

# Caminho correto para rodar a partir da raiz do projeto
FEATURES_PATH = 'co-piloto-quant/src/co_piloto_quant/data/features/ITUB4.SA_features.parquet'
OUTPUT_PATH = 'co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_ITUB4.SA.csv'

# Carregar dados de features
print('Carregando features...')
df = pd.read_parquet(FEATURES_PATH)

# --- Normalização helper ---

# --- Rolling z-score normalização ---
def rolling_zscore(series, window=252):
    # Walk-forward puro: não inclui o valor atual na média/STD
    mean = series.shift(1).rolling(window).mean()
    std = series.shift(1).rolling(window).std()
    return (series - mean) / (std + 1e-8)






## === CÁLCULO DOS FATORES PRIMEIRO ===
# ...existing code para cálculo dos fatores...

## Bloco removido — cálculo do campo estrutural contínuo duplicado

# --- Verificação de correlação Hurst x Half-life ---
print('Correlação Hurst x Half-life:')
print(df[['hurst_72_returns', 'half_life_60']].corr())

# Se a correlação for negativa, inverta half-life
half_life_corr = df[['hurst_72_returns', 'half_life_60']].corr().iloc[0,1]
if half_life_corr < 0:
    print('Invertendo half-life para alinhar com Hurst (persistência).')
    df['half_life_60'] = -df['half_life_60']

# === Fator de Persistência ===
from sklearn.decomposition import PCA
df['hurst_norm'] = rolling_zscore(df['hurst_72_returns'])
df['half_life_norm'] = rolling_zscore(df['half_life_60'])
# PCA dentro do eixo
pca_persist = PCA(n_components=1)
persist_data = df[['hurst_norm', 'half_life_norm']].dropna()
persist_factor = np.full(len(df), np.nan)
if len(persist_data) > 0:
    persist_factor[persist_data.index] = pca_persist.fit_transform(persist_data).ravel()
df['fator_persistencia'] = persist_factor

# === Fator de Estrutura ===
df['entropy_norm'] = rolling_zscore(-df['entropy_20'])  # invertido
df['choppiness_norm'] = rolling_zscore(-df['Choppiness_14'])  # invertido
df['fator_estrutura'] = (df['entropy_norm'] + df['choppiness_norm']) / 2

# === Fator de Expansão ===
window_vol = 63  # 3 meses
df['vol_z'] = rolling_zscore(df['volatility_21'], window=window_vol)
atr_period = 14
df['range'] = df['high'] - df['low']
df['atr'] = df['range'].rolling(atr_period).mean()
df['amplitude_relativa'] = df['range'] / (df['atr'] + 1e-6)
df['amplitude_relativa_z'] = rolling_zscore(df['amplitude_relativa'].fillna(0), window=window_vol)
# Vol of Vol
df['vol_of_vol'] = df['volatility_21'].rolling(21).std()
df['vol_of_vol_z'] = rolling_zscore(df['vol_of_vol'], window=window_vol)
# PCA dentro do eixo expansão
from sklearn.decomposition import PCA
exp_data = df[['vol_z', 'amplitude_relativa_z', 'vol_of_vol_z']].dropna()
exp_factor = np.full(len(df), np.nan)
if len(exp_data) > 0:
    pca_exp = PCA(n_components=1)
    exp_factor[exp_data.index] = pca_exp.fit_transform(exp_data).ravel()
df['fator_expansao'] = exp_factor


# --- Fator Liquidez (institucional: log(volume) antes do Amihud) ---
df['volume_log'] = np.log(df['volume'] + 1e-6)
df['amihud_proxy'] = np.abs(df['daily_return']) / (df['volume_log'] + 1e-6)
df['amihud_z'] = rolling_zscore(df['amihud_proxy'].fillna(0), window=window_vol)

df['fator_liquidez'] = df['amihud_z']

# === CAMADA 1 — Estado Estrutural Contínuo ===
print("\n[INFO] Calculando campo estrutural contínuo (estado, magnitude, direção, dinâmica, instabilidade)...")
window_state = 126  # 6 meses
for col in [
    "fator_persistencia",
    "fator_estrutura",
    "fator_expansao",
    "fator_liquidez"
]:
    df[col + "_state"] = rolling_zscore(df[col], window_state)

# Magnitude estrutural
state_cols = [c for c in df.columns if c.endswith("_state")]
df["state_magnitude"] = np.sqrt(sum(df[c]**2 for c in state_cols))

# Direção estrutural (PCA 1D)
from sklearn.decomposition import PCA
state_data = df[state_cols].dropna()
pca_state = PCA(n_components=1)
df.loc[state_data.index, "state_direction"] = pca_state.fit_transform(state_data).ravel()

# === CAMADA 2 — Dinâmica do Estado (ΔS) ===
# Velocidade estrutural
df["state_velocity"] = df["state_magnitude"].diff()
# Aceleração estrutural
df["state_acceleration"] = df["state_velocity"].diff()
# Rotação do campo
df["direction_change"] = df["state_direction"].diff()

# === CAMADA 3 — Estabilidade do Campo ===
window_stability = 63
df["state_instability"] = df["state_magnitude"].rolling(window_stability).std()

print("[INFO] Campo estrutural contínuo calculado com sucesso!")

# Salvar fatores estruturais


# Checagem de ortogonalidade e suavização
fatores = df[['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']]
print('Correlação entre fatores estruturais:')
print(fatores.corr())
fatores.to_csv(OUTPUT_PATH)
print(f'Fatores estruturais salvos em {OUTPUT_PATH}')


# === Suavização dos fatores ===

window_smooth = 60  # suavização aumentada para regimes mais longos (~60 dias)
fatores_smooth = fatores.rolling(window_smooth).mean()
fatores_smooth_valid = fatores_smooth.dropna()


# === Pipeline Rolling Institucional (Scaler, PCA, GMM) ===
# === Teste de BIC para número de regimes (comentado, não rodar mais) ===
# print("\n[INFO] Testando BIC para diferentes números de regimes...")
# X_bic = fatores_smooth_valid.values
# scaler_bic = StandardScaler()
# X_bic_scaled = scaler_bic.fit_transform(X_bic)
# pca_bic = PCA(n_components=2)
# X_bic_pca = pca_bic.fit_transform(X_bic_scaled)
# bic_scores = []
# regime_range = range(1, 6)
# for k in regime_range:
#     gmm_bic = GaussianMixture(n_components=k, covariance_type='full', random_state=42)
#     gmm_bic.fit(X_bic_pca)
#     bic = gmm_bic.bic(X_bic_pca)
#     bic_scores.append(bic)
#     print(f"Regimes: {k} | BIC: {bic:.2f}")
#
# # Gráfico BIC
# plt.figure(figsize=(8,4))
# plt.plot(regime_range, bic_scores, marker='o')
# plt.title('BIC vs Número de Regimes (GMM)')
# plt.xlabel('Número de Regimes')
# plt.ylabel('BIC')
# plt.grid(True)
# plt.show()
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import GaussianMixture

fatores_smooth_valid = fatores_smooth.dropna()
window_rolling = 360  # janela maior para regimes mais longos (~40 dias)
n_components_pca = 2
n_regimes = 3  # testar 3 regimes conforme BIC

rolling_labels = [np.nan] * len(fatores_smooth_valid)
rolling_pca_proj = [np.nan] * len(fatores_smooth_valid)

for i in range(window_rolling, len(fatores_smooth_valid)):
    X_hist = fatores_smooth_valid.iloc[i-window_rolling:i].values
    scaler = StandardScaler()
    X_hist_scaled = scaler.fit_transform(X_hist)
    pca = PCA(n_components=n_components_pca)
    X_hist_pca = pca.fit_transform(X_hist_scaled)
    gmm = GaussianMixture(n_components=n_regimes, covariance_type='full', random_state=42)
    gmm.fit(X_hist_pca)
    x_t = fatores_smooth_valid.iloc[i].values.reshape(1, -1)
    x_t_scaled = scaler.transform(x_t)
    x_t_pca = pca.transform(x_t_scaled)
    label = gmm.predict(x_t_pca)[0]
    rolling_labels[i] = label
    rolling_pca_proj[i] = x_t_pca[0]

# --- Filtro de persistência mínima nos labels dos regimes ---
def majority_filter(labels, window=5):
    labels = pd.Series(labels)
    return labels.rolling(window, min_periods=1).apply(lambda x: x.mode()[0] if len(x.mode()) > 0 else np.nan)

# --- Filtro de permanência mínima: elimina regimes de 1 dia ---
def min_persistence_filter(labels, min_len=2):
    labels = pd.Series(labels)
    filtered = labels.copy()
    prev_label = labels.iloc[0]
    count = 1
    for i in range(1, len(labels)):
        if labels.iloc[i] == prev_label:
            count += 1
        else:
            # Se bloco anterior teve só 1 dia, substitui pelo regime anterior
            if count < min_len:
                filtered.iloc[i-count:i] = labels.iloc[i]
            count = 1
            prev_label = labels.iloc[i]
    # Último bloco
    if count < min_len:
        filtered.iloc[len(labels)-count:] = prev_label
    return filtered


filtered_labels = majority_filter(rolling_labels, window=5)
fatores_smooth_valid['regime_rolling'] = rolling_labels
filtered_labels = min_persistence_filter(filtered_labels, min_len=2)
fatores_smooth_valid['regime_rolling'] = filtered_labels
fatores_smooth_valid['pca1_rolling'] = [p[0] if isinstance(p, np.ndarray) else np.nan for p in rolling_pca_proj]
fatores_smooth_valid['pca2_rolling'] = [p[1] if isinstance(p, np.ndarray) else np.nan for p in rolling_pca_proj]

print("\nRolling pipeline institucional (Scaler, PCA, GMM) concluído.")



# --- Validação dos regimes (usando regime_rolling) ---
df_valid = df.loc[fatores_smooth_valid.index].copy()
df_valid['regime_rolling'] = fatores_smooth_valid['regime_rolling']
df_valid['ret_futuro_10'] = df_valid['close'].pct_change(10).shift(-10)
print('\nRetorno futuro médio por regime (rolling):')
print(df_valid.groupby('regime_rolling')['ret_futuro_10'].mean())
print('\nVolatilidade futura por regime (rolling):')
print(df_valid.groupby('regime_rolling')['ret_futuro_10'].std())

# --- Duração real dos regimes (blocos) ---
df_valid['regime_change'] = df_valid['regime_rolling'].diff().ne(0)
df_valid['block'] = df_valid['regime_change'].cumsum()
duracoes = df_valid.groupby('block').size()
print('\nDuração dos regimes (em candles, rolling):')
print(duracoes.describe())

# --- Validação de distribuição: skew e kurtosis dos retornos futuros por regime ---
print('\nSkew e Kurtosis dos retornos futuros por regime (rolling):')
for r in sorted(df_valid['regime_rolling'].dropna().unique()):
    regime_df = df_valid[df_valid['regime_rolling']==r]['ret_futuro_10'].dropna()
    skew = regime_df.skew()
    kurt = regime_df.kurt()
    print(f'Regime {r}:')
    print(f'  Skew: {skew:.4f}')
    print(f'  Kurtosis: {kurt:.4f}')

# --- Diagnóstico institucional (rolling) ---
print("\nAssinatura média dos fatores por regime (rolling):")
print(fatores_smooth_valid.groupby("regime_rolling")[[
    "fator_persistencia",
    "fator_estrutura",
    "fator_expansao",
    "fator_liquidez"
]].mean())

print("\nMatriz de transição de Markov dos regimes (rolling):")
regimes = fatores_smooth_valid['regime_rolling'].dropna().astype(int)
regimes_shifted = regimes.shift(1)
markov = pd.crosstab(regimes_shifted, regimes, normalize='index')
print(markov)
# Visualização simples (opcional)
fatores_smooth.plot(subplots=True, figsize=(12,8), title='Fatores Estruturais Suavizados ao Longo do Tempo')
plt.tight_layout()
plt.show()
