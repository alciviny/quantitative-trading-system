import pandas as pd
import numpy as np
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# --- Importação Segura do MAD ---
try:
    from scipy.stats import median_abs_deviation
except ImportError:
    try:
        from scipy.stats import median_absolute_deviation as median_abs_deviation
    except ImportError:
        median_abs_deviation = None

@dataclass
class ValidationResult:
    approved: bool
    reason: str

def _calculate_vol_of_vol(price_series: pd.Series, window: int = 20) -> float:
    """
    Calcula a Volatilidade da Volatilidade (VolVol) de uma série de preços.
    Utilizada internamente pelo RiskRegimeManager.
    """
    try:
        if len(price_series) < window + 2: 
            return 0.0
        returns = price_series.pct_change().dropna()
        if len(returns) < window: # Adicionado para evitar erro em rolling
            return 0.0
        vol = returns.rolling(window).std().dropna()
        if len(vol) < 2: 
            return 0.0
        vol_diff = vol.diff().dropna()
        if median_abs_deviation:
            mad = median_abs_deviation(vol_diff, scale='normal')
        else:
            # Fallback manual para MAD se scipy.stats não estiver disponível
            mad = np.median(np.abs(vol_diff - np.median(vol_diff)))
        return float(mad) if not np.isnan(mad) else 0.0
    except Exception as e:
        logger.error(f"Erro ao calcular VolVol: {e}", exc_info=True)
        return 0.0

class RiskRegimeManager:
    """
    Gerencia a validação do regime de mercado para determinar se as operações de trading são permitidas.
    Implementa um sistema híbrido de limites absolutos e relativos (Z-Score).
    """

    def __init__(self):
        logger.info("RiskRegimeManager inicializado.")

    def validate_market_regime(self, df_indicators: pd.DataFrame) -> ValidationResult:
        """
        Sistema Híbrido de Validação de Risco:
        Combina Limites Absolutos (do Detect Toxicity) + Limites Relativos (Z-Score).

        Args:
            df_indicators: DataFrame contendo os indicadores necessários para a validação.
                           Deve incluir 'Entropy_20', 'VolVol_Z', 'Entropy_Z' e 'close'.

        Returns:
            Um objeto ValidationResult indicando se o regime é aprovado e a razão.
        """
        if df_indicators.empty or len(df_indicators) < 200:
            if len(df_indicators) > 50:
                 return ValidationResult(approved=True, reason='Modo Aprendizado (Dados < 200)')
            return ValidationResult(approved=False, reason='Dados insuficientes para validação de regime.')

        latest = df_indicators.iloc[-1]

        # --- CAMADA 1: LIMITES ABSOLUTOS (A "Herança" do seu Detect Toxicity) ---
        # Esses números vêm da sua pesquisa forense anterior. São o "Teto de Vidro".
        
        # Regra Forense 1: Entropia > 3.2 é tóxica
        if 'Entropy_20' in latest and latest['Entropy_20'] > 3.2:
            return ValidationResult(approved=False, reason=f'TETO ABSOLUTO: Entropia Tóxica ({latest["Entropy_20"]:.2f} > 3.2)')

        # Regra Forense 2: Volatilidade Pura > 3.5% ao dia é perigoso
        # Garante que 'close' exista e tenha dados suficientes
        if 'close' in df_indicators.columns:
            returns = df_indicators['close'].pct_change().dropna()
            # Garante que há dados suficientes para calcular rolling std de 20 períodos
            if len(returns) >= 20: 
                current_vol = returns.rolling(20).std().iloc[-1]
                if current_vol > 0.035:
                    return ValidationResult(approved=False, reason=f'TETO ABSOLUTO: Volatilidade Alta ({current_vol:.1%})')
            else:
                logger.warning("Dados insuficientes para calcular volatilidade (menos de 20 retornos).")
        else:
            logger.warning("Coluna 'close' ausente para calcular volatilidade diária.")


        # --- CAMADA 2: LIMITES RELATIVOS (A Inteligência Z-Score) ---
        # Esses pegam mudanças de comportamento ANTES de bater no teto.
        
        # Regra Quant 1: VolVol Z-Score (Instabilidade súbita)
        if 'VolVol_Z' in latest and latest['VolVol_Z'] > 3.0:
            return ValidationResult(approved=False, reason=f'ANOMALIA: Instabilidade Extrema (Z: {latest["VolVol_Z"]:.1f}σ)')

        # Regra Quant 2: Entropia Z-Score (Ativo ficando "estranho" para o padrão dele)
        # Note que aqui somos mais flexíveis (2.0 sigmas) porque já temos o teto de 3.2
        if 'Entropy_Z' in latest and latest['Entropy_Z'] > 2.0:
            return ValidationResult(approved=False, reason=f'ANOMALIA: Comportamento Anômalo (Z: {latest["Entropy_Z"]:.1f}σ)')

        return ValidationResult(approved=True, reason='Regime de mercado aprovado (Híbrido).')

