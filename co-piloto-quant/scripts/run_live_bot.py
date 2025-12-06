import MetaTrader5 as mt5
import pandas as pd
import time
import sys
import os
from datetime import datetime

# --- AJUSTE DE PATH ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importa a inteligência do seu sistema
from src.co_piloto_quant.analysis import calculate_indicators, check_rules

# --- CONFIGURAÇÕES ---
TIMEFRAME = mt5.TIMEFRAME_M15  # Mudei para M15 para ser mais rápido o teste
MAGIC_NUMBER = 777
DEVIATION = 20
MAX_ATIVOS = 10  # <--- NOVO: Limita a quantidade de ativos para não travar

def conectar_mt5():
    if not mt5.initialize():
        print(f"❌ Falha ao iniciar MT5: {mt5.last_error()}")
        return False
    print(f"✅ Conectado ao MT5. Conta: {mt5.account_info().login}")
    return True

def obter_ativos_visiveis():
    """
    Retorna os ativos da 'Observação de Mercado', mas com FILTRO e LIMITE.
    """
    symbols = mt5.symbols_get(visible=True)
    if not symbols:
        print("⚠️ Nenhum ativo visível na 'Observação de Mercado'!")
        return []
    
    # 1. Converte objetos para lista de nomes
    todos_nomes = [s.name for s in symbols]
    
    # 2. FILTRO INTELIGENTE: Pega apenas o que tem liquidez (USD, EUR, BTC, BRL)
    # Isso evita pegar índices estranhos ou ativos sem dados
    ativos_filtrados = [
        nome for nome in todos_nomes 
        if any(x in nome for x in ['USD', 'EUR', 'BRL', 'BTC', 'XAU'])
    ]
    
    # 3. LIMITADOR: Pega apenas os primeiros 'MAX_ATIVOS' (ex: 10)
    ativos_finais = ativos_filtrados[:MAX_ATIVOS]
    
    print(f"📋 Total detectado: {len(todos_nomes)} | Filtrados: {len(ativos_finais)}")
    print(f"👉 Operando apenas: {ativos_finais}")
    
    return ativos_finais

def buscar_dados_mt5(symbol, timeframe, n_barras=300):
    """Busca dados e formata para o padrão do analysis.py"""
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
    if not info:
        return 0.01
    return info.volume_min

def checar_posicao_aberta(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions and len(positions) > 0:
        return True
    return False

def executar_estrategia(ticker):
    # 1. Busca Dados
    df = buscar_dados_mt5(ticker, TIMEFRAME)
    if df.empty or len(df) < 100:
        return

    # 2. Calcula Indicadores (com proteção de erro)
    try:
        df_calc = calculate_indicators(df)
        sinal = check_rules(df_calc)
    except Exception:
        # Se der erro matemático (comum em ativos ruins), apenas ignora
        return

    # 3. Mostra que está vivo (Feedback visual simples)
    if sinal['Sinal_Compra']:
        print(f"🟢 {ticker}: SINAL DE COMPRA! (Bloqueio: {sinal['Motivo_Bloqueio']})")
    elif sinal['Sinal_Venda']:
        print(f"🔴 {ticker}: SINAL DE VENDA! (Bloqueio: {sinal['Motivo_Bloqueio']})")
    else:
        # Opcional: print(f"⚪ {ticker}: Neutro", end='\r')
        pass

    # 4. Execução REAL
    if checar_posicao_aberta(ticker):
        return

    # Só entra se o sinal for válido (sem bloqueio)
    if not (sinal['Sinal_Compra'] or sinal['Sinal_Venda']):
        return
    
    # Se tiver bloqueio (ex: Hurst baixo), não opera
    if "Reprovado" in sinal.get('Motivo_Bloqueio', ''):
        return

    tick = mt5.symbol_info_tick(ticker)
    if not tick: return

    lote = calcular_lote_minimo(ticker)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": ticker,
        "volume": float(lote),
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
        "magic": MAGIC_NUMBER,
        "deviation": DEVIATION,
        "comment": "UniversalBot",
    }

    tipo = mt5.ORDER_TYPE_BUY if sinal['Sinal_Compra'] else mt5.ORDER_TYPE_SELL
    preco = tick.ask if sinal['Sinal_Compra'] else tick.bid
    sl = sinal.get('Stop_Loss_Sugerido_Long') if sinal['Sinal_Compra'] else sinal.get('Stop_Loss_Sugerido_Short')

    request["type"] = tipo
    request["price"] = preco
    if sl: request["sl"] = sl
    
    print(f"🚀 Enviando ordem para {ticker}...")
    ret = mt5.order_send(request)
    if ret.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"   ❌ Erro MT5: {ret.comment} ({ret.retcode})")
    else:
        print(f"   ✅ Ordem Executada! Ticket: {ret.order}")

def run_universal_bot():
    if not conectar_mt5(): return

    print("\n🌍 --- BOT UNIVERSAL (FILTRADO) ---")
    
    try:
        while True:
            print(f"\n🔄 Scanner {datetime.now().strftime('%H:%M:%S')} ------------------------")
            
            ativos = obter_ativos_visiveis()
            
            for ativo in ativos:
                executar_estrategia(ativo)
            
            print("💤 Aguardando 30 segundos...")
            time.sleep(30)

    except KeyboardInterrupt:
        print("\n🛑 Bot parado.")
        mt5.shutdown()

if __name__ == "__main__":
    run_universal_bot()