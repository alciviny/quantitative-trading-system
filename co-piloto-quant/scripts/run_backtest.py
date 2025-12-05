import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_scanner_tickers

# --- CONFIGURAÇÕES DO BACKTEST ---
INITIAL_CAPITAL = 100000
# STOP_LOSS_PCT = 0.10 # Comentado pois o stop agora é dinâmico
FEES_PCT = 0.0006
SLIPPAGE_PCT = 0.001

# --- CONFIGURAÇÕES DA ESTRATÉGIA ---
BB_EXIT_STD_DEV = 1.5
ENTROPY_CHAOS_THRESHOLD = 3.2  # Limite para o filtro de entropia

# Ignorar avisos de cálculo do vectorbt
warnings.filterwarnings('ignore')

def run_vectorized_backtest(ticker: str):
    """
    Executa um backtest totalmente vetorizado para um único ativo com saída dinâmica.
    """
    print(f"\n--- Iniciando Backtest Vetorizado para {ticker} ---")
    
    df_raw = load_price_data(ticker)
    if df_raw.empty or len(df_raw) < 200:
        print(f"Dados insuficientes para {ticker}.")
        return None

    print(f"[{ticker}] Calculando indicadores complexos...")
    df = calculate_indicators(df_raw)
    
    if df.empty:
        print(f"[{ticker}] Falha ao calcular indicadores.")
        return None

    print(f"[{ticker}] Gerando sinais de forma vetorizada...")

    # --- Lógica de ENTRADA ---
    is_orderly = df['Entropy_20'] < ENTROPY_CHAOS_THRESHOLD
    tendencia_alta = df['close'] > df['WWMA_200']
    
    # CRITÉRIO DE ENTRADA NA BANDA DE BOLLINGER (AJUSTADO)
    # O preço deve estar na metade SUPERIOR da banda com desvio de 0.45
    preco_na_metade_superior = (df['close'] <= df[f'BB_Upper_{200}_0.45']) & (df['close'] >= df[f'BB_Middle_{200}'])
    
    fluxo_alta = (df['obtr'] > df['obtr_bb_middle_band']) | (df['wad'] > df['wad_bb_middle_band'])
    potencial_alta_tecnico = tendencia_alta & preco_na_metade_superior & fluxo_alta
    
    # --- CRITÉRIO DE ENTRADA (ESTOCÁSTICO) ---
    stoch_k_col = 'stoch_k_80_3' 
    condicao_stoch_compra = df[stoch_k_col] < 30
    entries = potencial_alta_tecnico & is_orderly & condicao_stoch_compra

    # --- Lógica de SAÍDA (COMPRA) ---
    bb_exit_col = f'BB_Upper_{200}_{BB_EXIT_STD_DEV}'
    take_profit_long = df['close'] >= df[bb_exit_col]
    stop_loss_long = df['close'] < df[f'BB_Lower_{200}_0.45']
    exits = take_profit_long | stop_loss_long

    # --- Lógica de ENTRADA (VENDA) ---
    # A lógica de regime (ordem) é a mesma para compra e venda
    tendencia_baixa = df['close'] < df['WWMA_200']
    
    # CRITÉRIO DE ENTRADA NA BANDA DE BOLLINGER (VENDA)
    # O preço deve estar na metade INFERIOR da banda com desvio de 0.45
    preco_na_metade_inferior = (df['close'] >= df[f'BB_Lower_{200}_0.45']) & (df['close'] <= df[f'BB_Middle_{200}'])
    
    fluxo_baixa = (df['obtr'] < df['obtr_bb_middle_band']) | (df['wad'] < df['wad_bb_middle_band'])
    potencial_baixa_tecnico = tendencia_baixa & preco_na_metade_inferior & fluxo_baixa
    
    # --- CRITÉRIO DE ENTRADA (ESTOCÁSTICO) ---
    condicao_stoch_venda = df[stoch_k_col] > 70
    short_entries = potencial_baixa_tecnico & is_orderly & condicao_stoch_venda

    # --- Lógica de SAÍDA (VENDA) ---
    bb_short_exit_col = f'BB_Lower_{200}_{BB_EXIT_STD_DEV}'
    take_profit_short = df['close'] <= df[bb_short_exit_col]
    stop_loss_short = df['close'] > df[f'BB_Upper_{200}_0.45']
    short_exits = take_profit_short | stop_loss_short


    entries = entries.fillna(False)
    exits = exits.fillna(False)
    short_entries = short_entries.fillna(False)
    short_exits = short_exits.fillna(False)
    
    # Verifica se existe algum sinal de entrada (compra ou venda)
    if entries.sum() == 0 and short_entries.sum() == 0:
        return None

    print(f"[{ticker}] Executando simulação do portfólio...")
    portfolio = vbt.Portfolio.from_signals(
        close=df['close'],
        entries=entries,
        exits=exits,
        short_entries=short_entries,
        short_exits=short_exits,
        # sl_stop foi removido para usar o stop dinâmico da banda de bollinger
        init_cash=INITIAL_CAPITAL,
        fees=FEES_PCT,
        slippage=SLIPPAGE_PCT,
        freq='1D' 
    )

    return portfolio

if __name__ == "__main__":
    tickers = get_scanner_tickers() # Pega os tickers do banco de dados do scanner
    all_stats = []
    last_pf = None # Armazena o último portfólio para plotagem

    for ticker in tickers:
        pf = run_vectorized_backtest(ticker)
        if pf:
            stats = pf.stats()
            if stats['Total Trades'] > 0:
                stats['Ticker'] = ticker
                all_stats.append(stats)
                last_pf = pf # Salva o portfólio se teve trades
                
                print("\n" + "="*50)
                print(f"RESULTADO DO BACKTEST: {ticker}")
                print("="*50)
                # --- CORREÇÃO APLICADA AQUI ---
                print(f"Período: {stats['Start']} a {stats['End']}")
                print(f"Retorno Total:     {stats['Total Return [%]']:.2f}%")
                print(f"Win Rate:          {stats['Win Rate [%]']:.2f}%")
                print(f"Trades Totais:     {stats['Total Trades']}")
                print(f"Sharpe Ratio:      {stats['Sharpe Ratio']:.2f} (CALMAR {stats['Calmar Ratio']:.2f})")
                print(f"Max Drawdown:      {stats['Max Drawdown [%]']:.2f}%")
                print("-" * 50)
            else:
                 print(f"\n--- Sem trades para {ticker} ---")
        else:
            print(f"\n--- Falha ao gerar portfólio para {ticker} (sem sinais ou dados) ---")

    if all_stats:
        df_summary = pd.DataFrame(all_stats).set_index('Ticker')
        
        # Todas as chaves aqui já estavam corretas, conforme sua saída de debug
        cols_to_show = [
            'Total Return [%]', 'Win Rate [%]', 'Total Trades', 'Sharpe Ratio', 
            'Calmar Ratio', 'Max Drawdown [%]', 'Avg Winning Trade [%]', 'Avg Losing Trade [%]'
        ]
        
        print("\n\n" + "="*80)
        print("          RELATÓRIO CONSOLIDADO DE BACKTESTS")
        print("="*80)
        print(df_summary[cols_to_show].sort_values(by='Sharpe Ratio', ascending=False))
        print("="*80)

        if last_pf:
            print("\nGerando gráfico para o último ativo com trades...")
            # A linha abaixo foi comentada para não gerar o output do gráfico no terminal.
            # last_pf.plot().show()
    else:
        print("\nNenhum backtest produziu resultados para ser consolidado.")