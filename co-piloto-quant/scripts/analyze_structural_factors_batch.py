"""
structural_factors_batch.py
----------------------------
Processa ativos brasileiros (.SA) calculando fatores estruturais e regimes de mercado
via PCA rolante + GMM. Salva resultados em CSV por ativo.
"""

import os
import glob
import multiprocessing as mp
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.mixture import GaussianMixture

# Logging simples
import datetime
def log(msg):
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")


# ---------------------------------------------------------------------------
# Funções auxiliares — globais (obrigatório para multiprocessing no Windows)
# ---------------------------------------------------------------------------

def rolling_zscore(series: pd.Series, window: int = 252) -> pd.Series:
    mean = series.shift(1).rolling(window).mean()
    std  = series.shift(1).rolling(window).std()
    return (series - mean) / (std + 1e-8)


def majority_filter(labels: pd.Series, window: int = 5) -> pd.Series:
    return labels.rolling(window, min_periods=1).apply(
        lambda x: x.mode().iloc[0] if not x.mode().empty else np.nan
    )


def min_persistence_filter(labels: pd.Series, min_len: int = 5) -> pd.Series:
    labels = labels.copy().reset_index(drop=True)
    n = len(labels)
    changed = True

    while changed:
        changed = False
        filtered = labels.copy()
        i = 0
        while i < n:
            j = i
            while j < n and labels.iloc[j] == labels.iloc[i]:
                j += 1
            if (j - i) < min_len:
                if j < n:
                    replacement = labels.iloc[j]
                elif i > 0:
                    replacement = labels.iloc[i - 1]
                else:
                    replacement = labels.iloc[i]
                filtered.iloc[i:j] = replacement
                changed = True
            i = j
        labels = filtered

    return labels


# ---------------------------------------------------------------------------
# Etapa 1: Cálculo dos fatores
# ---------------------------------------------------------------------------

def calcular_fatores(df: pd.DataFrame) -> pd.DataFrame:

    log('Iniciando cálculo dos fatores...')

    # Persistência
    if 'hurst_72_returns' in df.columns and 'half_life_60' in df.columns:
        corr = df[['hurst_72_returns', 'half_life_60']].corr().iloc[0, 1]
        if corr < 0:
            df['half_life_60'] = -df['half_life_60']

    df['hurst_norm']     = rolling_zscore(df.get('hurst_72_returns',   pd.Series(np.nan, index=df.index)))
    df['half_life_norm'] = rolling_zscore(df.get('half_life_60',       pd.Series(np.nan, index=df.index)))

    mask = df[['hurst_norm', 'half_life_norm']].notna().all(axis=1)
    persist_factor = np.full(len(df), np.nan)
    if mask.sum() > 1:
        persist_factor[mask.values] = PCA(n_components=1).fit_transform(
            df.loc[mask, ['hurst_norm', 'half_life_norm']]
        ).ravel()
    df['fator_persistencia'] = persist_factor

    # Estrutura
    df['entropy_norm']    = rolling_zscore(-df.get('entropy_20',    pd.Series(np.nan, index=df.index)))
    df['choppiness_norm'] = rolling_zscore(-df.get('Choppiness_14', pd.Series(np.nan, index=df.index)))
    df['fator_estrutura'] = (df['entropy_norm'] + df['choppiness_norm']) / 2

    # Expansão
    window_vol = 63
    df['vol_z'] = rolling_zscore(df.get('volatility_21', pd.Series(np.nan, index=df.index)), window=window_vol)

    df['range'] = df.get('high', pd.Series(np.nan, index=df.index)) - df.get('low', pd.Series(np.nan, index=df.index))
    df['atr']   = df['range'].rolling(14).mean()
    df['amplitude_relativa']   = df['range'] / (df['atr'] + 1e-6)
    df['amplitude_relativa_z'] = rolling_zscore(df['amplitude_relativa'].fillna(0), window=window_vol)

    vol21 = df.get('volatility_21', pd.Series(np.nan, index=df.index))
    df['vol_of_vol']   = vol21.rolling(21).std()
    df['vol_of_vol_z'] = rolling_zscore(df['vol_of_vol'], window=window_vol)

    mask_exp = df[['vol_z', 'amplitude_relativa_z', 'vol_of_vol_z']].notna().all(axis=1)
    exp_factor = np.full(len(df), np.nan)
    if mask_exp.sum() > 1:
        exp_factor[mask_exp.values] = PCA(n_components=1).fit_transform(
            df.loc[mask_exp, ['vol_z', 'amplitude_relativa_z', 'vol_of_vol_z']]
        ).ravel()
    df['fator_expansao'] = exp_factor

    # Liquidez
    df['volume_log']   = np.log(df.get('volume', pd.Series(np.nan, index=df.index)) + 1e-6)
    df['amihud_proxy'] = np.abs(df.get('daily_return', pd.Series(np.nan, index=df.index))) / (df['volume_log'] + 1e-6)
    df['amihud_z']     = rolling_zscore(df['amihud_proxy'].fillna(0), window=window_vol)
    df['fator_liquidez'] = df['amihud_z']

    log('Cálculo dos fatores concluído.')
    return df


