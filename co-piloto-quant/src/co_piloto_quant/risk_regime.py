import pandas as pd
import numpy as np
import logging

# Configura o logger
logger = logging.getLogger(__name__)

# --- Importação Segura do MAD (Compatibilidade entre versões do Scipy) ---
try:
    from scipy.stats import median_abs_deviation
except ImportError:
    try:
        from scipy.stats import median_absolute_deviation as median_abs_deviation
    except ImportError:
        median_abs_deviation = None

def calculate_vol_of_vol(price_series: pd.Series, window: int = 20) -> float:
    """
    Calcula a Volatilidade da Volatilidade (Medo de 2ª ordem).
    Cópia utilitária para evitar dependência circular com o script de forensics.
    """
    try:
        if len(price_series) < window + 2:
            return 0.0
            
        returns = price_series.pct_change().dropna()
        vol = returns.rolling(window).std().dropna()
        
        if len(vol) < 2:
            return 0.0
            
        vol_diff = vol.diff().dropna()
        
        # Cálculo robusto usando MAD
        if median_abs_deviation:
            mad = median_abs_deviation(vol_diff, scale='normal')
        else:
            # Fallback manual se scipy falhar
            mad = np.median(np.abs(vol_diff - np.median(vol_diff)))
            
        return float(mad) if not np.isnan(mad) else 0.0
    except Exception as e:
        logger.warning(f"Erro ao calcular VolVol: {e}")
        return 0.0

def validate_market_regime(df_indicators: pd.DataFrame) -> dict:
    """
    Aplica os filtros de segurança descobertos pela análise forense (SHAP).
    
    Retorna:
        dict: {'approved': bool, 'reason': str}
    """
    # Proteção contra DataFrame vazio
    if df_indicators.empty or len(df_indicators) < 20:
        return {'approved': False, 'reason': 'Dados insuficientes'}

    last_row = df_indicators.iloc[-1]
    
    # -----------------------------------------------------------
    # 1. FILTRO DE VOLATILIDADE DA VOLATILIDADE (O "Anti-Crash")
    # -----------------------------------------------------------
    # Se o Forensic Tool indicou que VolVol > 0.045 causa falha:
    vol_vol = calculate_vol_of_vol(df_indicators['close'])
    
    # AJUSTE ESTE VALOR COM BASE NO SEU RESULTADO DO FORENSIC TOOL
    LIMIT_VOL_VOL = 0.045 
    
    if vol_vol > LIMIT_VOL_VOL: 
        return {
            'approved': False, 
            'reason': f'Risco de Crash: Vol-of-Vol Alta ({vol_vol:.3f} > {LIMIT_VOL_VOL})'
        }

    # -----------------------------------------------------------
    # 2. FILTRO DE ENTROPIA (O "Anti-Ruído")
    # -----------------------------------------------------------
    # Verifica se a coluna existe antes de testar
    if 'Entropy_20' in last_row:
        entropy = last_row['Entropy_20']
        # AJUSTE ESTE VALOR COM BASE NO SEU RESULTADO DO FORENSIC TOOL
        LIMIT_ENTROPY = 3.15 
        
        if entropy > LIMIT_ENTROPY:
            return {
                'approved': False, 
                'reason': f'Mercado Caótico: Entropia Alta ({entropy:.2f} > {LIMIT_ENTROPY})'
            }

    # Se passou por tudo:
    return {'approved': True, 'reason': 'Regime Seguro'}