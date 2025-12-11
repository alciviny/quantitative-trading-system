"""
Módulo para a gestão centralizada de nomes de colunas de indicadores.
"""
from typing import Union

class IndicatorNames:
    """
    Classe estática para gerar nomes de colunas padronizados para indicadores.

    O objetivo é garantir que o nome de uma coluna gerado pelo IndicatorEngine
    seja exatamente o mesmo nome procurado pelas estratégias, eliminando
    erros causados por strings de texto hardcoded e divergentes.

    O padrão é snake_case.
    """

    @staticmethod
    def bollinger_bands(period: int, std_dev: float, band_type: str) -> str:
        """Nome genérico para uma banda de Bollinger."""
        if band_type not in ['upper', 'middle', 'lower']:
            raise ValueError("band_type deve ser 'upper', 'middle', ou 'lower'")
        if band_type == 'middle':
            return f"bb_middle_{period}"
        # Garante que o desvio padrão seja formatado com ponto, ex: '2.0'
        std_dev_str = str(float(std_dev))
        return f"bb_{band_type}_{period}_{std_dev_str}"

    @staticmethod
    def bollinger_upper(period: int, std_dev: float) -> str:
        """Nome para a banda superior de Bollinger."""
        return IndicatorNames.bollinger_bands(period, std_dev, 'upper')

    @staticmethod
    def bollinger_lower(period: int, std_dev: float) -> str:
        """Nome para a banda inferior de Bollinger."""
        return IndicatorNames.bollinger_bands(period, std_dev, 'lower')

    @staticmethod
    def bollinger_middle(period: int) -> str:
        """Nome para a banda central de Bollinger."""
        return IndicatorNames.bollinger_bands(period, 0, 'middle')

    @staticmethod
    def rsi(period: int) -> str:
        """Nome para o IFR (Índice de Força Relativa)."""
        return f"rsi_{period}"

    @staticmethod
    def stochastic_k(k_period: int, k_smooth: int) -> str:
        """Nome para a linha %K do Estocástico."""
        return f"stoch_k_{k_period}_{k_smooth}"

    @staticmethod
    def stochastic_d(k_period: int, k_smooth: int, d_smooth: int) -> str:
        """Nome para a linha %D do Estocástico."""
        return f"stoch_d_{k_period}_{k_smooth}_{d_smooth}"

    @staticmethod
    def log_return() -> str:
        """Nome para a coluna de retorno logarítmico."""
        return "log_return"

    @staticmethod
    def volatility(window: int) -> str:
        """Nome para a volatilidade."""
        return f"volatility_{window}"

    @staticmethod
    def kalman_band(period: int, dev: Union[float, int], band_type: str) -> str:
        """Nome genérico para as bandas de Kalman."""
        if band_type not in ['upper', 'lower']:
            raise ValueError("band_type para Kalman deve ser 'upper' ou 'lower'")
        dev_str = str(float(dev))
        return f"kalman_{band_type}_{period}_{dev_str}"
    
    @staticmethod
    def kalman_upper(period: int, dev: Union[float, int]) -> str:
        """Nome para a banda superior de Kalman."""
        return IndicatorNames.kalman_band(period, dev, 'upper')

    @staticmethod
    def kalman_lower(period: int, dev: Union[float, int]) -> str:
        """Nome para a banda inferior de Kalman."""
        return IndicatorNames.kalman_band(period, dev, 'lower')

    @staticmethod
    def wwma(period: int) -> str:
        """Nome para a Média Móvel de Wilder (Wilder's Moving Average)."""
        return f"wwma_{period}"

    @staticmethod
    def entropy(window: int) -> str:
        """Nome para a entropia."""
        return f"entropy_{window}"

    @staticmethod
    def entropy_z(window: int) -> str:
        """Nome para o Z-Score da entropia."""
        return f"entropy_z_{window}"

    @staticmethod
    def hurst(window: int, kind: str = 'c') -> str:
        """Nome para o expoente de Hurst."""
        return f"hurst_{window}_{kind}"

    @staticmethod
    def hurst_z(window: int, kind: str = 'c') -> str:
        """Nome para o Z-Score do expoente de Hurst."""
        return f"hurst_z_{window}_{kind}"
        
    @staticmethod
    def half_life(window: int) -> str:
        """Nome para a Meia-Vida da reversão à média."""
        return f"half_life_{window}"
        
    # --- Nomes para o System TPM ---
    @staticmethod
    def obtr() -> str:
        """On Balance True Range."""
        return "obtr"

    @staticmethod
    def wad() -> str:
        """Williams Accumulation/Distribution."""
        return "wad"

    @staticmethod
    def tpm_band(indicator_name: str, period: int, band_type: str, deviation: float = None) -> str:
        """Nome genérico para as bandas do System TPM."""
        if band_type not in ['upper', 'middle', 'lower']:
            raise ValueError("band_type deve ser 'upper', 'middle', ou 'lower'")
        
        base_name = f"{indicator_name}_{period}"
        
        if band_type == 'middle':
            return f"{base_name}_middle"
        
        if deviation is None:
            raise ValueError("O parâmetro 'deviation' é obrigatório para as bandas 'upper' e 'lower'")
            
        dev_str = str(float(deviation))
        return f"{base_name}_{band_type}_{dev_str}"