# ---------------------------------------------------------------------------
# Etapa 2: Regimes rolantes
# ---------------------------------------------------------------------------

def calcular_regimes(
    fatores_smooth: pd.DataFrame,
    window_rolling: int = 360,
    n_components_pca: int = 2,
    n_regimes: int = 3,
) -> pd.DataFrame:
    log('Iniciando cálculo dos regimes rolantes...')
    n = len(fatores_smooth)
    rolling_labels = np.full(n, np.nan)
    rolling_pca1   = np.full(n, np.nan)
    rolling_pca2   = np.full(n, np.nan)

    for i in range(window_rolling, n):
        if (i - window_rolling) % 25 == 0:
            log(f'Processando janela {i}/{n}...')
        try:
            x_hist    = fatores_smooth.iloc[i - window_rolling:i].values
            log(f'Janela {i}: shape x_hist={x_hist.shape}, min={np.nanmin(x_hist):.4f}, max={np.nanmax(x_hist):.4f}')
            scaler    = StandardScaler()
            x_hist_sc = scaler.fit_transform(x_hist)

            pca        = PCA(n_components=n_components_pca)
            x_hist_pca = pca.fit_transform(x_hist_sc)

            gmm = GaussianMixture(n_components=n_regimes, covariance_type='full', random_state=42)
            gmm.fit(x_hist_pca)

            x_t     = fatores_smooth.iloc[i].values.reshape(1, -1)
            log(f'Janela {i}: x_t={x_t}')
            x_t_pca = pca.transform(scaler.transform(x_t))

            rolling_labels[i] = gmm.predict(x_t_pca)[0]
            rolling_pca1[i]   = x_t_pca[0, 0]
            rolling_pca2[i]   = x_t_pca[0, 1]
        except Exception as e:
            log(f'ERRO na janela {i}: {e}')
            log(f'Janela {i}: x_hist shape={x_hist.shape}, x_hist sample={x_hist[:3]}')
            continue

    labels_series = pd.Series(rolling_labels)
    labels_series = majority_filter(labels_series, window=5)
    labels_series = min_persistence_filter(labels_series, min_len=5)

    resultado = fatores_smooth.copy()
    resultado['regime_rolling'] = labels_series.values
    resultado['pca1_rolling']   = rolling_pca1
    resultado['pca2_rolling']   = rolling_pca2
    log('Cálculo dos regimes rolantes concluído.')
    return resultado


# ---------------------------------------------------------------------------
# Etapa 3: Montagem do resultado final
# ---------------------------------------------------------------------------

