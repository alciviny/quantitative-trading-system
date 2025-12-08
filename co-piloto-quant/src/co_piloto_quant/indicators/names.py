from typing import Union

class IndicatorNames:
    """
    Centralized registry for indicator column names.
    This class provides static methods to generate consistent names for indicator
    columns across the entire application, from calculation to strategy consumption.
    Using this class prevents "Magic Strings" and ensures that if a naming
    convention changes, it only needs to be updated in one place.
    """

    @staticmethod
    def bollinger_upper(period: int, std_dev: Union[float, int]) -> str:
        """Generates the name for the Bollinger Bands Upper Band column."""
        return f"BB_Upper_{period}_{std_dev}"

    @staticmethod
    def bollinger_lower(period: int, std_dev: Union[float, int]) -> str:
        """Generates the name for the Bollinger Bands Lower Band column."""
        return f"BB_Lower_{period}_{std_dev}"

    @staticmethod
    def bollinger_middle(period: int) -> str:
        """Generates the name for the Bollinger Bands Middle Band column."""
        return f"BB_Middle_{period}"

    @staticmethod
    def stochastic_k(k_period: int, k_smooth: int) -> str:
        """Generates the name for the Stochastic %K line."""
        return f"stoch_k_{k_period}_{k_smooth}"

    @staticmethod
    def stochastic_d(k_period: int, k_smooth: int, d_smooth: int) -> str:
        """Generates the name for the Stochastic %D line."""
        return f"stoch_d_{k_period}_{k_smooth}_{d_smooth}"
    
    @staticmethod
    def wwma(period: int) -> str:
        """Generates the name for the Wilder's Moving Average."""
        return f"WWMA_{period}"

    @staticmethod
    def entropy(window: int) -> str:
        """Generates the name for the rolling entropy column."""
        return f"Entropy_{window}"

    @staticmethod
    def entropy_z(window: int) -> str:
        """Generates the name for the Z-Score of rolling entropy."""
        return "Entropy_Z"

    @staticmethod
    def hurst(window: int, kind: str) -> str:
        """Generates the name for the Hurst exponent column."""
        return f"Hurst_{window}_{kind}"
        
    @staticmethod
    def hurst_z() -> str:
        """Generates the name for the Z-Score of the Hurst exponent."""
        # The original code hardcoded the source column as 'Hurst_72_returns'
        # We will keep the Z-score name simple for now.
        return "Hurst_Z"

    @staticmethod
    def vol_of_vol(window: int) -> str:
        """Generates the name for the Volatility of Volatility column."""
        return f"VolVol_{window}"

    @staticmethod
    def vol_of_vol_z() -> str:
        """Generates the name for the Z-Score of Volatility of Volatility."""
        return "VolVol_Z"

    # -- System TPM --
    @staticmethod
    def tpm_band(indicator: str, band_type: str) -> str:
        """
        Generates names for System TPM bands (e.g., 'obtr_bb_middle_band').
        
        Args:
            indicator (str): 'obtr' or 'wad'.
            band_type (str): 'upper_band', 'middle_band', 'lower_band'.
        """
        return f"{indicator}_bb_{band_type}"

