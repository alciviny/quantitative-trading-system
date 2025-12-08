import pandas as pd
import time as os_time
from datetime import datetime, time
import sys
from pathlib import Path
import traceback

import MetaTrader5 as mt5

# --- AJUSTE DE PATH E IMPORTS ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

from co_piloto_quant.config import (
    MT5_MAGIC_NUMBER, MT5_DEVIATION, MT5_MAX_POSITIONS,
    TRADING_WHITELIST, FIXED_LOT_SIZE, BB_ENTRY_STD_DEV_DEFAULT
)
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy
from co_piloto_quant.data.adapters.mt5_adapter import MT5DataProvider, MT5ConnectionError
from co_piloto_quant.utils.telegram_sender import send_message
# --- NOVO: Importa o Logger de Trades ---
from co_piloto_quant.data.trade_logger import TradeLogger

# --- CONSTANTES E CONFIGS ---
MAX_SPREAD_POINTS = 15.0
TRADING_START_HOUR = 9
TRADING_START_MIN = 15
TRADING_END_HOUR = 16
TRADING_END_MIN = 50
BREAKEVEN_PROFIT_MULTIPLIER = 1.5
MT5_TIMEFRAME_STR = "M15"
N_BARS_TO_FETCH = 300

def load_optimal_parameters(file_path: Path) -> pd.DataFrame:
    """Carrega o ranking de estabilidade e o prepara para consulta rápida."""
    if not file_path.exists():
        send_message("Arquivo `professional_stability_ranking.csv` não encontrado. Usando parâmetros padrão.", type='WARNING')
        return pd.DataFrame()
    try:
        df = pd.read_csv(file_path)
        df.set_index('Ticker', inplace=True)
        send_message(f"Ranking de estabilidade com {len(df)} ativos carregado com sucesso.", type='INFO')
        return df
    except Exception as e:
        send_message(f"Falha ao ler o arquivo de ranking: {e}. Usando parâmetros padrão.", type='ERROR')
        return pd.DataFrame()

def is_trading_hours():
    now = datetime.now().time()
    start_time = time(TRADING_START_HOUR, TRADING_START_MIN)
    end_time = time(TRADING_END_HOUR, TRADING_END_MIN)
    return start_time <= now <= end_time

def obter_ativos_monitorados():
    if TRADING_WHITELIST:
        return TRADING_WHITELIST
    symbols = mt5.symbols_get(group="!*.ECN")
    return [s.name for s in symbols] if symbols else []

def executar_ordem(provider: MT5DataProvider, logger: TradeLogger, symbol: str, tipo_ordem: int, signal_data: pd.Series, strategy_engine: AdaptiveSniperStrategy):
    if (mt5.positions_total() + mt5.orders_total()) >= MT5_MAX_POSITIONS:
        return

    tick = provider.get_symbol_info_tick(symbol)
    symbol_info = provider.get_symbol_info(symbol)
    if not tick or not symbol_info: return

    spread_points = (tick.ask - tick.bid) / symbol_info.point
    if spread_points > MAX_SPREAD_POINTS:
        return

    price = tick.ask if tipo_ordem == mt5.ORDER_TYPE_BUY else tick.bid
    sl = float(signal_data.get('STOP_LOSS', price * 0.01))

    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(FIXED_LOT_SIZE),
        "type": tipo_ordem, "price": price, "sl": sl, "deviation": MT5_DEVIATION,
        "magic": MT5_MAGIC_NUMBER, "comment": f"Sniper {strategy_engine.get_name()}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": provider.get_filling_mode(symbol),
    }
    
    result = mt5.order_send(request)
    
    if not result or result.retcode != mt5.TRADE_RETCODE_DONE:
        msg = f"Falha ao enviar ordem para *{symbol}*.\nCausa: `{result.comment if result else 'N/A'}`"
        send_message(msg, type='ERROR')
    else:
        operation_str = 'BUY' if tipo_ordem == mt5.ORDER_TYPE_BUY else 'SELL'
        
        # --- LOGGING DA CAIXA PRETA ---
        logger.log_trade(
            ticket=result.order,
            symbol=symbol,
            operation=operation_str,
            price=result.price,
            volume=result.volume,
            stop_loss=result.sl,
            reason_data=signal_data
        )

        # --- NOTIFICAÇÃO TELEGRAM ---
        msg = (
            f"Ordem de *{operation_str}* enviada para `{symbol}`.\n\n"
            f"• *Parâmetro BB Dev:* `{strategy_engine.bb_entry_std_dev:.4f}`\n"
            f"• *Preço Entrada:* `{result.price:.5f}`\n"
            f"• *Stop Loss:* `{result.sl:.5f}`\n"
            f"• *Lote:* `{result.volume}` | *Ticket:* `{result.order}`"
        )
        send_message(msg, type='TRADE')
        print(f"✅ Ordem Executada! Ticket: {result.order}")


