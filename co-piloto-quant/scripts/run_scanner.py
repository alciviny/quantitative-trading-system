# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm
import concurrent.futures
import os

from co_piloto_quant.data.recorder import init_recorder_db, record_signal
from co_piloto_quant.config import PROCESSED_DATA_PATH
from co_piloto_quant.data.data_fetching import fetch_batch_data
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.utils import get_expanded_universe
from co_piloto_quant.data.data_processing import process_data
from co_piloto_quant.analysis import calculate_indicators, check_rules

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_single_ticker(ticker):
    """
    Função que encapsula todo o processamento para um único ativo.
    É projetada para ser executada em um processo separado.
    """
    try:
        # Cada processo carrega os dados de que precisa.
        raw_df = load_price_data(ticker)
        if raw_df.empty:
            return None

        # Calcula indicadores
        processed_df = process_data(raw_df, ticker)
        
        # --- CÁLCULO DE INDICADORES (CPU-BOUND) ---
        df_with_indicators = calculate_indicators(processed_df)

        if df_with_indicators.empty or df_with_indicators.iloc[-1].isnull().all():
            return None

        # Salva o resultado processado para o Dashboard
        file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
        df_with_indicators.to_csv(file_path)

        latest_data = df_with_indicators.iloc[-1]

        # Aplica as Regras
       # LINHA 49 (Nova - Passando o DataFrame completo)
        rules_check = check_rules(df_with_indicators)

        # Retorna os dados necessários para o processo principal
        return ticker, latest_data, rules_check

    except Exception as e:
        # É importante capturar exceções aqui para não travar o pool de processos
        logger.error(f"Erro ao processar {ticker} em um processo filho: {e}", exc_info=False)
        return None

