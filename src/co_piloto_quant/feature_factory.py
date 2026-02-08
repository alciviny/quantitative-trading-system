# src/co_piloto_quant/feature_factory.py
"""
Módulo Central para Engenharia de Features.

Este módulo, a "Fábrica de Features", consolida todos os cálculos de indicadores
e transformações de dados em um único lugar. O objetivo é criar um processo
unificado e extensível para enriquecer os dados brutos de mercado.

A função principal `add_all_features` orquestra a aplicação de todas as features.
Para adicionar um novo indicador, basta criar uma função correspondente e chamá-la
dentro de `add_all_features`.
"""
import pandas as pd
import numpy as np

# Importações de Indicadores do próprio sistema
from .data.indicator_engine import IndicatorEngine
from .indicators.special.frac_diff import fractional_diff_fixed_window
from .indicators.special.hurst_exponent import calculate_rolling_hurst
from .indicators.special.market_entropy import calculate_rolling_entropy
from .indicators.special.half_life import calculate_rolling_ou_params
from .indicators.special.fractal_dimension import calculate_rolling_fdi
from .indicators.special.lempel_ziv import calculate_rolling_lzc
from .indicators.vwap_annual import AnnualVWAPAnalyst
from .utils.math_tools import calculate_z_score

# =============================================================================
# Normalização e Targets (Funções Auxiliares)
# =============================================================================

def _rolling_normalize(series: pd.Series, window: int = 252) -> pd.Series:
    """Normaliza uma série em uma janela móvel para o range [0, 1]."""
    def _norm(x):
        xmin, xmax = np.min(x), np.max(x)
        if xmax == xmin:
            return 0.5
        return (x.iloc[-1] - xmin) / (xmax - xmin + 1e-9)

    return series.rolling(window, min_periods=window).apply(_norm, raw=False)

def add_forward_return_targets(df: pd.DataFrame, horizons: list = [5, 10, 20]) -> pd.DataFrame:
    """Adiciona colunas de retorno futuro para ML (com cuidado para evitar lookahead)."""
    for horizon in horizons:
        future_close = df['close'].shift(-horizon)
        df[f'target_ret_{horizon}d'] = (future_close - df['close']) / df['close']
    return df

# =============================================================================
# "Famílias" de Indicadores
# =============================================================================

def add_base_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona indicadores técnicos básicos usando o IndicatorEngine."""
    engine = IndicatorEngine(df)
    engine.add_indicator('bollinger_bands', period=20, std_devs=[2.0])
    engine.add_indicator('ifr', period=14)
    engine.add_indicator('stochastic', k_period=14, k_smooth=3, d_smooth=3)
    engine.add_indicator('ema', period=50)
    engine.add_indicator('ema', period=200)
    return engine.get_data()

def add_market_physics_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona indicadores de "física de mercado" (Hurst, Entropia, etc.)."""
    df['hurst_72_returns'] = calculate_rolling_hurst(df['close'], window=72, kind='returns')
    df['entropy_20'] = calculate_rolling_entropy(df['close'], window=20)
    
    # Half-Life
    ou_df = calculate_rolling_ou_params(df['close'], window=60, strict_mode=False)
    if 'half_life_60' in ou_df.columns:
        df['half_life_60'] = ou_df['half_life_60']

    # Complexidade e Fratalidade
    df['fdi_30'] = calculate_rolling_fdi(df["close"], 30)
    df['lzc_50'] = calculate_rolling_lzc(df["close"], 50)
    return df

def add_volatility_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona indicadores de volatilidade, incluindo vol-of-vol."""
    df['vol_20'] = df['close'].pct_change().rolling(20).std()
    df['vol_of_vol_20'] = df['vol_20'].rolling(20).std()
    return df

def add_stationarity_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona features de estacionariedade como diferenciação fracionária."""
    df['close_frac_diff_0.4'] = fractional_diff_fixed_window(df['close'], d=0.4, window=50)
    return df
    
