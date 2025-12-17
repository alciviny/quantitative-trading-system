import MetaTrader5 as mt5
import logging
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, TYPE_CHECKING

# Lazy import para evitar circular dependencies e para type checking apenas
if TYPE_CHECKING:
    from co_piloto_quant.data.adapters.mt5_adapter import MT5DataProvider
    from co_piloto_quant.risk_regime import RiskRegimeManager  # Assumindo que este é o nome da classe

logger = logging.getLogger(__name__)

class OrderExecutionError(Exception):
    """Exceção customizada para falhas na execução de ordens."""
    pass

# Objeto mock para simular o retorno de mt5.order_send em dry_run
class MockTradeResult:
    def __init__(self, request: Dict[str, Any]):
        self.retcode = mt5.TRADE_RETCODE_DONE
        self.comment = "DRY RUN - Order simulated successfully"
        self.request = request
        self.order = 1000000 + int(time.time() * 1000) % 1000000 # ID de ordem simulado
        self.deal = self.order + 1 # ID de negócio simulado
        self.volume = request.get("volume", 0)
        self.price = request.get("price", 0)
        self.bid = request.get("price", 0.0) # Assume o preço da requisição como bid/ask
        self.ask = request.get("price", 0.0)

class ExecutionManager:
    """
    Gerencia a execução de ordens, atuando como um "guardião" antes de enviar ordens ao MT5.
    Implementa um Kill Switch baseado no regime de risco e um Limite de Perda Diária.
    """

    def __init__(
        self, 
        mt5_adapter: "MT5DataProvider", 
        risk_regime_manager: "RiskRegimeManager",
        daily_loss_limit: float = -100.0, # Exemplo: -100 USD. Ajuste conforme necessário
        max_retries: int = 3,
        retry_delay_seconds: int = 1,
        dry_run: bool = False # Novo parâmetro para o modo de simulação
    ):
        """
        Inicializa o ExecutionManager.

        Args:
            mt5_adapter: Instância do MT5DataProvider para interação com o terminal MT5.
            risk_regime_manager: Instância do RiskRegimeManager para validação do mercado.
            daily_loss_limit: O limite máximo de perda diária permitido. Se o PnL do dia exceder
                              esse valor (negativo), novas aberturas de posição serão bloqueadas.
            max_retries: Número máximo de tentativas de reenvio de ordem em caso de falha transitória.
            retry_delay_seconds: Atraso em segundos entre as tentativas de reenvio.
            dry_run: Se True, nenhuma ordem real será enviada ao MT5; apenas simulada.
        """
        self.mt5_adapter = mt5_adapter
        self.risk_regime_manager = risk_regime_manager
        self.daily_loss_limit = daily_loss_limit
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.dry_run = dry_run
        self._current_daily_pnl: float = 0.0 # Será atualizado periodicamente ou on-demand
        self._last_pnl_update_time: Optional[datetime] = None
        logger.info(f"ExecutionManager inicializado com sucesso. DRY_RUN_MODE: {self.dry_run}")

    def _update_daily_pnl(self) -> None:
        """
        Atualiza o PnL diário da conta.
        NOTA: Para uma implementação robusta, este método precisaria ser chamado
        periodicamente ou em resposta a eventos de trading. Por simplicidade,
        aqui ele buscará o histórico de ordens fechadas do dia.
        """
        if self.dry_run:
            # Em dry run, não há PnL real. Poderíamos simular ou manter 0.
            # Para testes, é melhor que não afete as decisões de risco baseadas em PnL real.
            self._current_daily_pnl = 0.0 # Manter PnL em 0 ou um valor controlado
            self._last_pnl_update_time = datetime.now()
            return
            
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Obter histórico de ordens do dia
        # Isso pode ser custoso, então idealmente seria um valor mantido incrementalmente
        # ou obtido de uma fonte mais otimizada.
        deals = mt5.history_deals_get(today, datetime.now())
        
        current_pnl = 0.0
        if deals:
            for deal in deals:
                # Apenas consideramos o lucro/perda de negócios fechados no dia
                if deal.type in [mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL]: # BUY e SELL são ordens de abertura
                    # É mais complexo determinar PnL diário de deals
                    # MT5 não fornece um PnL por dia diretamente de history_deals_get
                    # Uma abordagem melhor seria manter um controle local do PnL
                    # ou usar mt5.account_info().profit para o PnL total da conta
                    # e deduzir o PnL anterior.
                    pass # Placeholder para a lógica de PnL
        
        # Para fins de demonstração, vamos usar account_info().profit e resetar diariamente
        account_info = mt5.account_info()
        if account_info:
            current_account_profit = account_info.profit # PnL total desde o início
            
            # TODO: Uma lógica mais robusta de PnL diário seria necessária aqui.
            # Por exemplo, salvar o PnL do final do dia anterior e subtrair do PnL atual.
            # Por enquanto, vamos assumir que self._current_daily_pnl será atualizado externamente
            # ou por um mecanismo mais sofisticado.
            if self._last_pnl_update_time is None or self._last_pnl_update_time.date() < datetime.now().date():
                # Reseta PnL diário no início de um novo dia
                self._current_daily_pnl = 0.0 # Reset ou calcular de forma mais robusta
                logger.info("PnL diário resetado para um novo dia.")
            
            # Esta é uma simplificação. A forma correta seria trackear o PnL de posições fechadas
            # APENAS no dia atual.
            # self._current_daily_pnl = some_function_to_calculate_daily_pnl_from_deals()
            
            # Placeholder: em uma aplicação real, o PnL diário seria calculado
            # de forma mais granular ou fornecido por um serviço de contabilidade.
            # Apenas para a demonstração, simularemos um PnL diário
            logger.warning("A atualização do PnL diário é um placeholder e precisa de uma implementação robusta.")
            
        self._last_pnl_update_time = datetime.now()


    def _check_daily_loss_limit(self, trade_type: int) -> bool:
        """
        Verifica se o limite de perda diária foi atingido para abertura de novas posições.
        """
        # Apenas bloqueia novas posições se o PnL estiver abaixo do limite
        # e a operação for uma ABERTURA de posição (não fechamento)
        
        # Simplificação: para MT5, verificar PnL da conta e comparar com o limite.
        # Uma implementação mais precisa consideraria apenas PnL realizado no dia.
        self._update_daily_pnl() # Atualiza o PnL antes de verificar

        # Lógica para determinar se é uma abertura de posição.
        # Isso dependeria de como o `trade_type` é interpretado ou do contexto da chamada.
        # Por enquanto, vamos considerar que esta checagem é para *novas* ordens de mercado/pendentes.
        is_opening_position = (trade_type == mt5.ORDER_TYPE_BUY or trade_type == mt5.ORDER_TYPE_SELL)
        
        # TODO: A lógica de PnL diário precisa ser aprimorada para ser robusta.
        # Por agora, vamos usar um valor simulado ou depender de um PnL acumulado
        # que seria mais fácil de obter do MT5.
        
        # Exemplo simplificado: se o PnL total (ou o que estamos usando como diário)
        # for menor que o limite de perda diária (um valor negativo).
        account_info = mt5.account_info()
        if account_info and is_opening_position and not self.dry_run: # Não checa PnL real em dry_run para não bloquear testes
            if account_info.profit < self.daily_loss_limit: # Usando profit total como proxy (NÃO IDEAL)
                logger.warning(
                    f"KILL SWITCH ATIVADO: Limite de perda diária excedido (PnL: {account_info.profit:.2f} < Limite: {self.daily_loss_limit:.2f}). "
                    "Novas posições não serão abertas."
                )
                return False
        return True

    def _validate_with_risk_regime(self) -> bool:
        """
        Consulta o RiskRegimeManager para validar se a execução de ordens é permitida.
        """
        validation_result = self.risk_regime_manager.validate_market_regime()
        if not validation_result.approved:
            logger.warning(
                f"KILL SWITCH ATIVADO: Regime de mercado não aprovado. Motivo: {validation_result.reason}. "
                "Ordem bloqueada."
            )
            return False
        return True

    def _handle_mt5_error(self, request: Dict[str, Any], result: Any) -> bool:
        """
        Trata erros retornados pelo MT5. Retorna True se a ordem pode ser reenviada, False caso contrário.
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Ignorando erros MT5 e assumindo sucesso para simulação. Request: {request}")
            return False # Em dry_run, assumimos que a simulação foi bem sucedida.

        if result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"Ordem executada com sucesso: {result.comment}")
            return False # Não precisa reenviar

        logger.error(f"Erro MT5 ao enviar ordem (retcode: {result.retcode}): {result.comment}. Request: {request}")

        # Lógica de reenvio/cancelamento baseada no código de retorno
        if result.retcode in [
            mt5.TRADE_RETCODE_REJECT,          # Rejeição geral
            mt5.TRADE_RETCODE_INVALID_VOLUME,  # Volume inválido
            mt5.TRADE_RETCODE_INVALID_PRICE,   # Preço inválido
            mt5.TRADE_RETCODE_TOO_MANY_REQUESTS # Excesso de requisições
        ]:
            logger.warning(f"Erro não recuperável para reenvio. Ordem será cancelada. Request: {request}")
            return False # Não tentar novamente, erro "fatal" para este pedido

        elif result.retcode in [
            mt5.TRADE_RETCODE_REQUOTE,         # Requotação (preço mudou)
            mt5.TRADE_RETCODE_PRICE_OFF,       # Preço fora do range
            mt5.TRADE_RETCODE_NO_CONNECTION,   # Sem conexão (embora MT5Adapter já lide com isso)
            mt5.TRADE_RETCODE_SERVER_BUSY,     # Servidor ocupado
            mt5.TRADE_RETCODE_TTIMEOUT         # Timeout da transação
        ]:
            logger.warning(f"Erro recuperável. Tentando reenviar ordem. Request: {request}")
            return True # Tentar novamente

        elif result.retcode in [
            mt5.TRADE_RETCODE_MARKET_CLOSED,    # Mercado fechado
            mt5.TRADE_RETCODE_TRADE_DISABLED    # Trading desabilitado para o símbolo
        ]:
            logger.warning(f"Mercado fechado ou trading desabilitado. Ordem será cancelada. Request: {request}")
            return False # Não tentar novamente, esperar abertura do mercado

        else:
            logger.error(f"Erro MT5 desconhecido. Ordem será cancelada. Request: {request}")
            return False # Erro desconhecido, cancelar por segurança


    def send_order(self, request: Dict[str, Any]) -> Any:
        """
        Envia uma ordem ao MetaTrader 5 após passar pelas validações.
        Em modo `dry_run`, simula o envio da ordem e retorna um resultado de sucesso.

        Args:
            request: Dicionário contendo os parâmetros da ordem no formato MT5.

        Returns:
            O resultado da operação mt5.order_send ou um objeto simulado de sucesso em dry_run.

        Raises:
            OrderExecutionError: Se a ordem for bloqueada pelo Kill Switch ou
                                 pelo limite de perda diária.
        """
        # 1. Kill Switch: Validação do Regime de Risco
        if not self._validate_with_risk_regime():
            raise OrderExecutionError("Ordem bloqueada pelo Kill Switch do Regime de Risco.")

        # 2. Daily Loss Limit
        if not self._check_daily_loss_limit(request.get("type")): # Assume 'type' existe no request
            raise OrderExecutionError("Ordem bloqueada devido ao limite de perda diária excedido.")

        if self.dry_run:
            logger.info(f"DRY RUN: Simulação de ordem -> Ação: {request.get('action')}, Símbolo: {request.get('symbol')}, Volume: {request.get('volume')}, Tipo: {request.get('type')}")
            return MockTradeResult(request)

        # 3. Envio da Ordem com Retries e tratamento de erros (APENAS EM MODO REAL)
        for attempt in range(self.max_retries + 1):
            logger.info(f"Enviando ordem (tentativa {attempt + 1}/{self.max_retries + 1}): {request}")
            result = mt5.order_send(request)

            if result is None:
                logger.error(f"mt5.order_send retornou None. Possível problema de conexão ou API. Request: {request}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay_seconds)
                    continue
                raise OrderExecutionError(f"Falha ao enviar ordem após {self.max_retries} tentativas: mt5.order_send retornou None.")

            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Ordem executada com sucesso. Order: {result.order}, Deal: {result.deal}")
                return result
            
            # Se não foi sucesso, decide se tenta novamente
            if attempt < self.max_retries and self._handle_mt5_error(request, result):
                time.sleep(self.retry_delay_seconds)
                continue
            else:
                logger.error(f"Falha final ao enviar ordem após {attempt + 1} tentativas. "
                             f"Retcode: {result.retcode}, Comment: {result.comment}. Request: {request}")
                raise OrderExecutionError(
                    f"Falha ao enviar ordem após {attempt + 1} tentativas. "
                    f"Retcode: {result.retcode}, Comment: {result.comment}"
                )

        raise OrderExecutionError(f"Falha inesperada ao enviar ordem após {self.max_retries + 1} tentativas.")

    def get_current_pnl(self) -> float:
        """Retorna o PnL diário atual. (Precisa de implementação robusta)"""
        # TODO: Implementar de forma robusta o cálculo do PnL diário
        if self.dry_run:
            return 0.0 # Em dry_run, PnL é sempre 0 ou mockado para não influenciar
        
        # A lógica de PnL real só é executada em modo real
        account_info = mt5.account_info()
        if account_info:
            logger.warning("get_current_pnl está usando account_info().profit como proxy para PnL diário, o que é impreciso. Necessita de implementação robusta para PnL diário real.")
            return account_info.profit 
        return 0.0

    def calculate_position_size(
        self,
        capital: float,
        entry_price: float,
        stop_loss_price: float,
        risk_pct: float = 0.5,
        point_value: float = 1.0
    ) -> float:
        """
        Calcula o tamanho da posição usando Fixed Risk Position Sizing.
        
        Fórmula: N = (Capital × Risk %) / (|Entry - Stop| × Point Value)
        
        Esta abordagem garante que o risco máximo por trade é sempre o mesmo
        percentual do capital, independentemente do tamanho da volatilidade.
        
        Args:
            capital: Saldo atual da conta (em USD/EUR/etc)
            entry_price: Preço de entrada da posição
            stop_loss_price: Preço do stop loss
            risk_pct: Percentual máximo de risco por trade (padrão 0.5%)
            point_value: Valor de cada ponto/pip (padrão 1.0 para cálculos simples)
            
        Returns:
            Tamanho da posição em lotes/unidades
            
        Example:
            # Capital: $10,000, Entrada: 1.1050, Stop: 1.1000, Risco: 0.5%
            # Perda máxima: $50 (0.5% de $10,000)
            # Distância: 50 pips
            # Tamanho: $50 / (50 pips × $0.10 por pip) = 10 lotes
            
            size = manager.calculate_position_size(
                capital=10000,
                entry_price=1.1050,
                stop_loss_price=1.1000,
                risk_pct=0.5,
                point_value=0.10
            )
        """
        if capital <= 0:
            logger.error(f"Capital inválido: {capital}")
            return 0.0
        
        if entry_price <= 0 or stop_loss_price <= 0:
            logger.error(f"Preços inválidos: entry={entry_price}, stop={stop_loss_price}")
            return 0.0
        
        if entry_price == stop_loss_price:
            logger.error("Entry price e stop loss são iguais. Não é possível calcular posição.")
            return 0.0
        
        risk_amount = capital * (risk_pct / 100.0)
        stop_distance = abs(entry_price - stop_loss_price)
        risk_per_unit = stop_distance * point_value
        
        if risk_per_unit <= 0:
            logger.error(f"Risk per unit inválido: {risk_per_unit}")
            return 0.0
        
        position_size = risk_amount / risk_per_unit
        
        logger.info(
            f"Position Sizing - Capital: ${capital:.2f}, Risk: {risk_pct}%, "
            f"Entry: {entry_price:.5f}, Stop: {stop_loss_price:.5f}, "
            f"RiskAmount: ${risk_amount:.2f}, Distance: {stop_distance:.5f}, "
            f"PositionSize: {position_size:.2f} unidades"
        )
        
        return position_size

