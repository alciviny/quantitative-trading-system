import MetaTrader5 as mt5
import pandas as pd
import time
import sys
import os
from datetime import datetime

# --- AJUSTE DE PATH ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa a inteligência do sistema
from src.co_piloto_quant.analysis import calculate_indicators, check_rules
# Importa o Validador de Regime para a Saída de Emergência
from src.co_piloto_quant.risk_regime import validate_market_regime

# --- CONFIGURAÇÕES ---
TIMEFRAME = mt5.TIMEFRAME_M15  # Gráfico de 15 minutos
MAGIC_NUMBER = 777
DEVIATION = 20
MAX_ATIVOS = 10  # Limite para não travar

def conectar_mt5():
    if not mt5.initialize():
        print(f"❌ Falha ao iniciar MT5: {mt5.last_error()}")
        return False
    print(f"✅ Conectado ao MT5. Conta: {mt5.account_info().login}")
    return True

def obter_ativos_visiveis():
    """Retorna ativos da Observação de Mercado com filtro e limite."""
    symbols = mt5.symbols_get(visible=True)
    if not symbols:
        print("⚠️ Nenhum ativo visível na 'Observação de Mercado'!")
        return []
    
    todos_nomes = [s.name for s in symbols]
    
    # Filtra apenas ativos principais para evitar lixo
    ativos_filtrados = [
        nome for nome in todos_nomes 
        if any(x in nome for x in ['USD', 'EUR', 'BRL', 'BTC', 'XAU', 'WIN', 'WDO'])
    ]
    
    ativos_finais = ativos_filtrados[:MAX_ATIVOS]
    print(f"📋 Monitorando {len(ativos_finais)} ativos: {ativos_finais}")
    return ativos_finais

def buscar_dados_mt5(symbol, timeframe, n_barras=300):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_barras)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    df.set_index('time', inplace=True)
    return df

def calcular_lote_minimo(symbol):
    info = mt5.symbol_info(symbol)
    if not info: return 0.01
    return info.volume_min

def checar_posicao_aberta(symbol):
    """Retorna True se existe posição aberta para o ativo."""
    positions = mt5.positions_get(symbol=symbol)
    if positions and len(positions) > 0:
        return True
    return False

def obter_filling_mode(symbol):
    """
    Descobre qual modo de preenchimento a corretora aceita para este ativo.
    Evita o erro 10030 (Unsupported filling mode).
    """
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return mt5.ORDER_FILLING_FOK  # Fallback padrão
        
    filling = symbol_info.filling_mode

    # Tenta encontrar o melhor modo disponível na ordem de prioridade
    if filling & mt5.ORDER_FILLING_IOC:
        return mt5.ORDER_FILLING_IOC
    elif filling & mt5.ORDER_FILLING_FOK:
        return mt5.ORDER_FILLING_FOK
    elif filling & mt5.ORDER_FILLING_RETURN:
        return mt5.ORDER_FILLING_RETURN
    
    return mt5.ORDER_FILLING_IOC # Se nada for detectado, tenta IOC

def fechar_posicao_emergencia(symbol, motivo):
    positions = mt5.positions_get(symbol=symbol)
    if not positions: return

    print(f"🚨 EMERGÊNCIA: Fechando {symbol} por {motivo}...")
    
    # Descobre o modo correto
    filling_type = obter_filling_mode(symbol)

    for pos in positions:
        tipo_fechamento = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if tipo_fechamento == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": pos.volume,
            "type": tipo_fechamento,
            "position": pos.ticket,
            "price": price,
            "deviation": DEVIATION,
            "magic": MAGIC_NUMBER,
            "comment": "Exit: Toxic Regime",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": filling_type,
        }
        
        result = mt5.order_send(request)
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"   ❌ Falha ao fechar {symbol}: {result.comment}")
        else:
            print(f"   ✅ Posição {pos.ticket} encerrada com sucesso.")

