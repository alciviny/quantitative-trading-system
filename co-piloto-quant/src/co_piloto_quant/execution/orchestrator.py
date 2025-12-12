import logging
import time
import signal
import sys
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Optional, Any, Dict

# Assumindo que essas classes existem e estão em seus respectivos paths
from co_piloto_quant.data.adapters.mt5_adapter import MT5DataProvider
from co_piloto_quant.execution.manager import ExecutionManager, OrderExecutionError
from co_piloto_quant.risk_regime import RiskRegimeManager
from co_piloto_quant.utils.telegram_sender import send_message as telegram_send_message

logger = logging.getLogger(__name__)

class TradingState(Enum):
    """Estados possíveis do orquestrador de trading."""
    SETUP = auto()
    MARKET_WAIT = auto()
    ACTIVE_TRADING = auto()
    EOD_FLATTEN = auto()
    SHUTDOWN = auto()

class TradingOrchestrator:
    """
    Orquestra o ciclo de vida de um robô de trading usando uma máquina de estados.
    Gerencia a inicialização, espera de mercado, trading ativo e final do dia.
    """
    def __init__(
        self,
        strategy: Any, # Placeholder para a classe de estratégia
        data_provider: MT5DataProvider,
        execution_manager: ExecutionManager,
        risk_regime_manager: RiskRegimeManager,
        telegram_sender: Any, # A função telegram_send_message
        start_time: str = "10:00", # Horário de início do trading
        end_time: str = "16:50",   # Horário para parar de abrir novas posições
        flatten_time: str = "16:55", # Horário para tentar zerar posições
        max_mt5_reconnect_attempts: int = 10,
        main_loop_interval_seconds: int = 5 # Intervalo entre iterações do loop principal
    ):
        self.strategy = strategy
        self.data_provider = data_provider
        self.execution_manager = execution_manager
        self.risk_regime_manager = risk_regime_manager
        self.telegram_sender = telegram_sender
        self.current_state = TradingState.SETUP
        self.running = True # Flag para controlar o loop principal
        self.max_mt5_reconnect_attempts = max_mt5_reconnect_attempts
        self.mt5_reconnect_failures = 0
        self.main_loop_interval_seconds = main_loop_interval_seconds

        # Configura horários de trading
        self.start_time = datetime.strptime(start_time, "%H:%M").time()
        self.end_time = datetime.strptime(end_time, "%H:%M").time()
        self.flatten_time = datetime.strptime(flatten_time, "%H:%M").time()

        # Configura o graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("TradingOrchestrator inicializado.")
        self.telegram_sender(f"Orchestrator inicializado. Horários configurados:\n"
                             f"Início: {self.start_time}\n"
                             f"Fim para novas posições: {self.end_time}\n"
                             f"Zeragem (Flatten): {self.flatten_time}", type='INFO')

    def _signal_handler(self, signum, frame):
        """Handler para sinais de interrupção (e.g., Ctrl+C)."""
        logger.warning(f"Sinal de interrupção ({signum}) recebido. Iniciando graceful shutdown...")
        self.telegram_sender(f"Sinal de interrupção ({signum}) recebido. Encerrando robô...", type='STOP')
        self.running = False
        self.current_state = TradingState.SHUTDOWN

    def run_session(self):
        """Executa o loop principal da máquina de estados do trading."""
        while self.running:
            try:
                if self.current_state == TradingState.SETUP:
                    self._state_setup()
                elif self.current_state == TradingState.MARKET_WAIT:
                    self._state_market_wait()
                elif self.current_state == TradingState.ACTIVE_TRADING:
                    self._state_active_trading()
                elif self.current_state == TradingState.EOD_FLATTEN:
                    self._state_eod()
                elif self.current_state == TradingState.SHUTDOWN:
                    self._state_shutdown()
                    break # Sai do loop principal após o shutdown
            except OrderExecutionError as e:
                logger.error(f"Erro de execução de ordem: {e}")
                self.telegram_sender(f"Erro de Execução: {e}", type='ERROR')
                # Decide se um erro de execução deve parar o bot completamente ou apenas logar
                # Por agora, vamos continuar, mas é um ponto de decisão.
            except Exception as e:
                logger.critical(f"Erro crítico inesperado no estado {self.current_state}: {e}", exc_info=True)
                self.telegram_sender(f"Erro FATAL no estado {self.current_state}: {e}", type='FATAL')
                self.running = False # Encerra o bot em caso de erro crítico inesperado
                self.current_state = TradingState.SHUTDOWN
            
            time.sleep(1) # Pequeno delay para evitar CPU spin

    def _state_setup(self):
        logger.info("Estado: SETUP - Verificando conexões e carregando configurações iniciais...")
        self.telegram_sender("🟢 Bot iniciado. Verificando setup...", type='START')

        # Verifica conexão MT5
        if not self.data_provider._is_connected:
            logger.warning("MT5 não conectado durante o SETUP. Tentando conectar...")
            self.data_provider._connect_mt5() # Tenta a conexão inicial

        if not self.data_provider._is_connected:
            self.mt5_reconnect_failures += 1
            if self.mt5_reconnect_failures > self.max_mt5_reconnect_attempts:
                logger.critical("Falha em conectar o MT5 após múltiplas tentativas no SETUP. Encerrando.")
                self.telegram_sender("💀 ERRO FATAL: Falha em conectar MT5. Encerrando.", type='FATAL')
                self.running = False
                self.current_state = TradingState.SHUTDOWN
                return
            else:
                logger.warning(f"MT5 ainda não conectado. Tentativa {self.mt5_reconnect_failures}/{self.max_mt5_reconnect_attempts}. Re-tentando...")
                time.sleep(self.data_provider.retry_delay_seconds) # Usa o delay do adapter
                return # Permanece no estado SETUP e tenta novamente no próximo ciclo

        logger.info("Setup concluído. MT5 conectado e pronto.")
        self.mt5_reconnect_failures = 0 # Reseta o contador de falhas
        
        current_time = datetime.now().time()
        if current_time < self.start_time:
            self.current_state = TradingState.MARKET_WAIT
        else:
            self.current_state = TradingState.ACTIVE_TRADING
        self.telegram_sender(f"Setup OK. Transicionando para {self.current_state.name}.", type='INFO')

    def _state_market_wait(self):
        current_time = datetime.now().time()
        if current_time >= self.start_time:
            logger.info(f"Estado: MARKET_WAIT - Horário de início ({self.start_time}) atingido. Transicionando para ACTIVE_TRADING.")
            self.telegram_sender(f"⏰ Início do pregão ({self.start_time}). Iniciando trading ativo.", type='INFO')
            self.current_state = TradingState.ACTIVE_TRADING
        else:
            logger.info(f"Estado: MARKET_WAIT - Aguardando horário de início do pregão. Agora: {current_time}. Início: {self.start_time}")
            self.telegram_sender(f"💤 Aguardando início do pregão. Agora: {current_time}. Início: {self.start_time}", type='INFO')
            # Dorme por um intervalo fixo e razoável, sem tentar calcular o tempo restante
            time.sleep(self.main_loop_interval_seconds)
        
        # Durante o Market Wait, também precisamos checar a conexão MT5
        if not self.data_provider._is_connected:
            logger.warning("Conexão MT5 perdida durante MARKET_WAIT. Tentando reconectar...")
            # O MT5DataProvider já tem lógica de auto-reconexão no heartbeat
            # Aqui apenas verificamos se ele conseguiu se reconectar
            if not self.data_provider._is_connected:
                self.mt5_reconnect_failures += 1
                if self.mt5_reconnect_failures > self.max_mt5_reconnect_attempts:
                    logger.critical("Falha em reconectar o MT5 após múltiplas tentativas no MARKET_WAIT. Encerrando.")
                    self.telegram_sender("💀 ERRO FATAL: Falha em reconectar MT5. Encerrando.", type='FATAL')
                    self.running = False
                    self.current_state = TradingState.SHUTDOWN
                    return
                # Se ainda não conectou, espera e tenta novamente no próximo ciclo
                time.sleep(self.data_provider.retry_delay_seconds)
                logger.warning(f"MT5 ainda não conectado. Tentativa {self.mt5_reconnect_failures}/{self.max_mt5_reconnect_attempts}. Re-tentando...")
            else:
                self.mt5_reconnect_failures = 0 # Reseta se reconectou

    def _state_active_trading(self):
        current_time = datetime.now().time()
        
        if not self.data_provider._is_connected:
            self.mt5_reconnect_failures += 1
            if self.mt5_reconnect_failures > self.max_mt5_reconnect_attempts:
                logger.critical("Falha em reconectar o MT5 após múltiplas tentativas no ACTIVE_TRADING. Encerrando.")
                self.telegram_sender("💀 ERRO FATAL: Falha em reconectar MT5. Encerrando.", type='FATAL')
                self.running = False
                self.current_state = TradingState.SHUTDOWN
                return
            else:
                logger.warning(f"MT5 desconectado durante ACTIVE_TRADING. Tentativa {self.mt5_reconnect_failures}/{self.max_mt5_reconnect_attempts}. Pausando operações...")
                time.sleep(self.data_provider.retry_delay_seconds)
                return # Não executa lógica de trading enquanto desconectado
        else:
            self.mt5_reconnect_failures = 0 # Reseta se reconectou

        if current_time >= self.flatten_time:
            logger.info(f"Estado: ACTIVE_TRADING - Horário de zeragem ({self.flatten_time}) atingido. Transicionando para EOD_FLATTEN.")
            self.telegram_sender(f"🏁 Horário de zeragem ({self.flatten_time}). Iniciando zeragem de posições.", type='STOP')
            self.current_state = TradingState.EOD_FLATTEN
            return
        elif current_time >= self.end_time:
            logger.info(f"Estado: ACTIVE_TRADING - Horário de fim para novas posições ({self.end_time}) atingido. Não abrirá mais posições.")
            self.telegram_sender(f"🛑 Horário de fim para novas posições ({self.end_time}).", type='STOP')
            # Ainda permite gerenciar posições existentes, mas não abrir novas.
            # A lógica de estratégia deve respeitar isso.

        logger.info(f"Estado: ACTIVE_TRADING - Executando ciclo de trading. Agora: {current_time}.")
        
        # --- Lógica principal do ciclo de trading ---
        try:
            # 1. Obter dados (a estratégia deve definir quais dados precisa)
            # Exemplo: dados_recentes = self.data_provider.get_data("PETR4", "M5", 100)

            # 2. Calcular sinais da estratégia
            # Exemplo: sinal = self.strategy.generate_signal(dados_recentes)

            # 3. Preparar requisição de ordem (placeholder)
            # Exemplo: request = self.strategy.prepare_order_request(sinal)

            # 4. Validar e enviar ordem via ExecutionManager
            # if request:
            #     order_result = self.execution_manager.send_order(request)
            #     logger.info(f"Ordem enviada: {order_result}")
            #     self.telegram_sender(f"Ordem enviada: {request.get('symbol')} {request.get('type')}", type='TRADE')

            # Placeholder para a lógica de trading real
            logger.info(">>> Lógica de trading da estratégia seria executada aqui. <<<")

            # Simula a verificação do limite de perda diária
            if self.execution_manager.get_current_pnl() < self.execution_manager.daily_loss_limit:
                 logger.warning("Limite de perda diária atingido. Novas posições bloqueadas.")
                 self.telegram_sender(
                     f"🛑 Limite de Perda Diária Atingido (PnL: {self.execution_manager.get_current_pnl():.2f}). "
                     "Novas posições bloqueadas. Aguardando horário de zeragem.",
                     type='STOP'
                 )
                 # Se o limite de perda for atingido, podemos parar de operar ativamente
                 # e apenas esperar o flatten_time ou até mesmo ir para EOD_FLATTEN
                 # Por enquanto, só emitimos o alerta e bloqueamos novas aberturas via EM.
            
            # TODO: Lógica para pegar indicadores para RiskRegimeManager e chamar validate_market_regime
            # Exemplo: df_indicadores_risco = self.data_provider.get_risk_indicators()
            # self.risk_regime_manager.validate_market_regime(df_indicadores_risco) # Isso é feito pelo ExecutionManager

        except OrderExecutionError as e:
            logger.warning(f"Ordem bloqueada pelo ExecutionManager: {e}")
            self.telegram_sender(f"⚠️ Ordem Bloqueada: {e}", type='WARNING')
        except Exception as e:
            logger.error(f"Erro na lógica de trading: {e}", exc_info=True)
            self.telegram_sender(f"❌ Erro na lógica de trading: {e}", type='ERROR')

        time.sleep(self.main_loop_interval_seconds) # Espera antes da próxima iteração

    def _state_eod(self):
        logger.info("Estado: EOD_FLATTEN - Iniciando processo de zeragem de posições e encerramento do dia.")
        self.telegram_sender("🏁 Fim do pregão. Iniciando zeragem de posições...", type='STOP')

        # TODO: Implementar lógica para zerar posições abertas
        # Isso envolveria:
        # 1. Obter todas as posições abertas via MT5DataProvider.
        # 2. Para cada posição, preparar uma ordem de fechamento (contra-operação).
        # 3. Enviar as ordens de fechamento via ExecutionManager.
        
        # Exemplo simplificado de zeragem (NÃO É UMA IMPLEMENTAÇÃO REAL)
        # positions = self.data_provider.get_open_positions() # Supondo que exista este método
        # for pos in positions:
        #     close_request = self.strategy.prepare_close_order(pos)
        #     try:
        #         self.execution_manager.send_order(close_request)
        #         logger.info(f"Posição {pos.ticket} zerada com sucesso.")
        #     except OrderExecutionError as e:
        #         logger.error(f"Falha ao zerar posição {pos.ticket}: {e}")
        #         self.telegram_sender(f"❌ Falha ao zerar posição {pos.ticket}: {e}", type='ERROR')

        logger.info(">>> Lógica de zeragem de posições seria executada aqui. <<<")

        # Após tentar zerar, reportar PnL e encerrar
        # PnL do dia (a ser implementado robustamente no ExecutionManager)
        estimated_daily_pnl = self.execution_manager.get_current_pnl() # Isto é um placeholder
        self.telegram_sender(f"🎉 Dia encerrado. PnL Estimado: R$ {estimated_daily_pnl:.2f}", type='INFO')
        logger.info("Processo de EOD_FLATTEN concluído. Transicionando para SHUTDOWN.")
        self.current_state = TradingState.SHUTDOWN

    def _state_shutdown(self):
        logger.info("Estado: SHUTDOWN - Iniciando desligamento graceful.")
        self.telegram_sender("👋 Encerrando robô. Desligamento seguro.", type='STOP')

        # Garante que todas as conexões sejam fechadas
        if self.data_provider:
            self.data_provider.close()
        
        logger.info("Desligamento concluído. Saindo.")
        self.running = False # Garante que o loop principal pare
        sys.exit(0) # Termina o processo

# Placeholder para a classe Strategy, que o Orchestrator espera
class DummyStrategy:
    def __init__(self):
        logger.info("DummyStrategy inicializada.")
    
    def generate_signal(self, data: Any) -> Optional[Dict[str, Any]]:
        """Simula a geração de um sinal de trading."""
        # Aqui sua estratégia real processaria 'data' e decidiria se há um sinal
        return None # Retorna None se não houver sinal

    def prepare_order_request(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Prepara uma requisição de ordem MT5 a partir de um sinal."""
        # Lógica para converter sinal em request MT5
        return None

    def prepare_close_order(self, position: Any) -> Optional[Dict[str, Any]]:
        """Prepara uma requisição para fechar uma posição."""
        return None
