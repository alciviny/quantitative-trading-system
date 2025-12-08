import MetaTrader5 as mt5
import pandas as pd
from typing import Dict, Optional, Any

from co_piloto_quant.data.interface import MarketDataProvider

class MT5ConnectionError(Exception):
    """Exceção customizada para falhas de conexão com o MT5."""
    pass

class MT5DataProvider(MarketDataProvider):
    """
    Implementação de um provedor de dados de mercado que se conecta ao MetaTrader 5.
    """
    
    # Mapeamento de strings de timeframe para o formato do MT5
    TIMEFRAME_MAP: Dict[str, int] = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1
    }

    _EMPTY_DF = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']).set_index(pd.to_datetime([]))

    def __init__(self):
        """Inicializa o provedor e estabelece conexão com o MetaTrader 5."""
        try:
            if not mt5.initialize():
                last_error = mt5.last_error()
                raise MT5ConnectionError(f"Falha ao inicializar MT5: {last_error}")
            
            account_info = mt5.account_info()
            if not account_info:
                raise MT5ConnectionError("Não foi possível obter informações da conta. Verifique o login.")
            
            print(f"✅ [MT5DataProvider] Conectado com sucesso à conta: {account_info.login}")
            self.metadata = {
                "provider_name": self.__class__.__name__,
                "account_login": account_info.login,
                "server": account_info.server,
            }

        except Exception as e:
            print(f"❌ [MT5DataProvider] Erro durante a inicialização: {e}")
            raise

    def get_data(self, symbol: str, timeframe_str: str, limit: int) -> pd.DataFrame:
        """
        Busca dados do MT5 e os normaliza para o formato padrão.
        """
        mt5_timeframe = self.TIMEFRAME_MAP.get(timeframe_str.upper())
        if mt5_timeframe is None:
            raise ValueError(f"Timeframe '{timeframe_str}' não é suportado pelo MT5Adapter.")

        # Garante que o símbolo está visível no Market Watch para obter os dados
        mt5.symbol_select(symbol, True)

        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, limit)
        
        if rates is None or len(rates) == 0:
            print(f"⚠️ [MT5DataProvider] Nenhum dado retornado para {symbol} no timeframe {timeframe_str}.")
            return self._EMPTY_DF.copy()

        df = pd.DataFrame(rates)

        # Padronização do Index
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)

        # Padronização de Colunas (o ponto central do Adapter)
        column_map = {
            'tick_volume': 'volume', # Principal coluna a ser normalizada
            'real_volume': 'volume', # Fallback se 'real_volume' existir
        }
        df.rename(columns=column_map, inplace=True)

        # Garante que as colunas obrigatórias existam, preenchendo com 0 se necessário
        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col not in df.columns:
                df[col] = 0.0
        
        # Retorna apenas as colunas do contrato, na ordem correta
        return df[['open', 'high', 'low', 'close', 'volume']]

    def close(self):
        """Encerra a conexão com o MetaTrader 5."""
        print("🔌 [MT5DataProvider] Encerrando conexão com o MT5.")
        mt5.shutdown()

    def get_metadata(self) -> Dict[str, any]:
        return self.metadata

    def get_filling_mode(self, symbol: str) -> Optional[int]:
        s_info = mt5.symbol_info(symbol)
        if not s_info: return None
        if s_info.filling_mode & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
        return mt5.ORDER_FILLING_FOK
    
    def get_symbol_info_tick(self, symbol: str) -> Optional[Any]:
        return mt5.symbol_info_tick(symbol)
    
    def get_symbol_info(self, symbol: str) -> Optional[mt5.SymbolInfo]:
        return mt5.symbol_info(symbol)