def enviar_ordem(ticker, tipo, sinal):
    info = mt5.symbol_info(ticker)
    if not info:
        return

    # --- CHECAGEM DE SESSÃO DE TRADING (EVITA ERROS DE MERCADO FECHADO) ---
    is_buy = tipo == mt5.ORDER_TYPE_BUY
    trade_mode = info.trade_mode

    if trade_mode == mt5.SYMBOL_TRADE_MODE_DISABLED:
        return
        
    if trade_mode == mt5.SYMBOL_TRADE_MODE_CLOSEONLY:
        return

    if is_buy and trade_mode == mt5.SYMBOL_TRADE_MODE_SHORTONLY:
        return

    if not is_buy and trade_mode == mt5.SYMBOL_TRADE_MODE_LONGONLY:
        return
        
    tick = mt5.symbol_info_tick(ticker)
    if not tick: return
    
    lote = calcular_lote_minimo(ticker)
    price = tick.ask if tipo == mt5.ORDER_TYPE_BUY else tick.bid
    sl = sinal.get('Stop_Loss_Sugerido_Long') if tipo == mt5.ORDER_TYPE_BUY else sinal.get('Stop_Loss_Sugerido_Short')
    
    # Descobre o modo correto
    filling_type = obter_filling_mode(ticker)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": float(lote),
        "type": tipo,
        "price": price,
        "sl": float(sl) if sl else 0.0,
        "deviation": DEVIATION,
        "magic": MAGIC_NUMBER,
        "comment": "SmartBot Entry",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling_type,
    }
    
    print(f"🚀 Enviando ordem {ticker} (Lote: {lote} | Mode: {filling_type})...")
    ret = mt5.order_send(request)
    
    if ret.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"   ❌ Erro MT5: {ret.comment} ({ret.retcode})")
        # Se der erro de Invalid Filling mesmo assim, tenta FOK na força bruta
        if ret.retcode == 10030:
            print("      ⚠️ Tentando forçar modo FOK...")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            ret_fok = mt5.order_send(request)
            if ret_fok.retcode != mt5.TRADE_RETCODE_DONE:
                print(f"         ❌ Erro FOK: {ret_fok.comment} ({ret_fok.retcode})")
            else:
                print(f"         ✅ Ordem FOK Executada! Ticket: {ret_fok.order}")
    else:
        print(f"   ✅ Ordem Executada! Ticket: {ret.order}")

def gerenciar_ativo(ticker):
    """
    Função Mestra: 
    1. Se tem posição -> Verifica se precisa sair (Regime Tóxico).
    2. Se não tem -> Verifica se pode entrar (Sinal Técnico).
    """
    # 1. Busca Dados
    df = buscar_dados_mt5(ticker, TIMEFRAME)
    if df.empty or len(df) < 100: return

    # 2. Calcula Inteligência (Indicadores + Regime)
    try:
        df_calc = calculate_indicators(df)
        
        # --- CHECAGEM DE REGIME (O GUARDIÃO) ---
        # Verifica se o mercado está seguro (Hurst, Entropia, VolVol)
        # Passamos o DataFrame completo para ele calcular os Z-Scores históricos
        regime = validate_market_regime(df_calc)
        
    except Exception as e:
        # Se der erro de cálculo, melhor não fazer nada
        # print(f"Erro calc {ticker}: {e}")
        return

    # 3. TOMADA DE DECISÃO
    tem_posicao = checar_posicao_aberta(ticker)

    # --- CENÁRIO A: JÁ ESTAMOS POSICIONADOS ---
    if tem_posicao:
        # Se o regime foi reprovado (Tóxico), sai imediatamente!
        if not regime['approved']:
            fechar_posicao_emergencia(ticker, motivo=regime['reason'])
        else:
            # Se o regime está ok, deixa o trade rolar (Stop Loss/Take Profit da corretora cuidam)
            # print(f"🛡️ {ticker}: Posição mantida. Regime seguro.")
            pass

    # --- CENÁRIO B: ESTAMOS LÍQUIDOS (PROCURANDO ENTRADA) ---
    else:
        # Só olhamos entrada se o regime estiver aprovado
        if regime['approved']:
            sinal = check_rules(df_calc)
            
            # Executa Entrada
            if sinal['Sinal_Compra']:
                enviar_ordem(ticker, mt5.ORDER_TYPE_BUY, sinal)
            elif sinal['Sinal_Venda']:
                enviar_ordem(ticker, mt5.ORDER_TYPE_SELL, sinal)
            else:
                # print(f"⚪ {ticker}: Neutro")
                pass
        else:
            # Regime reprovado, ignora o ativo
            # print(f"⛔ {ticker}: Bloqueado pelo Regime ({regime['reason']})")
            pass

def run_universal_bot():
    if not conectar_mt5(): return

    print("\n🌍 --- SMART BOT LIVE (COM SAÍDA DE EMERGÊNCIA) ---")
    
    try:
        while True:
            print(f"\n🔄 Scanner {datetime.now().strftime('%H:%M:%S')} ------------------------")
            
            ativos = obter_ativos_visiveis()
            
            for ativo in ativos:
                gerenciar_ativo(ativo)
            
            print("💤 Aguardando 15 segundos...")
            time.sleep(15)

    except KeyboardInterrupt:
        print("\n🛑 Bot parado.")
        mt5.shutdown()

if __name__ == "__main__":
    run_universal_bot()
