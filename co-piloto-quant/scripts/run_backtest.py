import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
import os
import logging
from tqdm import tqdm
import concurrent.futures
from datetime import datetime

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_expanded_universe
from co_piloto_quant.risk_regime import calculate_vol_of_vol # Instrução 1: Importar
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy

# --- CONFIGURAÇÕES DO BACKTEST ---
INITIAL_CAPITAL = 100000
STOP_LOSS_PCT = 0.06 # Ativado para stop de emergência fixo
FEES_PCT = 0.0006
SLIPPAGE_PCT = 0.001

# --- CONFIGURAÇÕES DA ESTRATÉGIA ---
BB_EXIT_STD_DEV = 2.0
ENTROPY_CHAOS_THRESHOLD = 4.5
LIMIT_VOL_VOL = 0.050 # AJUSTE FINO: Apertado de 0.040 para 0.030
LIMIT_RAW_VOL = 0.060 # NOVO: Filtro de Volatilidade Pura (Anti-Turbulência)

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ignorar avisos de cálculo do vectorbt
warnings.filterwarnings('ignore')

def run_vectorized_backtest(ticker: str):
    """
    Executa um backtest totalmente vetorizado para um único ativo.
    """
    df_raw = load_price_data(ticker)
    if df_raw is None or df_raw.empty or len(df_raw) < 200:
        return None

    df = calculate_indicators(df_raw)
    
    if df is None or df.empty:
        return None

    # --- DUPLA CAMADA DE SEGURANÇA VETORIZADA ---
    returns = df['close'].pct_change()
    
    # 1. Filtro de VolVol (Anti-Crash)
    df['VolVol'] = returns.rolling(20).std().diff().abs()
    vol_vol_cond = df['VolVol'] <= LIMIT_VOL_VOL
    
    # 2. Filtro de Vol Pura (Anti-Turbulência)
    df['RawVol'] = returns.rolling(20).std()
    raw_vol_cond = df['RawVol'] <= LIMIT_RAW_VOL

    # Máscara final: Ambas as condições devem ser verdadeiras
    risk_safe = vol_vol_cond & raw_vol_cond
    
    # --- Lógica de Trading (via Strategy Class) ---
    # A estratégia centralizada define os sinais de BUY e SELL, garantindo que o backtest
    # use o mesmo "cérebro" do robô de produção.
    strategy = AdaptiveSniperStrategy(
        bb_exit_std_dev=BB_EXIT_STD_DEV, 
        entropy_chaos_threshold=ENTROPY_CHAOS_THRESHOLD
    )
    df = strategy.evaluate(df)

    # Converte os sinais da estratégia em máscaras booleanas para o vectorbt
    entries = (df['SIGNAL'] == 'BUY')
    exits = (df['SIGNAL'] == 'SELL')
    
    # Aplica o filtro de risco externo do backtest sobre os sinais de entrada da estratégia
    entries = entries & risk_safe

    # A AdaptiveSniperStrategy é long-only, então o short está desativado.
    short_entries = pd.Series(False, index=df.index)
    short_exits = pd.Series(False, index=df.index)

    # Evitar look-ahead bias
    entries = entries.shift(1).fillna(False)
    exits = exits.shift(1).fillna(False)
    short_entries = short_entries.shift(1).fillna(False)
    short_exits = short_exits.shift(1).fillna(False)
    
    if not entries.any() and not short_entries.any():
        return None

    high_price = df.get('high', df['close'])
    low_price = df.get('low', df['close'])

    portfolio = vbt.Portfolio.from_signals(
        close=df['close'], high=high_price, low=low_price,
        entries=entries, exits=exits,
        short_entries=short_entries, short_exits=short_exits,
        sl_stop=STOP_LOSS_PCT, init_cash=INITIAL_CAPITAL,
        fees=FEES_PCT, slippage=SLIPPAGE_PCT, freq='1D' 
    )

    return portfolio

def process_single_ticker_backtest(ticker: str):
    """
    Função wrapper para executar o backtest de um único ativo.
    Captura exceções, calcula estatísticas e retorna um dicionário leve.
    """
    try:
        pf = run_vectorized_backtest(ticker)
        if pf and pf.trades.count() > 0:
            stats = pf.stats()
            
            start_date = pd.to_datetime(stats['Start'])
            end_date = pd.to_datetime(stats['End'])
            anos_de_historico = (end_date - start_date).days / 365.25
            
            trades_por_ano = stats['Total Trades'] / anos_de_historico if anos_de_historico > 0 else 0

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
            return resultado
    except Exception as e:
        logger.error(f"Falha no backtest de {ticker}: {e}", exc_info=False)
    
    return None

if __name__ == "__main__":
    tickers = get_expanded_universe() 
    todos_resultados = []

    logger.info(f"--- INICIANDO BATCH DE BACKTESTS PARALELO PARA {len(tickers)} ATIVOS ---")
    
    # Usando ProcessPoolExecutor para paralelizar a carga de trabalho
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        # Mapeia futuros para tickers para melhor logging se necessário
        future_to_ticker = {executor.submit(process_single_ticker_backtest, ticker): ticker for ticker in tickers}
        
        # Processa os resultados à medida que são concluídos com uma barra de progresso
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Executando Backtests"):
            resultado = future.result()
            if resultado:
                todos_resultados.append(resultado)

    logger.info(f"Processamento paralelo concluído. {len(todos_resultados)} ativos tiveram resultados.")

    if todos_resultados:
        df_report = pd.DataFrame(todos_resultados)
        
        # --- GERAÇÃO DOS RANKINGS ---
        print("\n\n" + "="*80)
        print("          🏆 TOP 10 ATIVOS POR LUCRATIVIDADE (RETORNO TOTAL)")
        print("="*80)
        df_top_lucro = df_report.sort_values(by='Retorno Total (%)', ascending=False).head(10)
        print(df_top_lucro.to_string(index=False))
        
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
            
            df_report_sorted = df_report.sort_values(by='Sharpe Ratio', ascending=False)
            df_report_sorted.to_csv(report_path, index=False, float_format='%.2f')
            
            logger.info(f"Relatório consolidado com {len(df_report)} ativos salvo em: {report_path}")
        except Exception as e:
            logger.error(f"Falha ao salvar o relatório CSV: {e}")

    else:
        logger.warning("Nenhum backtest produziu resultados para gerar um relatório.")
