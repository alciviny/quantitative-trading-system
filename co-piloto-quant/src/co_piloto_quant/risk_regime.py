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
    Agora com dupla camada de proteção: VolVol (Estabilidade) e Raw Vol (Turbulência).
    Retorna: dict: {'approved': bool, 'reason': str}
    """
    # 1. Proteção contra DataFrame vazio ou pequeno
    if df_indicators.empty or len(df_indicators) < 22: # Aumentado para segurança dos cálculos
        return {'approved': False, 'reason': 'Dados insuficientes'}

    close_prices = df_indicators['close']
    returns = close_prices.pct_change()

    # --- VACINA 1: ANTI-CRASH (INSTABILIDADE ESTRUTURAL) ---
    vol_vol = calculate_vol_of_vol(close_prices)
    LIMIT_VOL_VOL = 0.030  # Limite ajustado
    
    if vol_vol > LIMIT_VOL_VOL: 
        return {
            'approved': False, 
            'reason': f'CRASH ALERT: Volatilidade Instável ({vol_vol:.3f} > {LIMIT_VOL_VOL})'
        }

    # --- VACINA 2: ANTI-TURBULÊNCIA (RUÍDO EXCESSIVO) ---
    current_vol = returns.rolling(20).std().iloc[-1]
    LIMIT_RAW_VOL = 0.035 # Limite de 3.5% de vol diária

    if current_vol > LIMIT_RAW_VOL:
        return {
            'approved': False,
            'reason': f'TURBULÊNCIA: Volatilidade Recente Alta ({current_vol:.3f} > {LIMIT_RAW_VOL})'
        }

    # 3. FILTRO DE ENTROPIA (O "Anti-Ruído")
    last_row = df_indicators.iloc[-1]
    
    if 'Entropy_20' in last_row and not pd.isna(last_row['Entropy_20']):
        entropy = last_row['Entropy_20']
        LIMIT_ENTROPY = 3.2 
        
        if entropy > LIMIT_ENTROPY:
             return {
                 'approved': False, 
                 'reason': f'Caos Extremo: Entropia Alta ({entropy:.2f} > {LIMIT_ENTROPY})'
             }

    # Se passou por tudo:
    return {'approved': True, 'reason': 'Regime Seguro'}