import MetaTrader5 as mt5
import pandas as pd
import time
import sys
import os
from datetime import datetime
from pathlib import Path

# --- AJUSTE DE PATH E IMPORTS ---
# Adiciona o diretório src ao path para importar os módulos corretamente
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent / "src"
sys.path.append(str(project_root))

# Importa as Configurações Centralizadas (O Mapa)
from co_piloto_quant.config import (
    MT5_MAGIC_NUMBER, MT5_DEVIATION, MT5_MAX_POSITIONS, 
    TRADING_WHITELIST, FIXED_LOT_SIZE
)

# Importa a Inteligência (O Cérebro)
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy
from co_piloto_quant.risk_regime import validate_market_regime

# --- MAPA DE TIMEFRAMES ---
# TODO: Mover a string do timeframe para o arquivo de configuração (config.py)
MT5_TIMEFRAME_STR = "M15" # Exemplo: "M1", "H1", "D1"

# Mapeia a string do config para a constante do MT5
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1
}
# Define o timeframe usado pegando da variável (ou padrão M15)
CURRENT_TIMEFRAME = TIMEFRAME_MAP.get(MT5_TIMEFRAME_STR, mt5.TIMEFRAME_M15) 

# Instancia a Estratégia UMA VEZ (Singleton)
strategy_engine = AdaptiveSniperStrategy()

def conectar_mt5():
    if not mt5.initialize():
        print(f"❌ Falha ao iniciar MT5: {mt5.last_error()}")
        return False
    print(f"✅ Conectado ao MT5. Conta: {mt5.account_info().login}")
    return True

def obter_ativos_monitorados():
    """Retorna a lista de ativos com base no config ou Market Watch."""
    # Se houver whitelist no config, usa ela
    if TRADING_WHITELIST:
        print(f"📋 Usando Whitelist do Config: {TRADING_WHITELIST}")
        # Garante que estão visíveis no MT5
        for sym in TRADING_WHITELIST:
            mt5.symbol_select(sym, True)
        return TRADING_WHITELIST

    # Caso contrário, pega os visíveis do MT5
    symbols = mt5.symbols_get(visible=True)
    if not symbols:
        print("⚠️ Nenhum ativo visível na 'Observação de Mercado'!")
        return []
    
    ativos = [s.name for s in symbols]
    # Filtro básico para não pegar lixo (opcional)
    ativos_filtrados = [a for a in ativos if not a.endswith(('stat', 'k', 'c'))] # Exemplo de filtro
    
    # Limita quantidade para não sobrecarregar
    limit = 10 
    return ativos_filtrados[:limit]

def buscar_dados_mt5(symbol, timeframe, n_barras=300):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_barras)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df.set_index('time', inplace=True)
    
    # Limpeza básica e renomeação de colunas para padrão do sistema
    df = df[['open', 'high', 'low', 'close', 'volume']]
    return df

def obter_filling_mode(symbol):
    """Detecta o modo de preenchimento da ordem automaticamente."""
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return mt5.ORDER_FILLING_FOK
    
    filling = symbol_info.filling_mode
    if filling & mt5.ORDER_FILLING_IOC: return mt5.ORDER_FILLING_IOC
    if filling & mt5.ORDER_FILLING_FOK: return mt5.ORDER_FILLING_FOK
    if filling & mt5.ORDER_FILLING_RETURN: return mt5.ORDER_FILLING_RETURN
    return mt5.ORDER_FILLING_IOC

def executar_ordem(symbol, tipo_ordem, signal_data):
    """Envia a ordem para o MT5."""
    
    # Verifica limite de posições
    open_positions = mt5.positions_total()
    if open_positions >= MT5_MAX_POSITIONS and tipo_ordem in [mt5.ORDER_TYPE_BUY, mt5.ORDER_TYPE_SELL]:
        print(f"⛔ Limite de posições atingido ({open_positions}/{MT5_MAX_POSITIONS}). Ignorando {symbol}.")
        return

    tick = mt5.symbol_info_tick(symbol)
    if not tick: return

    # Preço de Entrada
    price = tick.ask if tipo_ordem == mt5.ORDER_TYPE_BUY else tick.bid
    
    # Stop Loss (Vindo da Estratégia)
    sl = signal_data.get('STOP_LOSS', 0.0)
    
    # Se o SL for NaN ou 0, aplica um SL de segurança básico (ex: 1% do preço)
    if not sl or pd.isna(sl):
        dist = price * 0.01
        sl = price - dist if tipo_ordem == mt5.ORDER_TYPE_BUY else price + dist

    # Lote (Pega do Config ou calcula)
    volume = FIXED_LOT_SIZE 
    
    filling_type = obter_filling_mode(symbol)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": tipo_ordem,
        "price": price,
        "sl": float(sl),
        "deviation": MT5_DEVIATION,
        "magic": MT5_MAGIC_NUMBER,
        "comment": f"Sniper {strategy_engine.get_name()}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }
    
    print(f"🚀 ENVIANDO ORDEM: {symbol} | {volume} lotes | SL: {sl}")
    result = mt5.order_send(request)
    
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"❌ Erro MT5: {result.comment} ({result.retcode})")
    else:
        print(f"✅ Ordem Executada! Ticket: {result.order}")