def fechar_posicao_emergencia(provider: MT5DataProvider, position, motivo: str):
    # ... (código sem alteração)
    pass 

def monitorar_posicoes_abertas():
    # ... (código sem alteração)
    pass

def processar_ativo(provider: MT5DataProvider, logger: TradeLogger, symbol: str, optimal_params_df: pd.DataFrame):
    
    # --- HANDOVER EM AÇÃO ---
    best_dev = BB_ENTRY_STD_DEV_DEFAULT
    if not optimal_params_df.empty and symbol in optimal_params_df.index:
        best_dev = optimal_params_df.loc[symbol]['Best BB Dev']
    
    strategy_engine = AdaptiveSniperStrategy(bb_entry_std_dev=best_dev)
    # --- FIM DO HANDOVER ---

    df = provider.get_data(symbol, MT5_TIMEFRAME_STR, limit=N_BARS_TO_FETCH)
    if df.empty or len(df) < 200: return

    df_indic = calculate_indicators(df, bb_entry_deviation=best_dev)
    df_analyzed = strategy_engine.evaluate(df_indic)
    latest = df_analyzed.iloc[-1]

    positions = mt5.positions_get(symbol=symbol)
    has_position = len(positions) > 0 if positions else False
    
    is_regime_toxic = latest.get('Entropy_Z', 0) > 2.0
    
    if has_position and is_regime_toxic:
        for pos in positions: fechar_posicao_emergencia(provider, pos, "Regime Tóxico")
        return

    if not has_position and not is_regime_toxic:
        if latest.get('SIGNAL') == 'BUY':
            executar_ordem(provider, logger, symbol, mt5.ORDER_TYPE_BUY, latest, strategy_engine)

def run_bot():
    provider = None
    logger = None
    try:
        # --- INICIALIZAÇÃO DOS SERVIÇOS ---
        provider = MT5DataProvider()
        logger = TradeLogger()

        # --- CARREGANDO A INTELIGÊNCIA ---
        ranking_path = project_root.parent / "data" / "reports" / "professional_stability_ranking.csv"
        optimal_params = load_optimal_parameters(ranking_path)
        
        ativos = obter_ativos_monitorados()
        
        start_message = f"Robô iniciado no servidor `{provider.get_metadata().get('server')}`."
        send_message(start_message, type='START')
        print(f"👁️  Monitorando {len(ativos)} ativos.")

        while True:
            monitorar_posicoes_abertas()
            if is_trading_hours():
                for ativo in ativos:
                    try:
                        processar_ativo(provider, logger, ativo, optimal_params)
                    except Exception as e:
                        # Erro no processamento de um ativo específico, não fatal para o robô
                        error_msg = f"Erro ao processar o ativo `{ativo}`: `{e}`"
                        send_message(error_msg, type='ERROR')
                        print(f"\n⚠️ {error_msg}")

            os_time.sleep(10)

    except (MT5ConnectionError, KeyboardInterrupt) as e:
        msg_type = 'FATAL' if isinstance(e, MT5ConnectionError) else 'INFO'
        end_message = f"Robô será encerrado.\nCausa: `{e}`"
        send_message(end_message, type=msg_type)
        print(f"\n🛑 {end_message}")
        
    except Exception as e:
        error_details = traceback.format_exc()
        fatal_message = f"""O robô encontrou um erro fatal!

*Exceção:*
```{e}```

*Traceback:*
```{error_details}```"""
        send_message(fatal_message, type='FATAL')
        print(f"\n💀 ERRO FATAL: {e}")
        traceback.print_exc()

    finally:
        if provider:
            provider.close()
        send_message("Robô Desconectado.", type='INFO')
        print("--- Bot Encerrado ---")

if __name__ == "__main__":
    run_bot()
