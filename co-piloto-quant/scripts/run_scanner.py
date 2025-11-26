# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm

# Importações do projeto
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
    Executa o scanner de mercado e gera relatórios detalhados para cada setup.
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

    logger.info("Carregando do Banco de Dados e analisando...")
    
    # 2. Análise Ativo por Ativo
    for ticker in tqdm(tickers, desc="Analisando Ativos"):
        try:
            raw_df = load_price_data(ticker)
            if raw_df.empty: continue

            processed_df = process_data(raw_df, ticker)
            df_with_indicators = calculate_indicators(processed_df)

            if df_with_indicators.empty: continue

            latest_data = df_with_indicators.iloc[-1]
            if latest_data.isnull().any(): continue

            try:
                rules_check = check_rules(latest_data)
            except KeyError as e:
                logger.error(f"[{ticker}] Erro de Chave: {e}")
                continue

            # --- Coleta Dados para o Relatório ---
            # Junta as flags (True/False) com os valores numéricos
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
    pd.set_option('display.max_rows', None) # Mostrar todas as linhas
    pd.set_option('display.expand_frame_repr', False) # Não quebrar linhas

    print("\n" + "="*80)
    print(f"      RAIO-X DETALHADO DO MERCADO ({len(debug_results)} ativos analisados)")
    print("="*80)

    if not debug_results:
        print("Nenhum dado processado.")
        return

    df = pd.DataFrame(debug_results)

    # Função auxiliar para imprimir grupos
    def print_group(title, condition_col, show_cols=['Ticker', 'Preço', 'Stoch_K', 'IFR_120']):
        subset = df[df[condition_col] == True]
        print(f"\n>> {title} (Total: {len(subset)})")
        if not subset.empty:
            # Ordena pela coluna Stoch_K se ela estiver na lista de exibição, senão por Ticker.
            sort_by_col = 'Stoch_K' if 'Stoch_K' in show_cols else 'Ticker'
            print(subset[show_cols].sort_values(by=sort_by_col).to_string(index=False))
        else:
            print("   - Nenhum ativo encontrado.")

    # 1. Relatório de Consolidação e Squeeze (Preço)
    print("\n--- 1. CONSOLIDAÇÃO & SQUEEZE ---")
    print_group("ATIVOS EM CONSOLIDAÇÃO (Preço dentro da Banda 1.0)", 'Filtro_Consolidacao')
    print_group("POTENCIAL SQUEEZE (Preço e Indicador dentro da Banda 0.45)", 'Potencial_Squeeze', 
                show_cols=['Ticker', 'Preço', 'WAD', 'OBTR'])

    # 2. Relatório de Setups Específicos de IFR
    print("\n--- 2. SETUPS DE IFR (Squeeze) ---")
    print_group("SQUEEZE IFR ALTA (IFR Neutro + Stoch < 30)", 'Squeeze_IFR_Alta')
    print_group("SQUEEZE IFR BAIXA (IFR Neutro + Stoch > 70)", 'Squeeze_IFR_Baixa')

    # 3. Relatório de Sinais Principais (Potencial Alta/Baixa)
    print("\n--- 3. SINAIS DIRECIONAIS (Alta/Baixa) ---")
    print_group("POTENCIAL ALTA (Preço em 1.0 + Fluxo Positivo + Stoch < 50)", 'Potencial_Alta')
    print_group("POTENCIAL BAIXA (Preço em 1.0 + Fluxo Negativo + Stoch > 50)", 'Potencial_Baixa')

    print("\n" + "="*80)
    print("FIM DO RELATÓRIO")
    print("="*80)

if __name__ == "__main__":
    run_scanner()