import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# --- Importação Segura do MAD ---
try:
    from scipy.stats import median_abs_deviation
except ImportError:
    try:
        from scipy.stats import median_absolute_deviation as median_abs_deviation
    except ImportError:
        median_abs_deviation = None

def calculate_vol_of_vol(price_series: pd.Series, window: int = 20) -> float:
    # (Mantém a mesma lógica de cálculo de VolVol que já funciona bem)
    try:
        if len(price_series) < window + 2: return 0.0
        returns = price_series.pct_change().dropna()
        vol = returns.rolling(window).std().dropna()
        if len(vol) < 2: return 0.0
        vol_diff = vol.diff().dropna()
        if median_abs_deviation:
            mad = median_abs_deviation(vol_diff, scale='normal')
        else:
            mad = np.median(np.abs(vol_diff - np.median(vol_diff)))
        return float(mad) if not np.isnan(mad) else 0.0
    except Exception:
        return 0.0

def validate_market_regime(df_indicators: pd.DataFrame) -> dict:
    """
    Sistema Híbrido de Validação de Risco:
    Combina Limites Absolutos (do Detect Toxicity) + Limites Relativos (Z-Score).
    """
    if df_indicators.empty or len(df_indicators) < 200:
        if len(df_indicators) > 50:
             return {'approved': True, 'reason': 'Modo Aprendizado (Dados < 200)'}
        return {'approved': False, 'reason': 'Dados insuficientes'}

    latest = df_indicators.iloc[-1]

    # --- CAMADA 1: LIMITES ABSOLUTOS (A "Herança" do seu Detect Toxicity) ---
    # Esses números vêm da sua pesquisa forense anterior. São o "Teto de Vidro".
    
    # Regra Forense 1: Entropia > 3.2 é tóxica
    if 'Entropy_20' in latest and latest['Entropy_20'] > 3.2:
        return {'approved': False, 'reason': f'TETO ABSOLUTO: Entropia Tóxica ({latest["Entropy_20"]:.2f} > 3.2)'}

    # Regra Forense 2: Volatilidade Pura > 3.5% ao dia é perigoso
    returns = df_indicators['close'].pct_change()
    current_vol = returns.rolling(20).std().iloc[-1]
    if current_vol > 0.035:
        return {'approved': False, 'reason': f'TETO ABSOLUTO: Volatilidade Alta ({current_vol:.1%})'}


    # --- CAMADA 2: LIMITES RELATIVOS (A Inteligência Z-Score) ---
    # Esses pegam mudanças de comportamento ANTES de bater no teto.
    
    # Regra Quant 1: VolVol Z-Score (Instabilidade súbita)
    if 'VolVol_Z' in latest and latest['VolVol_Z'] > 3.0:
        return {'approved': False, 'reason': f'ANOMALIA: Instabilidade Extrema (Z: {latest["VolVol_Z"]:.1f}σ)'}

    # Regra Quant 2: Entropia Z-Score (Ativo ficando "estranho" para o padrão dele)
    # Note que aqui somos mais flexíveis (2.0 sigmas) porque já temos o teto de 3.2
    if 'Entropy_Z' in latest and latest['Entropy_Z'] > 2.0:
        return {'approved': False, 'reason': f'ANOMALIA: Comportamento Anômalo (Z: {latest["Entropy_Z"]:.1f}σ)'}

    return {'approved': True, 'reason': 'Seguro (Híbrido)'}
