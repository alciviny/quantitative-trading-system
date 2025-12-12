import MetaTrader5 as mt5
import pandas as pd
import time
import threading
import logging
import random
from typing import Dict, Optional, Any

from co_piloto_quant.data.interface import MarketDataProvider

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MT5ConnectionError(Exception):
    """Exceção customizada para falhas de conexão com o MT5."""
    pass

class MT5DataProvider(MarketDataProvider):
    """
    Implementação de um provedor de dados de mercado que se conecta ao MetaTrader 5.
    Esta classe é um Singleton para garantir uma única conexão com o MT5.
    """
    _instance = None
    _is_connected = False
    _heartbeat_thread: Optional[threading.Thread] = None
    _stop_heartbeat = threading.Event()
    
    # Mapeamento de strings de timeframe para o formato do MT5
    TIMEFRAME_MAP: Dict[str, int] = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
        "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1
    }

    _EMPTY_DF = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume']).set_index(pd.to_datetime([]))

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializa o provedor e estabelece conexão com o MetaTrader 5."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.metadata: Dict[str, Any] = {}
            self._connect_mt5()
            
            if self._is_connected:
                self._stop_heartbeat.clear()
                self._heartbeat_thread = threading.Thread(target=self._run_heartbeat, daemon=True)
                self._heartbeat_thread.start()

    def _connect_mt5(self) -> None:
        """Tenta conectar ou reconectar ao MetaTrader 5."""
        if self._is_connected:
            logger.info("Já conectado ao MT5.")
            return

        try:
            # Força a re-inicialização caso a conexão tenha sido perdida
            if mt5.is_initialized():
                mt5.shutdown()
                logger.info("MT5 foi desligado antes da tentativa de re-inicialização.")

            if not mt5.initialize():
                last_error = mt5.last_error()
                raise MT5ConnectionError(f"Falha ao inicializar MT5: {last_error}")
            
            account_info = mt5.account_info()
            if not account_info:
                raise MT5ConnectionError("Não foi possível obter informações da conta. Verifique o login.")
            
            self.metadata = {
                "provider_name": self.__class__.__name__,
                "account_login": account_info.login,
                "server": account_info.server,
            }
            self._is_connected = True
            logger.info(f"✅ [MT5DataProvider] Conectado com sucesso à conta: {account_info.login} (Server: {account_info.server})")

        except Exception as e:
            self._is_connected = False
            logger.error(f"❌ [MT5DataProvider] Erro durante a conexão/inicialização: {e}", exc_info=True)
            # Não relança a exceção aqui para permitir o fluxo de reconexão

    def _check_connection(self) -> bool:
        """Verifica se a conexão com o MT5 está ativa de forma mais robusta."""
        if not self._is_connected:
            return False
        
        try:
            # Tenta uma operação que requer comunicação ativa com o terminal
            # Por exemplo, obter um tick para um símbolo comum, ou a informação da conta.
            # O terminal_info() pode ser um pouco passivo.
            account_info = mt5.account_info()
            if not account_info:
                logger.warning("Não foi possível obter informações da conta MT5. Conexão pode ter caído.")
                self._is_connected = False
                return False
            
            # Uma checagem mais ativa seria tentar obter um tick
            # if not mt5.symbol_info_tick("EURUSD"): # Assumindo um símbolo padrão
            #     logger.warning("Não foi possível obter tick para EURUSD. Conexão pode ter caído.")
            #     self._is_connected = False
            #     return False

            return True
        except Exception as e:
            logger.error(f"Erro ao verificar conexão com MT5: {e}", exc_info=True)
            self._is_connected = False
            return False

    def _reconnect_mt5(self) -> None:
        """Tenta reconectar ao MT5 com exponential backoff."""
        if self._is_connected:
            return

        logger.info("Iniciando processo de reconexão com MT5...")
        
        # Tenta desligar antes de tentar reconectar, se estiver em um estado "meio-termo"
        if mt5.is_connected():
            mt5.shutdown()
            logger.info("MT5 foi desligado antes da tentativa de reconexão.")
        
        retries = 0
        max_retries = 10
        base_delay = 1 # segundos

        while not self._is_connected and retries < max_retries and not self._stop_heartbeat.is_set():
            delay = base_delay * (2 ** retries) + random.uniform(0, 1) # Exponential backoff with jitter
            logger.warning(f"Tentando reconectar ao MT5 em {delay:.2f}s... (Tentativa {retries + 1}/{max_retries})")
            time.sleep(delay)
            self._connect_mt5()
            retries += 1
        
        if self._is_connected:
            logger.info("✅ Reconexão com MT5 bem-sucedida!")
        elif not self._stop_heartbeat.is_set():
            logger.critical(f"❌ Falha persistente na reconexão com MT5 após {max_retries} tentativas.")
            # Aqui você pode adicionar lógica para alertar o usuário, ou desligar o sistema
            # dependendo da criticidade.

    def _run_heartbeat(self) -> None:
        """Executa o heartbeat em um loop separado."""
        logger.info("Heartbeat do MT5 iniciado.")
        while not self._stop_heartbeat.is_set():
            if not self._check_connection():
                logger.warning("Conexão com MT5 perdida. Iniciando reconexão...")
                self._reconnect_mt5()
            
            # Ajuste o intervalo do heartbeat conforme a necessidade
            self._stop_heartbeat.wait(timeout=10) # Verifica a cada 10 segundos
        logger.info("Heartbeat do MT5 encerrado.")

    def get_data(self, symbol: str, timeframe_str: str, limit: int) -> pd.DataFrame:
        """
        Busca dados do MT5 e os normaliza para o formato padrão.
        """
        if not self._is_connected:
            logger.error("Não conectado ao MT5. Não é possível buscar dados.")
            return self._EMPTY_DF.copy()

        mt5_timeframe = self.TIMEFRAME_MAP.get(timeframe_str.upper())
        if mt5_timeframe is None:
            logger.error(f"Timeframe '{timeframe_str}' não é suportado pelo MT5Adapter.")
            raise ValueError(f"Timeframe '{timeframe_str}' não é suportado pelo MT5Adapter.")

        # Garante que o símbolo está visível no Market Watch para obter os dados
        # Este comando pode falhar se a conexão não estiver 100% ou símbolo inválido
        if not mt5.symbol_select(symbol, True):
            logger.warning(f"Não foi possível selecionar o símbolo {symbol}. Verifique se está no Market Watch ou se a conexão está estável.")
            # Tentativa de reconexão leve antes de falhar completamente
            if not self._is_connected:
                self._reconnect_mt5()
            if not mt5.symbol_select(symbol, True): # Tenta novamente
                logger.error(f"Falha ao selecionar o símbolo {symbol} mesmo após reconexão. Retornando DataFrame vazio.")
                return self._EMPTY_DF.copy()


        rates = mt5.copy_rates_from_pos(symbol, mt5_timeframe, 0, limit)
        
        if rates is None or len(rates) == 0:
            logger.warning(f"Nenhum dado retornado para {symbol} no timeframe {timeframe_str}.")
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
        """Encerra a conexão com o MetaTrader 5 e o heartbeat."""
        if self._initialized:
            logger.info("🔌 [MT5DataProvider] Encerrando conexão com o MT5 e parando heartbeat.")
            self._stop_heartbeat.set() # Sinaliza para o heartbeat parar
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=5) # Espera o heartbeat terminar
                if self._heartbeat_thread.is_alive():
                    logger.warning("Heartbeat thread não encerrou em tempo. Pode haver recursos pendentes.")
            
            if mt5.is_connected():
                mt5.shutdown()
            self._is_connected = False
            self._instance = None # Permite que uma nova instância seja criada posteriormente
            self._initialized = False # Reseta para permitir nova inicialização

    def get_metadata(self) -> Dict[str, Any]:
        return self.metadata

    def get_filling_mode(self, symbol: str) -> Optional[int]:
        if not self._is_connected:
            logger.error("Não conectado ao MT5. Não é possível obter filling mode.")
            return None
        s_info = mt5.symbol_info(symbol)
        if not s_info: 
            logger.warning(f"Não foi possível obter informações do símbolo {symbol}.")
            return None
        # Prioriza IOC se disponível, senão usa FOK (ou outro padrão)
        if s_info.filling_mode & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
        if s_info.filling_mode & mt5.ORDER_FILLING_FOK: return mt5.ORDER_FILLING_FOK
        return None # Caso nenhum modo específico seja encontrado
    
    def get_symbol_info_tick(self, symbol: str) -> Optional[Any]:
        if not self._is_connected:
            logger.error("Não conectado ao MT5. Não é possível obter tick info.")
            return None
        return mt5.symbol_info_tick(symbol)
    
    def get_symbol_info(self, symbol: str) -> Optional[mt5.SymbolInfo]:
        if not self._is_connected:
            logger.error("Não conectado ao MT5. Não é possível obter symbol info.")
            return None
        return mt5.symbol_info(symbol)

