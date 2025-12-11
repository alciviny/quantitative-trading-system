import MetaTrader5 as mt5
import pandas as pd
import vectorbt as vbt
import sys
import os
import plotly.io as pio

# --- CONFIGURAÇÃO DE AMBIENTE ---
pio.renderers.default = "browser"

# Adiciona o diretório src ao path para permitir importações do projeto
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)


# --- NOVAS IMPORTAÇÕES ---
from co_piloto_quant.data.indicator_engine import IndicatorEngine
from co_piloto_quant import config
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params
from co_piloto_quant.utils.math_tools import safe_join
from co_piloto_quant.indicators.names import IndicatorNames


# --- PARÂMETROS ---
ATIVO = "EURUSD"
TIMEFRAME = mt5.TIMEFRAME_H1
BARRAS = 5000
SALDO_INICIAL = 10000

# Parâmetros específicos da lógica de visualização
STOCH_K_VISUAL = 80
HURST_WINDOW_VISUAL = 72
ENTROPY_WINDOW_VISUAL = 20
HALFLIFE_WINDOW_VISUAL = 60


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
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    return df

def get_pandas_freq(mt5_timeframe):
    """Converte o timeframe do MT5 para uma string de frequência do Pandas."""
    freq_map = {
        mt5.TIMEFRAME_M1: "1T", mt5.TIMEFRAME_M5: "5T", mt5.TIMEFRAME_M15: "15T",
        mt5.TIMEFRAME_M30: "30T", mt5.TIMEFRAME_H1: "h", mt5.TIMEFRAME_H4: "4h",
        mt5.TIMEFRAME_D1: "d", mt5.TIMEFRAME_W1: "W", mt5.TIMEFRAME_MN1: "M",
    }
    return freq_map.get(mt5_timeframe)


def executar_visualizacao():
    if not conectar_mt5(): return

    print(f"📥 Baixando {BARRAS} candles de {ATIVO} do MT5...")
    df = buscar_dados_mt5(ATIVO, TIMEFRAME, BARRAS)
    
    if df.empty or len(df) < 200:
        print("❌ Nenhum dado encontrado ou dados insuficientes. Verifique se o ativo está na Observação de Mercado.")
        return

    print("🧮  Calculando Indicadores com a nova arquitetura...")
    
    # --- ARQUITETURA REATORADA ---
    # 1. Usar o IndicatorEngine para indicadores padrão
    engine = IndicatorEngine(df)
    engine.add_indicator(
        'bollinger_bands', 
        period=config.BB_PERIOD, 
        std_devs=config.PRICE_BB_DEVIATIONS # Usa a lista completa do config
    ).add_indicator(
        'stochastic',
        k_period=STOCH_K_VISUAL, # Usa o período específico da visualização (80)
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=3 # Usa o D=3 que estava implícito na lógica anterior
    )
    df = engine.get_data()

    # 2. Manter cálculo manual para indicadores "especiais" por enquanto
    print("🔬 Calculando indicadores especiais (Hurst, Entropia, Half-Life)...")
    hurst = calculate_rolling_hurst(df['close'], window=HURST_WINDOW_VISUAL, kind='returns')
    df = safe_join(df, pd.DataFrame(hurst))
    
    entropy_col = IndicatorNames.entropy(ENTROPY_WINDOW_VISUAL)
    entropy_series = calculate_rolling_entropy(df['close'], window=ENTROPY_WINDOW_VISUAL)
    df[entropy_col] = entropy_series

    ou_stats = calculate_rolling_ou_params(df['close'], window=HALFLIFE_WINDOW_VISUAL)
    df = safe_join(df, ou_stats)
    # --- FIM DA ARQUITETURA REATORADA ---

    print("✅ Indicadores calculados.")

    # --- REPLICAÇÃO DA LÓGICA DE BACKTEST (Mesma do run_backtest.py) ---
    hurst_col_name = IndicatorNames.hurst(HURST_WINDOW_VISUAL, 'returns')
    halflife_col_name = IndicatorNames.half_life(HALFLIFE_WINDOW_VISUAL)
    stoch_col_name = IndicatorNames.stochastic_k(STOCH_K_VISUAL, config.STOCH_K_SMOOTH)
    bb_lower_squeeze = IndicatorNames.bollinger_lower(config.BB_PERIOD, 0.45)
    bb_upper_squeeze = IndicatorNames.bollinger_upper(config.BB_PERIOD, 0.45)
    bb_middle = IndicatorNames.bollinger_middle(config.BB_PERIOD)
    bb_lower_exit = IndicatorNames.bollinger_lower(config.BB_PERIOD, 2.0)
    bb_upper_exit = IndicatorNames.bollinger_upper(config.BB_PERIOD, 2.0)

    # 1. Filtros de Regime
    regime_ok = (
        (df[hurst_col_name] >= 0.53) & 
        (df[entropy_col] <= 3.2) &
        (df[halflife_col_name] >= 15)
    )
    
    # 2. Sinais de Compra (Long)
    zona_compra = (df['close'] >= df[bb_lower_squeeze]) & (df['close'] <= df[bb_upper_squeeze])
    stoch_compra = df[stoch_col_name] < 30
    entries = regime_ok & zona_compra & stoch_compra

    # 3. Sinais de Venda (Short)
    zona_venda = (df['close'] >= df[bb_lower_squeeze]) & (df['close'] <= df[bb_middle])
    stoch_venda = df[stoch_col_name] > 70
    short_entries = regime_ok & zona_venda & stoch_venda
    
    # 4. Saídas (Exits)
    exits = (df['close'] >= df[bb_upper_exit]) | (~regime_ok)
    short_exits = (df['close'] <= df[bb_lower_exit]) | (~regime_ok)

    # Limpeza de sinais
    entries = entries.vbt.signals.fshift()
    exits = exits.vbt.signals.fshift()
    short_entries = short_entries.vbt.signals.fshift()
    short_exits = short_exits.vbt.signals.fshift()

    print("📊 Gerando Gráfico Interativo...")
    
    freq_str = get_pandas_freq(TIMEFRAME)
    if freq_str is None:
        print(f"⚠️  Aviso: Timeframe {TIMEFRAME} não mapeado para frequência Pandas. Sharpe Ratio pode falhar.")

    pf = vbt.Portfolio.from_signals(
        df['close'], 
        entries=entries, exits=exits, 
        short_entries=short_entries, short_exits=short_exits,
        freq=freq_str,
        init_cash=SALDO_INICIAL,
        fees=0.0006,
        slippage=0.001
    )

    print("\n" + "="*40)
    print(f" RESULTADO BACKTEST: {ATIVO}")
    print("="*40)
    print(f"Retorno Total: {pf.total_return():.2%}")
    print(f"Win Rate:      {pf.trades.win_rate():.2%}")
    print(f"Total Trades:  {pf.trades.count()}")
    print(f"Sharpe Ratio:  {pf.sharpe_ratio():.2f}")
    print("="*40)
    print("👉 Abrindo gráfico no navegador...")

    fig = pf.plot(subplots=['orders', 'cum_returns'])
    fig.show()

if __name__ == "__main__":
    executar_visualizacao()
