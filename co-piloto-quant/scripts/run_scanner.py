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
from co_piloto_quant.utils import get_top_50_tickers
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
        rules_check = check_rules(latest_data)

        # Retorna os dados necessários para o processo principal
        return ticker, latest_data, rules_check

    except Exception as e:
        # É importante capturar exceções aqui para não travar o pool de processos
        logger.error(f"Erro ao processar {ticker} em um processo filho: {e}", exc_info=False)
        return None

def run_scanner():
    """
    Executa o scanner de mercado de forma paralela, gera relatórios e salva os dados.
    """
    tickers = get_top_50_tickers()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers.")

    # 1. Download e Salvamento (Garante dados frescos)
    # Esta parte permanece sequencial, pois é predominantemente I/O-bound.
    period = "max"
    interval = "1d"
    logger.info(f"Atualizando base de dados com período '{period}'...")
    
    try:
        fetch_batch_data(tickers, period=period, interval=interval)
    except Exception as e:
        logger.error(f"Não foi possível baixar os dados em lote. Erro: {e}")
        return

    debug_results = []
    results = []

    logger.info("Iniciando análise paralela dos ativos...")

    # 2. Análise Ativo por Ativo em Paralelo
    # Usamos ProcessPoolExecutor para rodar a função CPU-bound em múltiplos processos
    # O número de workers é gerenciado pelo `os.cpu_count()`
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        # `executor.map` aplica a função a cada item da lista de tickers
        # `tqdm` envolve o resultado para mostrar a barra de progresso
        future_to_ticker = {executor.submit(process_single_ticker, ticker): ticker for ticker in tickers}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Processando Ativos"):
            result = future.result()
            if result:
                results.append(result)

    logger.info("Análise paralela concluída. Coletando e salvando resultados...")

    # 3. Processamento Sequencial dos Resultados
    # Esta parte é rápida e centraliza a escrita no DB e a agregação de relatórios.
    for result_item in results:
        if result_item is None:
            continue
        
        ticker, latest_data, rules_check = result_item

        # --- INÍCIO: Gravação de Sinais no Banco de Dados (Centralizado) ---
        if rules_check.get('Sinal_Compra'):
            record_signal(ticker, 'COMPRA_TECNICA', latest_data.get('close'), rules_check)
        
        if rules_check.get('Sinal_Venda'):
            record_signal(ticker, 'VENDA_TECNICA', latest_data.get('close'), rules_check)

        if rules_check.get('Sinal_Pullback_Sniper'):
            record_signal(ticker, 'COMPRA_SNIPER', latest_data.get('close'), rules_check)
        # --- FIM: Gravação de Sinais ---

        # --- Coleta Dados para o Relatório ---
        debug_info = {'Ticker': ticker, **rules_check}
        debug_info['Preço'] = latest_data.get('close')
        debug_info['IFR'] = latest_data.get('IFR_120')
        debug_info['Stoch'] = latest_data.get('stoch_k_80_3')
        debug_info['Hurst'] = latest_data.get('Hurst_72_returns', 0.5)
        debug_info['Half_Life'] = rules_check.get('Half_Life_Val', 1000)
        debug_info['OU_R2'] = rules_check.get('OU_R2', 0.0)

        debug_results.append(debug_info)

    # --- RELATÓRIOS (sem alterações) ---
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')
    pd.set_option('display.max_rows', None) 
    pd.set_option('display.expand_frame_repr', False) 

    print("\n" + "="*80)
    print(f"      RAIO-X DETALHADO DO MERCADO ({len(debug_results)} ativos processados)")
    print("="*80)

    if not debug_results:
        print("Nenhum dado processado.")
        return

    df = pd.DataFrame(debug_results)

    # Função auxiliar para imprimir grupos
    def print_group(title, condition_col, show_cols=['Ticker', 'Preço', 'Hurst', 'Stoch']):
        if condition_col not in df.columns:
            print(f"\n>> {title} [AVISO: Coluna '{condition_col}' não encontrada]")
            return

        subset = df[df[condition_col] == True]
        print(f"\n>> {title} (Total: {len(subset)})")
        if not subset.empty:
            sort_col = 'Hurst' if 'Hurst' in show_cols and 'Hurst' in subset.columns else 'Ticker'
            valid_cols = [c for c in show_cols if c in subset.columns]
            print(subset[valid_cols].sort_values(by=sort_col, ascending=False).to_string(index=False))
        else:
            print("   - Nenhum ativo encontrado.")

    print("\n--- 1. SINAIS CONFIRMADOS (TENDÊNCIA + TÉCNICA) ---")
    print_group("COMPRA FORTE (Confirmada)", 'Potencial_Alta', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Regime_Tendencia'])
    print_group("VENDA FORTE (Confirmada)", 'Potencial_Baixa', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Regime_Tendencia'])
    
    print("\n--- 2. REGIMES DE MERCADO (Hurst Detrended) ---")
    print_group("ALTA TENDÊNCIA (Hurst > 0.6)", 'Regime_Tendencia', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo'])
    print_group("MERCADO LATERAL/MEAN REVERSION (Hurst < 0.4)", 'Regime_Lateral', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'IFR'])

    print("\n--- 3. ESTRUTURA E VOLATILIDADE ---")
    print_group("EM CONSOLIDAÇÃO (BB)", 'Filtro_Consolidacao', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo'])
    print_group("POTENCIAL SQUEEZE (Explosão)", 'Potencial_Squeeze', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Preco_Em_Compressao'])

    print("\n--- 4. CANDIDATOS TÉCNICOS (SEM VALIDAÇÃO DE REGIME) ---")
    print_group("SETUP ALTA (Técnico Puro)", 'Potencial_Alta_Tecnico', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Half_Life', 'OU_R2'])
    print_group("SETUP BAIXA (Técnico Puro)", 'Potencial_Baixa_Tecnico', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Half_Life', 'OU_R2'])

    print("\n--- 5. SINAIS ESPECIAIS (Estratégias Alternativas) ---")
    print_group("OPORTUNIDADE OURO (Pullback Sniper)", 'Sinal_Pullback_Sniper', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Half_Life', 'OU_R2'])
    print_group("VIRADA DE CICLO (Hilbert Sniper)", 'Sinal_Entrada_Ciclo', show_cols=['Ticker', 'Preço', 'Hurst', 'Hilbert_Ciclo', 'Hilbert_Periodo', 'Hilbert_Sine'])

    print("\n--- 6. FILTRO DE QUALIDADE (ENTROPIA) ---")
    print_group("MERCADO CAÓTICO/RUIDOSO (Sinais Bloqueados)", 'Regime_Caotico', show_cols=['Ticker', 'Preço', 'Hurst', 'Entropy_Score'])

    print("\n" + "="*80)
    print("Processamento concluído.")
    print("="*80)

if __name__ == "__main__":
    # Garante que o banco de dados seja inicializado antes de qualquer operação
    init_recorder_db()
    run_scanner()
