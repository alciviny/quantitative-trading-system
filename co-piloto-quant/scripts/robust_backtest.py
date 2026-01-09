"""
Strategy-Driven Backtester
Save as: scripts/robust_backtest.py

O que faz:
- Carrega um dataset de preços para um ativo específico.
- Processa o dataset para adicionar indicadores técnicos.
- Carrega e instancia dinamicamente uma classe de Estratégia (ex: VolatileMomentumProfessional).
- Executa a lógica da estratégia para gerar sinais de COMPRA/VENDA.
- Simula a execução desses sinais em um loop de backtest simples (não-vetorizado).
- Calcula e exibe as métricas de performance da estratégia.
"""

import importlib
import logging
import pandas as pd
import numpy as np
from pathlib import Path

# Supondo que essas funções existem e estão acessíveis
# Se elas não estiverem no path, pode ser necessário ajustar o sys.path
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.data.data_processing import process_data
from co_piloto_quant.strategies.base import Strategy

# --------------------------
# Config
# --------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('StrategyBacktester')

# --- Parâmetros do Backtest ---
TICKER = 'PETR4'  # Ativo para testar
STRATEGY_CLASS_NAME = 'VolatileMomentumProfessional'  # Nome da classe da Estratégia
STRATEGY_MODULE_PATH = 'co_piloto_quant.strategies.volatile_momentum_professional' # Caminho para o módulo da estratégia
INITIAL_CAPITAL = 100_000
COMMISSION_PER_TRADE_PCT = 0.001 # 0.1% por operação (compra/venda)

# --------------------------
# Carregador de Estratégia
# --------------------------

def load_strategy(module_path: str, class_name: str) -> Strategy:
    """Carrega dinamicamente uma classe de estratégia a partir de seu módulo e nome."""
    try:
        module = importlib.import_module(module_path)
        strategy_class = getattr(module, class_name)
        return strategy_class() # Instancia com parâmetros padrão
    except (ImportError, AttributeError) as e:
        logger.error(f"Não foi possível carregar a estratégia '{class_name}' de '{module_path}': {e}")
        raise

# --------------------------
# Motor de Backtest Simples
# --------------------------

def run_simple_backtest(df_signals: pd.DataFrame, initial_capital: float, commission_pct: float):
    """
    Executa um backtest iterativo baseado nos sinais de uma estratégia.
    """
    if 'SIGNAL' not in df_signals.columns:
        raise ValueError("O DataFrame de sinais precisa conter a coluna 'SIGNAL'.")

    trades = []
    position = None  # None, 'LONG', or 'SHORT'
    entry_price = 0
    entry_date = None
    stop_loss = None
    profit_target = None
    max_hold_days = 7 # Padrão da estratégia, pode ser pego da instância no futuro

    for i, row in df_signals.iterrows():
        # --- Lógica de Saída de Posição ---
        if position:
            exit_price = None
            exit_reason = None
            
            # 1. Checar Stop Loss
            if position == 'LONG' and row['low'] <= stop_loss:
                exit_price = stop_loss
                exit_reason = 'STOP_LOSS'
            elif position == 'SHORT' and row['high'] >= stop_loss:
                exit_price = stop_loss
                exit_reason = 'STOP_LOSS'

            # 2. Checar Profit Target
            if exit_price is None:
                if position == 'LONG' and row['high'] >= profit_target:
                    exit_price = profit_target
                    exit_reason = 'PROFIT_TARGET'
                elif position == 'SHORT' and row['low'] <= profit_target:
                    exit_price = profit_target
                    exit_reason = 'PROFIT_TARGET'

            # 3. Checar Tempo Máximo de Posição
            if exit_price is None and (row.name - entry_date).days >= max_hold_days:
                exit_price = row['close']
                exit_reason = 'MAX_HOLD_DAYS'

            # 4. Checar Sinal de Saída (Oposto)
            if exit_price is None:
                if position == 'LONG' and row['SIGNAL'] == 'SELL':
                    exit_price = row['close']
                    exit_reason = 'SIGNAL_EXIT'
                elif position == 'SHORT' and row['SIGNAL'] == 'BUY':
                    exit_price = row['close']
                    exit_reason = 'SIGNAL_EXIT'

            if exit_price:
                # Calcular resultado do trade
                if position == 'LONG':
                    pnl = (exit_price - entry_price) / entry_price
                else: # SHORT
                    pnl = (entry_price - exit_price) / entry_price
                
                # Aplicar custos
                pnl -= 2 * commission_pct # Custo de entrada e saída
                
                trades.append({
                    'entry_date': entry_date,
                    'exit_date': row.name,
                    'position_type': position,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'pnl_pct': pnl,
                    'exit_reason': exit_reason
                })
                position, entry_price, entry_date, stop_loss, profit_target = None, 0, None, None, None

        # --- Lógica de Entrada de Posição ---
        if not position:
            if row['SIGNAL'] == 'BUY':
                position = 'LONG'
                entry_price = row['close'] # Simplificação: assume entrada no fechamento
                entry_date = row.name
                stop_loss = row['STOP_LOSS']
                profit_target = row['PROFIT_TARGET']
            elif row['SIGNAL'] == 'SELL':
                position = 'SHORT'
                entry_price = row['close']
                entry_date = row.name
                stop_loss = row['STOP_LOSS']
                profit_target = row['PROFIT_TARGET']

    return pd.DataFrame(trades)

