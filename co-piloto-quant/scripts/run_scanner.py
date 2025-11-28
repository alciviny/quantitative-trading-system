# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm

# Importações do projeto
from co_piloto_quant.config import PROCESSED_DATA_PATH  # <--- Importante para salvar
from co_piloto_quant.data.data_fetching import fetch_batch_data
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.utils import get_top_50_tickers
from co_piloto_quant.data.data_processing import process_data
from co_piloto_quant.analysis import calculate_indicators, check_rules

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scanner():
    """
    Executa o scanner de mercado, gera relatórios e SALVA os dados para o Dashboard.
    """
    tickers = get_top_50_tickers()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers.")

    # 1. Download e Salvamento (Garante dados frescos)
    period = "max"
    interval = "1d"
    logger.info(f"Atualizando base de dados com período '{period}'...")
    
    try:
        fetch_batch_data(tickers, period=period, interval=interval)
    except Exception as e:
        logger.error(f"Não foi possível baixar os dados em lote. Erro: {e}")
        return

    debug_results = []

    logger.info("Carregando do Banco de Dados, analisando e salvando para Dashboard...")
    
    # 2. Análise Ativo por Ativo
    for ticker in tqdm(tickers, desc="Processando Ativos"):
        try:
            raw_df = load_price_data(ticker)
            if raw_df.empty: continue

            # Calcula indicadores
            processed_df = process_data(raw_df, ticker)
            df_with_indicators = calculate_indicators(processed_df)

            if df_with_indicators.empty: continue

            # --- NOVO: SALVA O ARQUIVO PARA O DASHBOARD ---
            # Isso cria o arquivo que o Streamlit precisa para mostrar o gráfico
            file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
            df_with_indicators.to_csv(file_path)
            # ---------------------------------------------

            latest_data = df_with_indicators.iloc[-1]
            if latest_data.isnull().any(): continue

            try:
                rules_check = check_rules(latest_data)
            except KeyError as e:
                logger.error(f"[{ticker}] Erro de Chave: {e}")
                continue

            # --- Coleta Dados para o Relatório ---
            debug_info = {'Ticker': ticker, **rules_check}
            debug_info['Preço'] = latest_data.get('close')
            debug_info['IFR_120'] = latest_data.get('IFR_120')
            debug_info['Stoch_K'] = latest_data.get('stoch_k_80_3')
            debug_info['WAD'] = latest_data.get('wad')
            debug_info['OBTR'] = latest_data.get('obtr')
            
            debug_results.append(debug_info)

        except Exception as e:
            logger.error(f"Erro ao processar {ticker}: {e}", exc_info=False)

    # --- RELATÓRIOS ---
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

    def print_group(title, condition_col, show_cols=['Ticker', 'Preço', 'Stoch_K', 'IFR_120']):
        subset = df[df[condition_col] == True]
        print(f"\n>> {title} (Total: {len(subset)})")
        if not subset.empty:
            sort_by_col = 'Stoch_K' if 'Stoch_K' in show_cols else 'Ticker'
            print(subset[show_cols].sort_values(by=sort_by_col).to_string(index=False))
        else:
            print("   - Nenhum ativo encontrado.")

    print("\n--- 1. CONSOLIDAÇÃO & SQUEEZE ---")
    print_group("ATIVOS EM CONSOLIDAÇÃO", 'Filtro_Consolidacao')
    print_group("POTENCIAL SQUEEZE", 'Potencial_Squeeze', show_cols=['Ticker', 'Preço', 'WAD', 'OBTR'])

    print("\n--- 2. SETUPS DE IFR (Squeeze) ---")
    print_group("SQUEEZE IFR ALTA", 'Squeeze_IFR_Alta')
    print_group("SQUEEZE IFR BAIXA", 'Squeeze_IFR_Baixa')

    print("\n--- 3. SINAIS DIRECIONAIS ---")
    print_group("POTENCIAL ALTA", 'Potencial_Alta')
    print_group("POTENCIAL BAIXA", 'Potencial_Baixa')

    print("\n" + "="*80)
    print("Processamento concluído. Abra o Dashboard para visualizar os gráficos.")
    print("="*80)

if __name__ == "__main__":
    run_scanner()