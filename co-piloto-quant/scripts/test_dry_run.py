import logging
import sys
import time
from datetime import datetime, timedelta
from typing import Optional, Any, Dict

# Importar as novas classes
from co_piloto_quant.data.adapters.mt5_adapter import MT5DataProvider
from co_piloto_quant.execution.manager import ExecutionManager, OrderExecutionError
from co_piloto_quant.risk_regime import RiskRegimeManager, ValidationResult
from co_piloto_quant.execution.orchestrator import TradingOrchestrator, TradingState
from co_piloto_quant.utils.telegram_sender import send_message as telegram_send_message

# Configuração global de logging para o teste
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Mock da estratégia para o teste
class MockStrategy:
    def __init__(self, should_generate_signal: bool = False):
        self.should_generate_signal = should_generate_signal
        self.signal_generated = False # Para gerar sinal apenas uma vez por ciclo de trading ativo
        logger.info("MockStrategy inicializada para teste.")

    def generate_signal(self, data: Any) -> Optional[Dict[str, Any]]:
        """Simula a geração de um sinal de trading."""
        if self.should_generate_signal and not self.signal_generated:
            # Simula um sinal para que o ExecutionManager possa ser testado
            logger.info("MockStrategy: Gerando sinal de compra simulado (uma vez).")
            self.signal_generated = True
            return {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": "TEST_DRY_RUN",
                "volume": 0.01,
                "type": mt5.ORDER_TYPE_BUY,
                "price": 100.0, # Preço mockado
                "deviation": 0,
                "magic": 98765,
                "comment": "DRY RUN TEST BUY",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
        return None

    def prepare_order_request(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prepara uma requisição de ordem MT5 a partir de um sinal."""
        return signal # Sinal já está no formato de request

    def prepare_close_order(self, position: Any) -> Optional[Dict[str, Any]]:
        """Prepara uma requisição para fechar uma posição."""
        logger.info(f"MockStrategy: Preparando ordem para fechar posição simulada: {position}")
        # Retorna uma ordem de fechamento mockada
        return {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": "TEST_DRY_RUN",
            "volume": 0.01,
            "type": mt5.ORDER_TYPE_SELL, # Ou BUY, dependendo da posição
            "price": 99.0,
            "deviation": 0,
            "magic": 98765,
            "comment": "DRY RUN TEST CLOSE",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

# Mock do MT5DataProvider para não tentar inicializar o MT5 real durante o teste
class MockMT5DataProvider(MT5DataProvider):
    _instance = None # Resetar o Singleton para este mock

    def __init__(self, dry_run: bool = True):
        # Override para não chamar mt5.initialize
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.metadata: Dict[str, Any] = {"provider_name": "MockMT5DataProvider"}
            self._is_connected = True # Sempre conectado em mock
            logger.info("✅ MockMT5DataProvider: Conectado com sucesso (simulado).")
            # Não iniciar heartbeat thread real
            
    def _connect_mt5(self) -> None:
        logger.info("MockMT5DataProvider: Conexão simulada.")
        self._is_connected = True

    def _check_connection(self) -> bool:
        return True # Sempre conectado

    def _reconnect_mt5(self) -> None:
        logger.info("MockMT5DataProvider: Reconexão simulada.")
        self._is_connected = True

    def close(self):
        logger.info("MockMT5DataProvider: Encerrando conexão simulada.")
        self._is_connected = False
        self._instance = None
        self._initialized = False

    def get_data(self, symbol: str, timeframe_str: str, limit: int) -> pd.DataFrame:
        logger.info(f"MockMT5DataProvider: Obtendo dados simulados para {symbol}.")
        # Retorna um DataFrame vazio ou um mock simples
        return pd.DataFrame({'open': [100.0], 'high': [101.0], 'low': [99.0], 'close': [100.5], 'volume': [100]},
                            index=pd.to_datetime([datetime.now() - timedelta(minutes=1)]))


def run_dry_run_test():
    logger.info("Iniciando teste de Dry Run do TradingOrchestrator.")

    # --- 1. Inicialização dos Componentes Básicos em MODO DRY_RUN ---
    # Usar o MockMT5DataProvider para evitar conexão real com MT5
    mt5_data_provider = MockMT5DataProvider(dry_run=True)

    # RiskRegimeManager
    # Para o teste, podemos mockar o retorno de validate_market_regime se necessário
    class MockRiskRegimeManager(RiskRegimeManager):
        def validate_market_regime(self, df_indicators: pd.DataFrame) -> ValidationResult:
            logger.info("MockRiskRegimeManager: Validando regime de mercado (sempre aprovado para teste).")
            return ValidationResult(approved=True, reason='Regime de mercado aprovado (mock).')
    
    risk_regime_manager = MockRiskRegimeManager()

    # ExecutionManager em MODO DRY_RUN
    execution_manager = ExecutionManager(
        mt5_adapter=mt5_data_provider,
        risk_regime_manager=risk_regime_manager,
        daily_loss_limit=-100.0,
        max_retries=1, # Menos retries para teste rápido
        retry_delay_seconds=0.1, # Delay menor para teste rápido
        dry_run=True # MODO DRY_RUN ATIVADO
    )

    # Mock da estratégia para o teste - pode gerar um sinal para verificar o EM
    mock_strategy = MockStrategy(should_generate_signal=True) 

    # --- 2. Configuração do TradingOrchestrator para Teste ---
    # Definir horários que permitam o ciclo completo em segundos
    # CUIDADO: A hora real do sistema vai influenciar isso.
    # Para garantir o ciclo, use `datetime.now()` como base.
    now = datetime.now()
    test_start_time = (now + timedelta(seconds=2)).strftime("%H:%M") # Setup -> wait por 2s
    test_end_time = (now + timedelta(seconds=7)).strftime("%H:%M") # Wait -> active por 5s
    test_flatten_time = (now + timedelta(seconds=10)).strftime("%H:%M") # Active -> EOD por 3s

    orchestrator = TradingOrchestrator(
        strategy=mock_strategy,
        data_provider=mt5_data_provider,
        execution_manager=execution_manager,
        risk_regime_manager=risk_regime_manager,
        telegram_sender=telegram_send_message,
        start_time=test_start_time,
        end_time=test_end_time,
        flatten_time=test_flatten_time,
        max_mt5_reconnect_attempts=1, # Menos tentativas para falha rápida
        main_loop_interval_seconds=1 # Loop mais rápido para teste
    )

    # --- 3. Executar a Sessão de Trading (simulada) ---
    logger.info("Iniciando o loop do Orchestrator. Observar logs e mensagens Telegram simuladas.")
    try:
        orchestrator.run_session()
    except KeyboardInterrupt:
        logger.info("Teste de Dry Run interrompido manualmente.")
    except Exception as e:
        logger.error(f"Erro durante o teste de Dry Run: {e}", exc_info=True)
    finally:
        logger.info("Finalizando o teste de Dry Run.")

    logger.info("Teste de Dry Run concluído. Verifique os logs acima para as transições de estado.")

if __name__ == "__main__":
    run_dry_run_test()