# --------------------------
# Análise de Resultados
# --------------------------
def analyze_results(trades_df: pd.DataFrame, initial_capital: float):
    if trades_df.empty:
        logger.warning("Nenhum trade foi executado. Não há resultados para analisar.")
        return

    total_trades = len(trades_df)
    win_trades = trades_df[trades_df['pnl_pct'] > 0]
    loss_trades = trades_df[trades_df['pnl_pct'] <= 0]
    
    win_rate = len(win_trades) / total_trades if total_trades > 0 else 0
    
    avg_win = win_trades['pnl_pct'].mean()
    avg_loss = loss_trades['pnl_pct'].mean()
    
    payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else np.inf
    
    expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)

    # Calcular PnL cumulativo
    trades_df['cumulative_pnl'] = (1 + trades_df['pnl_pct']).cumprod()
    final_capital = initial_capital * trades_df['cumulative_pnl'].iloc[-1]
    total_return_pct = (final_capital / initial_capital) - 1

    # Calcular Drawdown
    trades_df['capital'] = initial_capital * trades_df['cumulative_pnl']
    peak = trades_df['capital'].cummax()
    drawdown = (trades_df['capital'] - peak) / peak
    max_drawdown = drawdown.min()

    logger.info("--- Análise de Resultados do Backtest ---")
    logger.info(f"Período: {trades_df['entry_date'].min().date()} a {trades_df['exit_date'].max().date()}")
    logger.info(f"Retorno Total: {total_return_pct:.2%}")
    logger.info(f"Capital Final: ${final_capital:,.2f}")
    logger.info(f"Drawdown Máximo: {max_drawdown:.2%}")
    logger.info("-" * 20)
    logger.info(f"Total de Trades: {total_trades}")
    logger.info(f"Taxa de Acerto (Win Rate): {win_rate:.2%}")
    logger.info(f"Payoff Ratio (Média Ganho/Média Perda): {payoff_ratio:.2f}")
    logger.info(f"Expectativa Matemática por Trade: {expectancy:.4%}")
    logger.info("-" * 20)
    
# --------------------------
# Entrypoint
# --------------------------
def main():
    """Ponto de entrada principal do script de backtest."""
    logger.info(f"Iniciando backtest para o ativo '{TICKER}'...")
    
    # 1. Carregar Dados
    # Usando uma data de fim para garantir que o backtest não pegue dados muito recentes
    # e tenha um período de teste definido.
    try:
        raw_data = load_price_data(TICKER, end_date='2024-12-31')
        if raw_data is None or raw_data.empty:
            logger.error(f"Não foram encontrados dados para o ticker {TICKER}.")
            return
        logger.info(f"Dados carregados: {len(raw_data)} candles de {raw_data.index.min().date()} a {raw_data.index.max().date()}")
    except Exception as e:
        logger.error(f"Falha ao carregar dados: {e}")
        return

    # 2. Processar Dados para adicionar indicadores
    # Esta etapa enriquece o dataframe com indicadores que a estratégia pode usar.
    enriched_df = process_data(raw_data)
    logger.info("Dados processados e indicadores adicionados.")

    # 3. Carregar e aplicar a Estratégia
    logger.info(f"Carregando estratégia: '{STRATEGY_CLASS_NAME}'")
    strategy = load_strategy(STRATEGY_MODULE_PATH, STRATEGY_CLASS_NAME)
    
    logger.info("Executando a lógica da estratégia para gerar sinais...")
    # O método `calculate_signals` agora tem a correção de regime e usa indicadores pré-calculados
    df_with_signals = strategy.calculate_signals(enriched_df)
    
    buy_signals = len(df_with_signals[df_with_signals['SIGNAL'] == 'BUY'])
    sell_signals = len(df_with_signals[df_with_signals['SIGNAL'] == 'SELL'])
    logger.info(f"Sinais gerados: {buy_signals} de Compra, {sell_signals} de Venda.")

    if buy_signals == 0 and sell_signals == 0:
        logger.warning("A estratégia não gerou nenhum sinal de Compra ou Venda. Verifique a lógica e os dados.")
        return

    # 4. Executar o Backtest
    logger.info("Iniciando simulação de trades...")
    trades_df = run_simple_backtest(df_with_signals, INITIAL_CAPITAL, COMMISSION_PER_TRADE_PCT)
    
    # 5. Analisar e mostrar os resultados
    if not trades_df.empty:
        analyze_results(trades_df, INITIAL_CAPITAL)
    else:
        logger.warning("A simulação não resultou em nenhum trade executado.")

    logger.info("Backtest finalizado.")

if __name__ == '__main__':
    main()