def run_scanner():
    """
    Executa o scanner de mercado, agora com uma lógica de relatório híbrida:
    usa a 'check_rules' para os sinais finais e recalcula os status secundários
    para um relatório de mercado detalhado.
    """
    tickers = get_expanded_universe()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers.")

    # 1. Atualização da Base de Dados
    period = "max"
    interval = "1d"
    logger.info(f"Atualizando base de dados com período '{period}'...")
    try:
        fetch_batch_data(tickers, period=period, interval=interval)
    except Exception as e:
        logger.error(f"Não foi possível baixar os dados em lote. Erro: {e}")
        return

    all_results = []
    logger.info("Iniciando análise paralela dos ativos...")

    # 2. Análise em Paralelo
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_ticker = {executor.submit(process_single_ticker, ticker): ticker for ticker in tickers}
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Processando Ativos"):
            result = future.result()
            if result:
                all_results.append(result)

    logger.info("Análise concluída. Gerando relatório detalhado...")

    # 3. Processamento e Agregação para Relatório Detalhado
    report_data = []
    for result_item in all_results:
        if result_item is None:
            continue
        
        ticker, latest_data, rules_check = result_item

        # --- Gravação dos Sinais Finais no Banco ---
        if rules_check.get('Sinal_Compra'):
            record_signal(ticker, 'COMPRA_FINAL', latest_data.get('close'), rules_check)
        if rules_check.get('Sinal_Venda'):
            record_signal(ticker, 'VENDA_FINAL', latest_data.get('close'), rules_check)

        # --- RECONSTRUÇÃO DOS STATUS PARA O RELATÓRIO DETALHADO ---
        # Recalcula as condições de regime e potencial que antes vinham da check_rules
        hurst_val = latest_data.get('Hurst_72_returns', 0.5)
        entropy_val = latest_data.get('Entropy_20', 10.0)
        
        status_info = {
            'Ticker': ticker,
            'Preço': latest_data.get('close'),
            'Hurst': hurst_val,
            'Estocástico': latest_data.get(f'stoch_k_{80}_{3}'),
            'Half_Life': latest_data.get('HalfLife_60'),
            'OU_R2': latest_data.get('R2_60'),
            'Entropy_Score': entropy_val,
            'Hilbert_Ciclo': latest_data.get('Hilbert_Status', 'N/A'),
            'Hilbert_Periodo': latest_data.get('Hilbert_Period'),
            
            # Sinais Finais da nova 'check_rules'
            'Sinal_Compra_Final': rules_check.get('Sinal_Compra', False),
            'Sinal_Venda_Final': rules_check.get('Sinal_Venda', False),

            # Status de Regime
            'Regime_Tendencia': hurst_val > 0.54,
            'Regime_Lateral': hurst_val < 0.46,
            'Regime_Caotico': entropy_val >= 3.2,

            # Status de Squeeze (usando BB de 0.45)
            'Potencial_Squeeze': (
                latest_data.get('close') <= latest_data.get('BB_Upper_200_0.45', float('inf')) and
                latest_data.get('close') >= latest_data.get('BB_Lower_200_0.45', float('-inf'))
            )
        }
        report_data.append(status_info)

    # --- ANTIGO RELATÓRIO DETALHADO (RESTAURADO E ADAPTADO) ---
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')
    pd.set_option('display.max_rows', None) 
    pd.set_option('display.expand_frame_repr', False) 

    print("\n" + "="*80)
    print(f"      RAIO-X DETALHADO DO MERCADO ({pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')})")
    print("="*80)

    if not report_data:
        print("Nenhum dado processado.")
        return

    df = pd.DataFrame(report_data)

    def print_group(title, condition_col, show_cols, sort_col='Hurst', ascending=False):
        if condition_col not in df.columns:
            print(f"\n>> {title} [AVISO: Coluna '{condition_col}' não encontrada]")
            return

        subset = df[df[condition_col] == True]
        print(f"\n>> {title} (Total: {len(subset)})")
        if not subset.empty:
            # Garante que a coluna de ordenação exista antes de usá-la
            sort_col = sort_col if sort_col in subset.columns else 'Ticker'
            valid_cols = [c for c in show_cols if c in subset.columns]
            print(subset[valid_cols].sort_values(by=sort_col, ascending=ascending).to_string(index=False))
        else:
            print("   - Nenhum ativo encontrado.")

    # --- 1. SINAIS PRINCIPAIS (DA NOVA ESTRATÉGIA) ---
    print("\n--- 1. SINAIS DE ENTRADA CONFIRMADOS (ESTRATÉGIA PRINCIPAL) ---")
    print_group("COMPRA (Sinal Final)", 'Sinal_Compra_Final', show_cols=['Ticker', 'Preço', 'Estocástico', 'Stop Sugerido Compra'], sort_col='Ticker')
    print_group("VENDA (Sinal Final)", 'Sinal_Venda_Final', show_cols=['Ticker', 'Preço', 'Estocástico', 'Stop Sugerido Venda'], sort_col='Ticker')

    # --- 2. ANÁLISE DE REGIMES E DIAGNÓSTICOS ---
    print("\n--- 2. REGIMES DE MERCADO E DIAGNÓSTICOS ---")
    print_group("ALTA TENDÊNCIA (Hurst > 0.54)", 'Regime_Tendencia', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo'])
    print_group("MERCADO LATERAL (Hurst < 0.46)", 'Regime_Lateral', show_cols=['Ticker', 'Preço', 'Hurst', 'Half_Life', 'OU_R2'], sort_col='Half_Life', ascending=True)
    print_group("POTENCIAL SQUEEZE (Dentro da BB 0.45)", 'Potencial_Squeeze', show_cols=['Ticker', 'Preço', 'Hurst', 'Estocástico'])
    print_group("MERCADO CAÓTICO (Entropia >= 3.2)", 'Regime_Caotico', show_cols=['Ticker', 'Preço', 'Hurst', 'Entropy_Score'])
    
    print("\n" + "="*80)
    print("Processamento concluído.")
    print("="*80)

if __name__ == "__main__":
    # Garante que o banco de dados seja inicializado antes de qualquer operação
    init_recorder_db()
    run_scanner()