def montar_resultado(df: pd.DataFrame, fatores_regimes: pd.DataFrame) -> pd.DataFrame:
    log('Montando resultado final...')
    colunas_base     = ['date', 'open', 'high', 'low', 'close', 'volume', 'daily_return']
    colunas_features = ['hurst_72_returns', 'half_life_60', 'entropy_20', 'Choppiness_14', 'volatility_21']
    colunas_norm     = [
        'hurst_norm', 'half_life_norm', 'entropy_norm', 'choppiness_norm',
        'vol_z', 'amplitude_relativa', 'amplitude_relativa_z',
        'vol_of_vol', 'vol_of_vol_z', 'amihud_proxy', 'amihud_z',
    ]
    colunas_fatores = ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']
    colunas_regime  = ['regime_rolling', 'pca1_rolling', 'pca2_rolling']

    out = fatores_regimes.copy()

    for col in colunas_base + colunas_features:
        if col in df.columns:
            out[col] = df[col].reindex(out.index)

    if 'close' in df.columns:
        out['ret_futuro_10'] = df['close'].reindex(out.index).pct_change(10).shift(-10)
    elif 'ret_futuro_10' in df.columns:
        out['ret_futuro_10'] = df['ret_futuro_10'].reindex(out.index)

    todas = colunas_base + colunas_features + colunas_norm + colunas_fatores + colunas_regime
    if 'ret_futuro_10' in out.columns:
        todas.append('ret_futuro_10')

    cols = list(dict.fromkeys(c for c in todas if c in out.columns))
    log('Resultado final montado.')
    return out[cols]


# ---------------------------------------------------------------------------
# Worker — chamado pelos processos filhos.
#
# REGRA DE OURO: esta função só pode:
#   - ler um arquivo
#   - processar dados
#   - salvar um CSV
#   - retornar uma string
#
# NUNCA deve: criar Pool, Manager, Lock, fazer glob, ou chamar main().
# ---------------------------------------------------------------------------

def process_ativo(features_path: str) -> str:
    ativo = os.path.basename(features_path).replace('_features.parquet', '')
    output_path = (
        f'co-piloto-quant/src/co_piloto_quant/data/results/'
        f'structural_factors_{ativo}.csv'
    )
    try:
        log(f'Processando ativo: {ativo}')
        df             = pd.read_parquet(features_path)
        log('Arquivo lido com sucesso.')
        df             = calcular_fatores(df)
        fatores_cols   = ['fator_persistencia', 'fator_estrutura', 'fator_expansao', 'fator_liquidez']
        fatores_smooth = df[fatores_cols].rolling(60).mean().dropna().copy()
        log('Suavização dos fatores concluída.')

        if len(fatores_smooth) < 361:
            log(f'PULADO: {ativo}: apenas {len(fatores_smooth)} linhas após suavização')
            return f'PULADO:{ativo}:apenas {len(fatores_smooth)} linhas após suavização'

        fatores_regimes = calcular_regimes(fatores_smooth)
        resultado       = montar_resultado(df, fatores_regimes)
        resultado.to_csv(output_path)
        log(f'Resultado salvo em {output_path} ({len(resultado)} linhas)')
        return f'OK:{ativo}'

    except Exception as e:
        import traceback
        log(f'ERRO ao processar {ativo}: {e}')
        return f'ERRO:{ativo}:{e}\n{traceback.format_exc()}'


# ---------------------------------------------------------------------------
# Entry point — só roda no processo principal
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    features_dir = 'co-piloto-quant/src/co_piloto_quant/data/features'
    log_path     = 'co-piloto-quant/src/co_piloto_quant/data/results/ativos_processados.log'

    log('Buscando arquivos de features...')
    files = [
        f for f in glob.glob(os.path.join(features_dir, '*_features.parquet'))
        if f.endswith('.SA_features.parquet')
    ]

    log(f'Encontrados {len(files)} arquivos de ativos brasileiros.')
    if not files:
        log('Nenhum arquivo encontrado. Verifique o caminho.')
        raise SystemExit('Nenhum arquivo encontrado. Verifique o caminho.')

    n_cpus = max(1, mp.cpu_count() - 1)
    log(f'Iniciando pool com {n_cpus} processos...')

    # Log escrito SOMENTE aqui, no processo principal.
    # Sem Manager, sem Lock — sem risco de deadlock.
    with mp.Pool(n_cpus) as pool, open(log_path, 'a') as logf:
        for i, resultado in enumerate(pool.imap_unordered(process_ativo, files), 1):
            status, *resto = resultado.split(':', 1)

            if status == 'OK':
                logf.write(f'{resto[0]}\n')
                logf.flush()
                log(f'Ativo {resto[0]} processado com sucesso e registrado no log.')
            else:
                log(resultado)  # exibe PULADO ou ERRO com detalhes completos

            if i % 10 == 0 or i == len(files):
                log(f'{i}/{len(files)} ativos processados...')

    log('Processamento batch concluído.')