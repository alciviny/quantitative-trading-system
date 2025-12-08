from abc import ABC, abstractmethod
import pandas as pd
from typing import Dict, Any

class MarketDataProvider(ABC):
    """
    Interface abstrata para um provedor de dados de mercado.
    
    Define um contrato que todas as fontes de dados (MT5, Yahoo Finance, Binance, etc.)
    devem seguir para fornecer dados de forma consistente para o sistema de trading.
    """

    @abstractmethod
    def get_data(self, symbol: str, timeframe_str: str, limit: int) -> pd.DataFrame:
        """
        Busca dados históricos de mercado para um determinado símbolo e timeframe.

        Args:
            symbol (str): O ticker ou símbolo do ativo.
            timeframe_str (str): A representação em string do timeframe (ex: "M15", "H1", "D1").
            limit (int): O número de barras/velas a serem retornadas.

        Returns:
            pd.DataFrame: Um DataFrame padronizado contendo os dados OHLCV.
                          O DataFrame DEVE:
                          1. Ter um índice do tipo pd.DatetimeIndex.
                          2. Conter as colunas OBRIGATÓRIAS, todas em minúsculas:
                             ['open', 'high', 'low', 'close', 'volume'].
                          
                          Se não for possível obter os dados, deve retornar um
                          DataFrame vazio com as colunas esperadas.
        """
        pass

    def get_metadata(self) -> Dict[str, Any]:
        """
        Retorna metadados sobre o provedor de dados. Opcional.
        """
        return {"provider_name": self.__class__.__name__}
