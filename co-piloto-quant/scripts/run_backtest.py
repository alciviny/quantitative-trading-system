import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_scanner_tickers

# --- CONFIGURAÇÕES DO BACKTEST ---
INITIAL_CAPITAL = 100000
STOP_LOSS_PCT = 0.06 # Ativado para stop de emergência fixo
FEES_PCT = 0.0006
SLIPPAGE_PCT = 0.001

# --- CONFIGURAÇÕES DA ESTRATÉGIA ---
BB_EXIT_STD_DEV = 2.0
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
    # TRIO DE FILTROS DE REGIME: Só operar em mercados com tendência, organização e sustentação.
    filtro_tendencia = df.get('Hurst_72_returns', pd.Series(0.0, index=df.index)) >= 0.53
    filtro_caos = df.get('Entropy_20', pd.Series(999.0, index=df.index)) <= 3.2
    filtro_sustentacao = df.get('HalfLife_60', pd.Series(0.0, index=df.index)) >= 15
    regime_filter = filtro_tendencia & filtro_caos & filtro_sustentacao
    
    # tendencia_alta = df['close'] > df['WWMA_200'] # REMOVIDO para permitir pullbacks

    # NOVA "ZONA DE VALOR": Preço entre BB Inferior (0.45) e BB Superior (0.45)
    preco_na_zona_valor = (df['close'] >= df[f'BB_Lower_{200}_0.45']) & \
                          (df['close'] <= df[f'BB_Upper_{200}_0.45'])
    
    # FILTRO DE INCLINAÇÃO DA WWMA PARA SEGURANÇA
    inclincao_wwma_positiva = df['WWMA_200'].diff(5) > 0

    fluxo_alta = (df['obtr'] > df['obtr_bb_middle_band']) | (df['wad'] > df['wad_bb_middle_band'])
    # potencial_alta_tecnico = tendencia_alta & preco_na_metade_superior & fluxo_alta # ANTES
    potencial_alta_tecnico = preco_na_zona_valor & inclincao_wwma_positiva & fluxo_alta # AGORA
    
    # --- CRITÉRIO DE ENTRADA (ESTOCÁSTICO) ---
    stoch_k_col = 'stoch_k_80_3' 
    condicao_stoch_compra = df[stoch_k_col] < 30
    entries = potencial_alta_tecnico & regime_filter & condicao_stoch_compra

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
    short_entries = potencial_baixa_tecnico & regime_filter & condicao_stoch_venda

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
        sl_stop=STOP_LOSS_PCT,
        init_cash=INITIAL_CAPITAL,
        fees=FEES_PCT,
        slippage=SLIPPAGE_PCT,
        freq='1D' 
    )

    return portfolio

if __name__ == "__main__":
    import os
    from datetime import datetime

    tickers = get_scanner_tickers() 
    todos_resultados = []

    print(f"--- INICIANDO BATCH DE BACKTESTS PARA {len(tickers)} ATIVOS ---")

    for ticker in tickers:
        pf = run_vectorized_backtest(ticker)
        if pf:
            stats = pf.stats()
            if stats['Total Trades'] > 0:
            
            # Cálculo de anos para a métrica de frequência
                start_date = pd.to_datetime(stats['Start'])
                end_date = pd.to_datetime(stats['End'])
                anos_de_historico = (end_date - start_date).days / 365.25
            
            if anos_de_historico > 0:
                trades_por_ano = stats['Total Trades'] / anos_de_historico
            else:
                trades_por_ano = 0

            # Coleta dos dados para o relatório
            resultado = {
                'Ticker': ticker,
                'Retorno Total (%)': stats['Total Return [%]'],
                'Lucro Líquido (Cash)': stats['End Value'] - stats['Start Value'],
                'Total de Trades': stats['Total Trades'],
                'Win Rate (%)': stats['Win Rate [%]'],
                'Sharpe Ratio': stats['Sharpe Ratio'],
                'Max Drawdown (%)': stats['Max Drawdown [%]'],
                'Trades por Ano': trades_por_ano
            }
            todos_resultados.append(resultado)
            
            print(f"--- ✅ Backtest de {ticker} concluído com {stats['Total Trades']} trades. ---")
        else:
            print(f"--- ⚠️ Sem trades ou dados para {ticker}. ---")

    if todos_resultados:
        # Criação do DataFrame consolidado
        df_report = pd.DataFrame(todos_resultados)
        
        # --- GERAÇÃO DOS RANKINGS ---
        
        # 1. TOP 10 por Lucratividade (Retorno Total)
        print("\n\n" + "="*80)
        print("          🏆 TOP 10 ATIVOS POR LUCRATIVIDADE (RETORNO TOTAL)")
        print("="*80)
        df_top_lucro = df_report.sort_values(by='Retorno Total (%)', ascending=False).head(10)
        print(df_top_lucro.to_string(index=False))
        
        # 2. TOP 10 por Frequência (Apenas ativos com lucro)
        print("\n\n" + "="*80)
        print("          ⚡ TOP 10 ATIVOS POR FREQUÊNCIA (COM LUCRO > 0)")
        print("="*80)
        df_lucrativos = df_report[df_report['Lucro Líquido (Cash)'] > 0]
        if not df_lucrativos.empty:
            df_top_freq = df_lucrativos.sort_values(by='Trades por Ano', ascending=False).head(10)
            print(df_top_freq.to_string(index=False))
        else:
            print("Nenhum ativo lucrativo encontrado para o ranking de frequência.")
        print("="*80)

        # --- EXPORTAÇÃO DO RELATÓRIO COMPLETO ---
        try:
            report_dir = 'data/reports'
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, 'ranking_backtest.csv')
            
            # Ordena o relatório final pelo Sharpe Ratio antes de salvar
            df_report_sorted = df_report.sort_values(by='Sharpe Ratio', ascending=False)
            df_report_sorted.to_csv(report_path, index=False, float_format='%.2f')
            
            print(f"\n\n[ SUCESSO ] Relatório consolidado com {len(df_report)} ativos salvo em: {report_path}")
        except Exception as e:
            print(f"\n\n[ ERRO ] Falha ao salvar o relatório CSV: {e}")

    else:
        print("\nNenhum backtest produziu resultados para gerar um relatório.")