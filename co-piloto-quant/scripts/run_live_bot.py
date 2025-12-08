import MetaTrader5 as mt5
import pandas as pd
import time as os_time
from datetime import datetime, time
import sys
import os
from pathlib import Path

# --- AJUSTE DE PATH E IMPORTS ---
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

from co_piloto_quant.config import (
    MT5_MAGIC_NUMBER, MT5_DEVIATION, MT5_MAX_POSITIONS, 
    TRADING_WHITELIST, FIXED_LOT_SIZE
)
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy
from co_piloto_quant.risk_regime import validate_market_regime

# --- CONSTANTES DE ROBUSTEZ ---
MAX_SPREAD_POINTS = 15.0       # Em pontos (ex: 15 para WIN, 1.5 para WDO)
TRADING_START_HOUR = 9
TRADING_START_MIN = 15
TRADING_END_HOUR = 16
TRADING_END_MIN = 50
BREAKEVEN_PROFIT_MULTIPLIER = 1.5 # Move SL para o breakeven quando o lucro for 1.5x o risco

# --- MAPA DE TIMEFRAMES ---
MT5_TIMEFRAME_STR = "M15"
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1
}
CURRENT_TIMEFRAME = TIMEFRAME_MAP.get(MT5_TIMEFRAME_STR, mt5.TIMEFRAME_M15) 

strategy_engine = AdaptiveSniperStrategy()

def is_trading_hours():
    """Verifica se o horário atual está dentro da janela de operação."""
    now = datetime.now().time()
    start_time = time(TRADING_START_HOUR, TRADING_START_MIN)
    end_time = time(TRADING_END_HOUR, TRADING_END_MIN)
    return start_time <= now <= end_time

def conectar_mt5():
    if not mt5.initialize():
        print(f"❌ Falha ao iniciar MT5: {mt5.last_error()}")
        return False
    print(f"✅ Conectado ao MT5. Conta: {mt5.account_info().login}")
    return True

def obter_ativos_monitorados():
    if TRADING_WHITELIST:
        print(f"📋 Usando Whitelist do Config: {TRADING_WHITELIST}")
        for sym in TRADING_WHITELIST: mt5.symbol_select(sym, True)
        return TRADING_WHITELIST

    symbols = mt5.symbols_get(group="!*.ECN") # Exemplo: pega tudo, menos os de extensão .ECN
    if not symbols: return []
    return [s.name for s in symbols]

def buscar_dados_mt5(symbol, timeframe, n_barras=300):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_barras)
    if rates is None or len(rates) == 0: return pd.DataFrame()
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df.set_index('time', inplace=True)
    return df[['open', 'high', 'low', 'close', 'volume']]

def obter_filling_mode(symbol):
    s_info = mt5.symbol_info(symbol)
    if not s_info: return mt5.ORDER_FILLING_FOK
    if s_info.filling_mode & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_FOK

def executar_ordem(symbol, tipo_ordem, signal_data):
    """Envia a ordem para o MT5 com checagens de robustez."""
    
    # 1. GESTÃO DE ORDENS PENDENTES E POSIÇÕES
    if (mt5.positions_total() + mt5.orders_total()) >= MT5_MAX_POSITIONS:
        print(f"⛔ Limite de operações ({MT5_MAX_POSITIONS}) atingido. Ignorando {symbol}.")
        return
    if mt5.orders_get(symbol=symbol):
        print(f"🟡 Já existe ordem pendente para {symbol}. Aguardando.")
        return

    tick = mt5.symbol_info_tick(symbol)
    symbol_info = mt5.symbol_info(symbol)
    if not tick or not symbol_info: return

    # 2. PROTEÇÃO DE SPREAD
    spread = (tick.ask - tick.bid)
    spread_points = spread / symbol_info.point
    if spread_points > MAX_SPREAD_POINTS:
        print(f"📈 Spread alto para {symbol}: {spread_points:.1f} pts (Limite: {MAX_SPREAD_POINTS}). Abortando.")
        return

    price = tick.ask if tipo_ordem == mt5.ORDER_TYPE_BUY else tick.bid
    sl = signal_data.get('STOP_LOSS', 0.0)
    if not sl or pd.isna(sl):
        dist = price * 0.01
        sl = price - dist if tipo_ordem == mt5.ORDER_TYPE_BUY else price + dist

    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(FIXED_LOT_SIZE),
        "type": tipo_ordem, "price": price, "sl": float(sl), "deviation": MT5_DEVIATION,
        "magic": MT5_MAGIC_NUMBER, "comment": f"Sniper {strategy_engine.get_name()}",
        "type_time": mt5.ORDER_TIME_GTC, "type_filling": obter_filling_mode(symbol),
    }
    
    print(f"🚀 ENVIANDO ORDEM: {symbol} | {request['volume']} lots | SL: {sl}")
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Erro MT5: {result.comment} ({result.retcode})")
    else:
        print(f"✅ Ordem Executada! Ticket: {result.order}")

