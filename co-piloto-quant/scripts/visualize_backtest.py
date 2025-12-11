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
from co_piloto_quant.utils.math_tools import safe_join, calculate_z_score
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.strategies.loader import load_strategy


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

    print("🧮  Calculando todos os indicadores necessários para a estratégia...")
    
    # 1. Configurar o IndicatorEngine com TODOS os indicadores que a(s) estratégia(s) podem usar
    engine = IndicatorEngine(df)
    engine.add_indicator(
        'bollinger_bands', 
        period=config.BB_PERIOD, 
        std_devs=[config.BB_ENTRY_STD_DEV_DEFAULT, 2.0] # Adiciona os dois desvios usados
    ).add_indicator(
        'stochastic',
        k_period=config.STOCH_K_PERIOD, # Usa o K do config, não mais o visual
        k_smooth=config.STOCH_K_SMOOTH,
        d_smooth=config.STOCH_D_SMOOTH
    ).add_indicator(
        'system_tpm',
        indicator='obtr',
        period=config.SYSTEM_PERIOD
    ).add_indicator(
        'system_tpm',
        indicator='wad',
        period=config.SYSTEM_PERIOD
    ).add_indicator(
        'wwma',
        period=200
    ).add_indicator(
        'wwma',
        period=20
    ).add_indicator(
        'volatility',
        period=21 # Período padrão de mercado
    ).add_indicator(
        'hurst',
        window=config.HURST_WINDOW,
        kind='price'
    ).add_indicator(
        'entropy',
        window=config.ENTROPY_WINDOW
    )
    
    df = engine.get_data() # Pega o DF final com TODOS os indicadores
    print("✅ Indicadores calculados.")


    print("🧮  Calculando Z-Scores...")
    # O cálculo do Z-Score foi movido para fora do IndicatorEngine
    
    # Nomes das colunas originais
    hurst_col = IndicatorNames.hurst(config.HURST_WINDOW, kind='price')
    entropy_col = IndicatorNames.entropy(config.ENTROPY_WINDOW)
    
    # Nomes das novas colunas de Z-Score
    hurst_z_col = IndicatorNames.hurst_z(config.HURST_WINDOW, kind='price')
    entropy_z_col = IndicatorNames.entropy_z(config.ENTROPY_WINDOW)

    if hurst_col in df.columns:
        df[hurst_z_col] = calculate_z_score(df[hurst_col], window=config.HURST_WINDOW)
        print(f"  -> Z-Score para '{hurst_col}' calculado em '{hurst_z_col}'.")
    else:
        print(f"  ⚠️  Aviso: Coluna '{hurst_col}' não encontrada para calcular Z-Score.")

    if entropy_col in df.columns:
        df[entropy_z_col] = calculate_z_score(df[entropy_col], window=config.ENTROPY_WINDOW)
        print(f"  -> Z-Score para '{entropy_col}' calculado em '{entropy_z_col}'.")
    else:
        print(f"  ⚠️  Aviso: Coluna '{entropy_col}' não encontrada para calcular Z-Score.")
    print("✅ Z-Scores calculados.")


    # --- LÓGICA DE BACKTEST CENTRALIZADA (STRATEGY PATTERN) ---
    print(f"🔌 Carregando a estratégia '{config.ACTIVE_STRATEGY}'...")
    check_rules = load_strategy(mode='vectorized')

    print("♟️  Executando a lógica da estratégia de forma vetorial...")
    sinais = check_rules(df)

    entries = sinais.get('entries', pd.Series(False, index=df.index))
    exits = sinais.get('exits', pd.Series(False, index=df.index))
    short_entries = sinais.get('short_entries', pd.Series(False, index=df.index))
    short_exits = sinais.get('short_exits', pd.Series(False, index=df.index))


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
    print(f" RESULTADO BACKTEST: {ATIVO} com Estratégia: {config.ACTIVE_STRATEGY}")
    print("="*40)
    print(f"Retorno Total: {pf.total_return():.2%}")
    print(f"Win Rate:      {pf.trades.win_rate():.2%}")
    print(f"Total Trades:  {pf.trades.count()}")
    print(f"Sharpe Ratio:  {pf.sharpe_ratio():.2f}")
    print("="*40)
    print("👉 Abrindo gráfico no navegador...")

    # Plota o gráfico, mas adiciona os indicadores-chave da estratégia para visualização
    fig = pf.plot(subplots=[
        ('price', dict(
            title=f"{ATIVO} - Estratégia: {config.ACTIVE_STRATEGY}",
            yaxis_title='Preço'
        )),
        ('orders', dict(
            title='Ordens de Compra e Venda'
        )),
        (IndicatorNames.stochastic_k(config.STOCH_K_PERIOD, config.STOCH_K_SMOOTH), dict(
            title='Estocástico',
            yaxis_title='Valor'
        )),
        ('cum_returns', dict(
            title='Retorno Acumulado',
            yaxis_title='Percentual (%)'
        ))
    ])
    
    # Adiciona as bandas de bollinger ao gráfico de preço
    bb_upper_exit = IndicatorNames.bollinger_upper(config.BB_PERIOD, 2.0)
    bb_lower_exit = IndicatorNames.bollinger_lower(config.BB_PERIOD, 2.0)
    fig.add_scatter(y=df[bb_upper_exit], name='BB Upper (Exit)', row=1, col=1)
    fig.add_scatter(y=df[bb_lower_exit], name='BB Lower (Exit)', row=1, col=1)

    fig.show()

if __name__ == "__main__":
    executar_visualizacao()
