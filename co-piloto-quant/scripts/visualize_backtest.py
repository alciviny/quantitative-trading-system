import MetaTrader5 as mt5
import pandas as pd
import vectorbt as vbt
import sys
import os
import plotly.io as pio

# --- CONFIGURAÇÃO DE AMBIENTE ---
# Isso faz o gráfico abrir no navegador padrão
pio.renderers.default = "browser"

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.co_piloto_quant.analysis import calculate_indicators

# --- PARÂMETROS ---
ATIVO = "EURUSD"       # Qual ativo testar (Tem que estar no Market Watch do MT5)
TIMEFRAME = mt5.TIMEFRAME_H1 # Timeframe (H1, M15, D1)
BARRAS = 5000          # Quantidade de candles para voltar no tempo
SALDO_INICIAL = 10000

def conectar_mt5():
    if not mt5.initialize():
        print(f"❌ Erro MT5: {mt5.last_error()}")
        return False
    return True

def buscar_dados_mt5(symbol, timeframe, n_barras):
    """Busca dados direto do MT5 para o backtest"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_barras)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    
    # Padronizar nomes para minúsculo (close, open, high, low)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df

def get_pandas_freq(mt5_timeframe):
    """Converte o timeframe do MT5 para uma string de frequência do Pandas."""
    freq_map = {
        mt5.TIMEFRAME_M1: "1T",
        mt5.TIMEFRAME_M5: "5T",
        mt5.TIMEFRAME_M15: "15T",
        mt5.TIMEFRAME_M30: "30T",
        mt5.TIMEFRAME_H1: "H",
        mt5.TIMEFRAME_H4: "4H",
        mt5.TIMEFRAME_D1: "D",
        mt5.TIMEFRAME_W1: "W",
        mt5.TIMEFRAME_MN1: "M",
    }
    return freq_map.get(mt5_timeframe)


def executar_visualizacao():
    if not conectar_mt5(): return

    print(f"📥 Baixando {BARRAS} candles de {ATIVO} do MT5...")
    df = buscar_dados_mt5(ATIVO, TIMEFRAME, BARRAS)
    
    if df.empty:
        print("❌ Nenhum dado encontrado. Verifique se o ativo está na Observação de Mercado.")
        return

    print("🧮 Calculando Indicadores e Sinais (Hurst, Entropia, BB)...")
    # Calcula todos os indicadores (pode demorar um pouco dependendo do PC)
    df = calculate_indicators(df)
    
    # --- REPLICAÇÃO DA LÓGICA DE BACKTEST (Mesma do run_backtest.py) ---
    # Aqui aplicamos as regras de forma vetorizada para o gráfico
    
    # 1. Filtros de Regime
    regime_ok = (
        (df['Hurst_72_returns'] >= 0.53) & 
        (df['Entropy_20'] <= 3.2) &
        (df['HalfLife_60'] >= 15)
    )
    
    # 2. Sinais de Compra (Long)
    zona_compra = (df['close'] >= df['BB_Lower_200_0.45']) & (df['close'] <= df['BB_Upper_200_0.45'])
    stoch_compra = df['stoch_k_80_3'] < 30
    entries = regime_ok & zona_compra & stoch_compra

    # 3. Sinais de Venda (Short) - Opcional, se quiser ver só Long comente isso
    zona_venda = (df['close'] >= df['BB_Lower_200_0.45']) & (df['close'] <= df['BB_Middle_200'])
    stoch_venda = df['stoch_k_80_3'] > 70
    short_entries = regime_ok & zona_venda & stoch_venda
    
    # 4. Saídas (Exits)
    # Sai se tocar na banda oposta ou se o regime ficar ruim
    exits = (df['close'] >= df['BB_Upper_200_2.0']) | (~regime_ok)
    short_exits = (df['close'] <= df['BB_Lower_200_2.0']) | (~regime_ok)

    # Limpeza de sinais (Shift para não operar no futuro)
    entries = entries.vbt.signals.fshift()
    exits = exits.vbt.signals.fshift()
    short_entries = short_entries.vbt.signals.fshift()
    short_exits = short_exits.vbt.signals.fshift()

    print("📊 Gerando Gráfico Interativo...")
    
    # Converte o timeframe do MT5 para a frequência do Pandas para o cálculo do Sharpe Ratio
    freq_str = get_pandas_freq(TIMEFRAME)
    if freq_str is None:
        print(f"⚠️  Aviso: Timeframe {TIMEFRAME} não mapeado. O Sharpe Ratio pode falhar.")

    # Cria o Portfólio VectorBT
    pf = vbt.Portfolio.from_signals(
        df['close'], 
        entries=entries, 
        exits=exits, 
        short_entries=short_entries, 
        short_exits=short_exits,
        freq=freq_str,
        init_cash=SALDO_INICIAL,
        fees=0.0006, # Taxas estimadas
        slippage=0.001 # Slippage estimado
    )

    # Mostra Estatísticas no Terminal
    print("\n" + "="*40)
    print(f" RESULTADO BACKTEST: {ATIVO}")
    print("="*40)
    print(f"Retorno Total: {pf.total_return():.2%}")
    print(f"Win Rate:      {pf.trades.win_rate():.2%}")
    print(f"Total Trades:  {pf.trades.count()}")
    print(f"Sharpe Ratio:  {pf.sharpe_ratio():.2f}")
    print("="*40)
    print("👉 Abrindo gráfico no navegador...")

    # Plota o gráfico completo
    # O subplot 'orders' mostra setas de compra/venda
    # O subplot 'trade_pnl' mostra lucro/prejuízo
    fig = pf.plot(subplots=['orders', 'cum_returns'])
    fig.show()

if __name__ == "__main__":
    executar_visualizacao()