def fechar_posicao_emergencia(position, motivo):
    """Fecha uma posição específica se o regime de mercado deteriorar."""
    tick = mt5.symbol_info_tick(position.symbol)
    if not tick: return

    tipo_fechamento = mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    price = tick.bid if tipo_fechamento == mt5.ORDER_TYPE_SELL else tick.ask
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": tipo_fechamento,
        "position": position.ticket,
        "price": price,
        "magic": MT5_MAGIC_NUMBER,
        "comment": f"Exit: {motivo}",
        "type_filling": obter_filling_mode(position.symbol)
    }
    
    mt5.order_send(request)
    print(f"🚨 Posição {position.ticket} ({position.symbol}) encerrada. Motivo: {motivo}")

def processar_ativo(symbol):
    """
    Ciclo completo de inteligência para um ativo.
    """
    # 1. Download de Dados
    df = buscar_dados_mt5(symbol, CURRENT_TIMEFRAME, n_barras=300)
    if df.empty or len(df) < 200: return

    # 2. Cálculo de Indicadores (Usa a mesma func do Scanner)
    # Isso garante que os indicadores sejam matematicamente idênticos
    try:
        df_indic = calculate_indicators(df)
    except Exception as e:
        print(f"⚠️  Erro ao calcular indicadores para {symbol}: {e}")
        return

    # 3. Aplicação da Estratégia (O CÉREBRO)
    # Aqui usamos a classe strategy_engine importada
    try:
        df_analyzed = strategy_engine.evaluate(df_indic)
        latest = df_analyzed.iloc[-1]
    except Exception as e:
        print(f"⚠️  Erro ao avaliar estratégia para {symbol}: {e}")
        return

    # 4. Decisão de Trading
    # Verifica se já temos posição neste ativo
    positions = mt5.positions_get(symbol=symbol)
    has_position = len(positions) > 0 if positions else False
    
    # --- SAÍDA DE EMERGÊNCIA (Risk Regime) ---
    # Verifica a qualidade do regime (Hurst/Entropia)
    # Se o strategy.evaluate rodou, já temos Hurst_Z e Entropy_Z no DataFrame
    hurst_z = latest.get('Hurst_Z', 0)
    entropy_z = latest.get('Entropy_Z', 0)
    
    is_regime_toxic = (entropy_z > 2.0) # Exemplo: Entropia muito alta = Caos
    
    if has_position and is_regime_toxic:
        for pos in positions:
            fechar_posicao_emergencia(pos, "Regime Tóxico Detectado")
        return # Sai da função para não abrir nova ordem

    # --- ENTRADA (Sinais Técnicos) ---
    if not has_position and not is_regime_toxic:
        signal = latest.get('SIGNAL', 'HOLD')
        
        if signal == 'BUY':
            executar_ordem(symbol, mt5.ORDER_TYPE_BUY, latest)
        elif signal == 'SELL':
            executar_ordem(symbol, mt5.ORDER_TYPE_SELL, latest)

def run_bot():
    if not conectar_mt5(): return
    
    print("\n💀 --- ADAPTIVE SNIPER BOT INICIADO ---")
    print(f"🔧 Configuração: Timeframe {MT5_TIMEFRAME_STR} | Magic {MT5_MAGIC_NUMBER}")
    
    ativos = obter_ativos_monitorados()
    print(f"👁️  Monitorando {len(ativos)} ativos.")

    try:
        while True:
            print(f".", end="", flush=True) # Heartbeat visual
            
            for ativo in ativos:
                try:
                    processar_ativo(ativo)
                except Exception as e:
                    print(f"Erro em {ativo}: {e}")
            
            time.sleep(10) # Aguarda 10s entre ciclos

    except KeyboardInterrupt:
        print("\n🛑 Bot Parado pelo Usuário.")
        mt5.shutdown()

if __name__ == "__main__":
    run_bot()