def add_vwap_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona features baseadas no VWAP Anual."""
    # O AnnualVWAPAnalyst precisa de um DataFrame com colunas de nomes específicos.
    # Garantimos que as colunas existam e estejam com a primeira letra maiúscula.
    df_vwap = df.copy()
    rename_map = {c: c.capitalize() for c in ['open', 'high', 'low', 'close', 'volume'] if c in df_vwap.columns}
    df_vwap = df_vwap.rename(columns=rename_map)
    
    if 'Date' not in df_vwap.columns:
         df_vwap.reset_index(inplace=True)
         df_vwap = df_vwap.rename(columns={'index': 'Date', 'data_pregao': 'Date'})

    if not all(col in df_vwap.columns for col in ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']):
        print("Aviso: Colunas necessárias para o VWAP Anual não encontradas. Pulando cálculo.")
        return df

    analyst = AnnualVWAPAnalyst(price_col="Close")
    df_vwap_calcd = analyst.calculate(df_vwap)
    
    # Junta os resultados de volta ao DataFrame original
    df['vwap_z_score'] = df_vwap_calcd['vwap_z_score'].values
    df['vwap_dist_pct'] = df_vwap_calcd['vwap_dist_pct'].values
    return df

def add_regime_and_zscore_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona Z-Scores e o score de regime consolidado."""
    # Z-Scores
    if 'hurst_72_returns' in df.columns:
        df['hurst_z_score'] = calculate_z_score(df['hurst_72_returns'])
    if 'entropy_20' in df.columns:
        df['entropy_z_score'] = calculate_z_score(df['entropy_20'])
    if 'vol_of_vol_20' in df.columns:
        df['vol_of_vol_z_score'] = calculate_z_score(df['vol_of_vol_20'])

    # Regime Score (baseado no script regime_market.py)
    df["fdi_norm"] = 1.0 - _rolling_normalize(df["fdi_30"])
    df["entropy_norm"] = 1.0 - _rolling_normalize(df["entropy_20"])
    df["lzc_norm"] = 1.0 - _rolling_normalize(df["lzc_50"])
    # Reutiliza o Hurst já calculado, mas com window de 100 para o score
    hurst_100 = calculate_rolling_hurst(df['close'], window=100)
    df["hurst_norm"] = _rolling_normalize(hurst_100)

    df["regime_score"] = (
        0.30 * df["fdi_norm"] +
        0.25 * df["entropy_norm"] +
        0.25 * df["lzc_norm"] +
        0.20 * df["hurst_norm"]
    ).fillna(0) * 100.0

    df["regime_state"] = pd.cut(
        df["regime_score"],
        bins=[0, 20, 40, 60, 80, 101],
        labels=["toxic", "chop", "neutral", "trend", "clean_trend"],
        right=True
    )
    return df

# =============================================================================
# Orquestrador Principal da Fábrica
# =============================================================================

def add_all_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Orquestra a aplicação de todas as famílias de indicadores e features.
    
    Args:
        df (pd.DataFrame): DataFrame com dados de mercado brutos (OHLCV).

    Returns:
        pd.DataFrame: DataFrame enriquecido com todas as features calculadas.
    """
    if df.empty:
        return df

    # Garante que as colunas estejam em minúsculo para consistência
    df.columns = [col.lower() for col in df.columns]

    df = (df
          .pipe(add_base_technical_indicators)
          .pipe(add_market_physics_indicators)
          .pipe(add_volatility_indicators)
          .pipe(add_stationarity_indicators)
          .pipe(add_vwap_indicators)
          .pipe(add_regime_and_zscore_indicators)
          .pipe(add_forward_return_targets)
         )
         
    # Arredonda colunas float para 5 casas decimais para otimizar armazenamento
    for col in df.select_dtypes(include=['float64']).columns:
        df[col] = df[col].round(5)

    return df
