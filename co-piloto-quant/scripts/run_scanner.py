# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm

# Importações dos módulos do projeto
from co_piloto_quant.utils import get_top_50_tickers
from co_piloto_quant.data.data_fetching import fetch_batch_data, fetch_data_from_csv, DataFetchError
from co_piloto_quant.data.data_processing import process_data
from co_piloto_quant.analysis import calculate_indicators, check_rules
from co_piloto_quant.config import RAW_DATA_PATH

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_scanner():
    """
    Executa o scanner de mercado em modo de depuração para entender por que
    nenhum ativo está sendo encontrado.
    """
    tickers = get_top_50_tickers()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers.")

    # Alterado para "max" para buscar o máximo de dados históricos disponíveis
    period = "max"
    interval = "1d"
    logger.info(f"Buscando dados históricos com período '{period}' para garantir o cálculo dos indicadores.")
    try:
        fetch_batch_data(tickers, period=period, interval=interval)
    except DataFetchError as e:
        logger.error(f"Não foi possível baixar os dados em lote. Abortando. Erro: {e}")
        return

    oportunidades_compra = []
    oportunidades_venda = []
    debug_results = []

    logger.info("Processando e analisando cada ativo...")
    for ticker in tqdm(tickers, desc="Analisando Ativos"):
        try:
            file_path = RAW_DATA_PATH / f"{ticker}_raw.csv"
            if not file_path.exists():
                logger.warning(f"Arquivo não encontrado para {ticker}, pulando.")
                continue

            raw_df = fetch_data_from_csv(str(file_path))
            processed_df = process_data(raw_df, ticker)
            df_with_indicators = calculate_indicators(processed_df)

            if df_with_indicators.empty:
                logger.warning(f"[{ticker}] Pulando ativo: DataFrame vazio após cálculo de indicadores.")
                continue

            latest_data = df_with_indicators.iloc[-1]
            
            if latest_data.isnull().any():
                null_cols = latest_data[latest_data.isnull()].index.tolist()
                logger.warning(f"[{ticker}] Pulando ativo: Valores nulos no último candle. Colunas: {null_cols}")
                continue

            # Bloco try/except para capturar o KeyError específico das Bandas de Bollinger
            try:
                rules_check = check_rules(latest_data)
            except KeyError as e:
                logger.error(f"[{ticker}] Erro de Chave (KeyError) ao verificar regras: {e}")
                logger.error(f"[{ticker}] Colunas disponíveis no DataFrame: {df_with_indicators.columns.tolist()}")
                continue # Pula para o próximo ticker

            
            debug_info = {'Ticker': ticker, **rules_check}
            debug_info['IFR_120'] = latest_data.get('IFR_120')
            debug_info['Stoch_K'] = latest_data.get('stoch_k_80_3')
            debug_results.append(debug_info)

            stoch_k_col = 'stoch_k_80_3'
            if rules_check.get('Sinal_Compra', False):
                oportunidades_compra.append({
                    'Ticker': ticker,
                    'Preço': latest_data['close'],
                    'Stoch_K': latest_data[stoch_k_col],
                    'IFR_120': latest_data['IFR_120']
                })

            if rules_check.get('Sinal_Venda', False):
                oportunidades_venda.append({
                    'Ticker': ticker,
                    'Preço': latest_data['close'],
                    'Stoch_K': latest_data[stoch_k_col],
                    'IFR_120': latest_data['IFR_120']
                })

        except DataFetchError as e:
            logger.error(f"Erro ao buscar/ler dados para {ticker}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado geral ao processar o ticker {ticker}: {e}", exc_info=False)

    pd.set_option('display.float_format', lambda x: f'{x:.2f}')

    # --- INÍCIO DA SEÇÃO DE DEPURAÇÃO ---
    print("\n" + "="*55)
    print("      ANÁLISE DE DEPURAÇÃO DO SCANNER")
    print("="*55)

    if not debug_results:
        print("\nNenhum ativo pôde ser processado para depuração, mesmo com o aumento do período de dados.")
        print("Verifique os logs de aviso (WARN) para ver por que os ativos individuais foram pulados.")
    else:
        debug_df = pd.DataFrame(debug_results)
        
        print("\n[1] Contagem de Ativos que Passaram em Cada Etapa:")
        rule_counts = debug_df.select_dtypes(include='bool').sum()
        print(rule_counts.to_string())

        print("\n\n[2] Ativos que passaram no 'Filtro_Consolidacao':")
        ativos_em_consolidacao = debug_df[debug_df['Filtro_Consolidacao'] == True]
        if ativos_em_consolidacao.empty:
            print("Nenhum ativo está em consolidação com os parâmetros atuais.")
        else:
            cols_to_show = [
                'Ticker', 'IFR_120', 'Stoch_K', 
                'Forca_Compradora', 'Gatilho_Compra', 
                'Forca_Vendedora', 'Gatilho_Venda'
            ]
            print(ativos_em_consolidacao[cols_to_show].to_string(index=False))
            
    # --- FIM DA SEÇÃO DE DEPURAÇÃO ---

    print("\n\n" + "="*55)
    print("      RESULTADO DO SCANNER - ENTRADA EM COMPRESSÃO")
    print("="*55)

    if not oportunidades_compra:
        print("\nNenhuma oportunidade de COMPRA encontrada.")
    else:
        compra_df = pd.DataFrame(oportunidades_compra)
        sorted_compra = compra_df.sort_values(by='Stoch_K', ascending=True)
        print("\n--- TOP 10 OPORTUNIDADES DE COMPRA (Alta Potencial) ---")
        print(sorted_compra.head(10).to_string(index=False))

    if not oportunidades_venda:
        print("\nNenhuma oportunidade de VENDA encontrada.")
    else:
        venda_df = pd.DataFrame(oportunidades_venda)
        sorted_venda = venda_df.sort_values(by='Stoch_K', ascending=False)
        print("\n\n--- TOP 10 OPORTUNIDADES DE VENDA (Baixa Potencial) ---")
        print(sorted_venda.head(10).to_string(index=False))

    print("\n" + "="*55)


if __name__ == "__main__":
    run_scanner()
