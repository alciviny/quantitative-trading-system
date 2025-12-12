import logging
import sys
from datetime import datetime, time as dt_time

# Importar as novas classes
from co_piloto_quant.data.adapters.mt5_adapter import MT5DataProvider
from co_piloto_quant.execution.manager import ExecutionManager
from co_piloto_quant.risk_regime import RiskRegimeManager
from co_piloto_quant.execution.orchestrator import TradingOrchestrator, DummyStrategy # Importe sua estratégia real aqui
from co_piloto_quant.utils.telegram_sender import send_message as telegram_send_message


# Configuração global de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout) # Envia logs para o console
        # logging.FileHandler("bot_log.log") # Opcional: Enviar logs para um arquivo
    ]
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Iniciando o run_live_bot.py...")

    # --- 1. Inicialização dos Componentes Básicos ---
    # MT5DataProvider (Singleton)
    mt5_data_provider = MT5DataProvider()

    # RiskRegimeManager
    risk_regime_manager = RiskRegimeManager()

    # ExecutionManager
    # Configure os limites e parâmetros conforme sua estratégia de risco
    execution_manager = ExecutionManager(
        mt5_adapter=mt5_data_provider,
        risk_regime_manager=risk_regime_manager,
        daily_loss_limit=-500.0,  # Exemplo: Limite de perda diária de 500 unidades monetárias
        max_retries=5,
        retry_delay_seconds=2
    )

    # --- 2. Inicialização da Estratégia ---
    # Substitua DummyStrategy() pela sua classe de estratégia real quando estiver pronta.
    # Sua estratégia deve ter métodos como generate_signal, prepare_order_request, etc.
    my_strategy = DummyStrategy() 

    # --- 3. Configuração do TradingOrchestrator ---
    orchestrator = TradingOrchestrator(
        strategy=my_strategy,
        data_provider=mt5_data_provider,
        execution_manager=execution_manager,
        risk_regime_manager=risk_regime_manager, # Opcional, mas útil para o Orchestrator ter acesso direto
        telegram_sender=telegram_send_message,
        start_time="10:00",       # Exemplo: Início do trading às 10:00
        end_time="16:50",         # Exemplo: Para de abrir novas posições às 16:50
        flatten_time="16:55",     # Exemplo: Tenta zerar posições às 16:55
        max_mt5_reconnect_attempts=20, # Tentativas máximas do orchestrator antes de um erro fatal
        main_loop_interval_seconds=10 # Intervalo principal do loop em segundos
    )

    # --- 4. Iniciar a Sessão de Trading ---
    try:
        orchestrator.run_session()
    except KeyboardInterrupt:
        logger.info("Bot encerrado manualmente via KeyboardInterrupt (Ctrl+C).")
        # O graceful shutdown já foi tratado pelo signal_handler no Orchestrator
    except Exception as e:
        logger.critical(f"Exceção não tratada no main: {e}", exc_info=True)
        telegram_send_message(f"💀 ERRO FATAL não tratado no main: {e}", type='FATAL')
    finally:
        # Garante que os recursos sejam liberados, mesmo em caso de erro
        # O Orchestrator.shutdown() já cuida disso, mas um log final aqui é bom.
        logger.info("run_live_bot.py finalizado.")

if __name__ == "__main__":
    main()