def fechar_posicao_emergencia(position, motivo):
    tick = mt5.symbol_info_tick(position.symbol)
    if not tick: return
    price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
    request = {
        "action": mt5.TRADE_ACTION_DEAL, "symbol": position.symbol, "volume": position.volume,
        "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
        "position": position.ticket, "price": price, "magic": MT5_MAGIC_NUMBER,
        "comment": f"Exit: {motivo}", "type_filling": obter_filling_mode(position.symbol)
    }
    mt5.order_send(request)
    print(f"🚨 Posição {position.ticket} ({position.symbol}) encerrada. Motivo: {motivo}")

def monitorar_posicoes_abertas():
    """Gerencia posições abertas, aplicando lógicas como Trailing Stop e Breakeven."""
    positions = mt5.positions_get()
    if not positions: return

    for pos in positions:
        if pos.magic != MT5_MAGIC_NUMBER: continue

        initial_risk = abs(pos.price_open - pos.sl)
        if initial_risk == 0: continue

        profit = 0
        if pos.type == mt5.ORDER_TYPE_BUY: # Posição Comprada
            profit = pos.price_current - pos.price_open
            if pos.sl >= pos.price_open: continue
        elif pos.type == mt5.ORDER_TYPE_SELL: # Posição Vendida
            profit = pos.price_open - pos.price_current
            if pos.sl <= pos.price_open: continue

        if profit >= (initial_risk * BREAKEVEN_PROFIT_MULTIPLIER):
            request = {
                "action": mt5.TRADE_ACTION_SLTP, "position": pos.ticket,
                "sl": pos.price_open, "magic": MT5_MAGIC_NUMBER
            }
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ BREAKEVEN ATIVADO para {pos.symbol} (Ticket: {pos.ticket})")
            else:
                print(f"❌ Falha ao mover SL para Breakeven em {pos.symbol}: {result.comment}")

def processar_ativo(symbol):
    """Ciclo de análise para decidir se ABRE uma nova posição."""
    df = buscar_dados_mt5(symbol, CURRENT_TIMEFRAME, n_barras=300)
    if df.empty or len(df) < 200: return

    try:
        df_indic = calculate_indicators(df)
        df_analyzed = strategy_engine.evaluate(df_indic)
        latest = df_analyzed.iloc[-1]
    except Exception as e:
        print(f"⚠️ Erro ao analisar {symbol}: {e}"); return

    positions = mt5.positions_get(symbol=symbol)
    has_position = len(positions) > 0 if positions else False
    
    hurst_z = latest.get('Hurst_Z', 0)
    entropy_z = latest.get('Entropy_Z', 0)
    is_regime_toxic = (entropy_z > 2.0)
    
    if has_position and is_regime_toxic:
        for pos in positions: fechar_posicao_emergencia(pos, "Regime Tóxico")
        return

    if not has_position and not is_regime_toxic:
        signal = latest.get('SIGNAL', 'HOLD')
        if signal == 'BUY':
            executar_ordem(symbol, mt5.ORDER_TYPE_BUY, latest)
        elif signal == 'SELL':
            # No modo live, um sinal de SELL da estratégia pode ser ignorado ou
            # interpretado como uma ordem de venda real (short).
            # Por segurança, vamos ignorar por enquanto.
            pass

def run_bot():
    if not conectar_mt5(): return
    
    print("\n💀 --- ADAPTIVE SNIPER BOT INICIADO (v2 Robustez) ---")
    print(f"🔧 Config: Timeframe {MT5_TIMEFRAME_STR} | Magic {MT5_MAGIC_NUMBER} | Max Spread: {MAX_SPREAD_POINTS} pts")
    
    ativos = obter_ativos_monitorados()
    print(f"👁️  Monitorando {len(ativos)} ativos. Janela de Trading: {TRADING_START_HOUR:02d}:{TRADING_START_MIN:02d} - {TRADING_END_HOUR:02d}:{TRADING_END_MIN:02d}")

    try:
        while True:
            try:
                monitorar_posicoes_abertas()
            except Exception as e:
                print(f"Erro no monitoramento de posições: {e}")

            if is_trading_hours():
                print(f".", end="", flush=True)
                for ativo in ativos:
                    try: processar_ativo(ativo)
                    except Exception as e: print(f"Erro em {ativo}: {e}")
            else:
                 print(f"z", end="", flush=True)
            
            os_time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Bot Parado pelo Usuário.")
        mt5.shutdown()

if __name__ == "__main__":
    run_bot()