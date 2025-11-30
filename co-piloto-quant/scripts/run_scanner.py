# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm

# Importações do projeto
from co_piloto_quant.config import PROCESSED_DATA_PATH
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
            
            # --- CÁLCULO DE INDICADORES (INCLUINDO HURST) ---
            # Isso agora vai chamar o seu novo calculate_indicators com Hurst
            df_with_indicators = calculate_indicators(processed_df)

            if df_with_indicators.empty: continue

            # Salva para o Dashboard
            file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
            df_with_indicators.to_csv(file_path)

            latest_data = df_with_indicators.iloc[-1]
            if latest_data.isnull().any(): 
                pass

            try:
                # Aplica as Regras (Agora com Filtro de Regime Hurst)
                rules_check = check_rules(latest_data)
            except KeyError as e:
                logger.error(f"[{ticker}] Erro de Chave na verificação de regras: {e}")
                continue

            # --- Coleta Dados para o Relatório ---
            debug_info = {'Ticker': ticker, **rules_check}
            
            # Adiciona valores numéricos importantes para visualização rápida
            debug_info['Preço'] = latest_data.get('close')
            debug_info['IFR'] = latest_data.get('IFR_120')
            debug_info['Stoch'] = latest_data.get('stoch_k_80_3')
            
            # Busca a chave correta do Hurst (via get para segurança)
            hurst_val = latest_data.get('Hurst_72_returns', 0.5)
            debug_info['Hurst'] = hurst_val
            
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

    # Função auxiliar para imprimir grupos
    def print_group(title, condition_col, show_cols=['Ticker', 'Preço', 'Hurst', 'Stoch']):
        # Verifica se a coluna existe antes de filtrar
        if condition_col not in df.columns:
            print(f"\n>> {title} [AVISO: Coluna '{condition_col}' não encontrada]")
            return

        subset = df[df[condition_col] == True]
        print(f"\n>> {title} (Total: {len(subset)})")
        if not subset.empty:
            # Ordena por Hurst se disponível para priorizar tendência
            sort_col = 'Hurst' if 'Hurst' in show_cols and 'Hurst' in subset.columns else 'Ticker'
            valid_cols = [c for c in show_cols if c in subset.columns]
            
            # Mostra ordenado (maior Hurst primeiro)
            print(subset[valid_cols].sort_values(by=sort_col, ascending=False).to_string(index=False))
        else:
            print("   - Nenhum ativo encontrado.")

    # 1. SINAIS FINAIS (FILTRADOS PELO HURST)
    # Usa 'Potencial_Alta' conforme seu analysis.py
    print("\n--- 1. SINAIS CONFIRMADOS (TENDÊNCIA + TÉCNICA) ---")
    print_group("COMPRA FORTE (Confirmada)", 'Potencial_Alta', show_cols=['Ticker', 'Preço', 'Hurst', 'Regime_Tendencia'])
    print_group("VENDA FORTE (Confirmada)", 'Potencial_Baixa', show_cols=['Ticker', 'Preço', 'Hurst', 'Regime_Tendencia'])

    # 2. REGIMES DE MERCADO
    print("\n--- 2. REGIMES DE MERCADO (Hurst Detrended) ---")
    print_group("ALTA TENDÊNCIA (Hurst > 0.6)", 'Regime_Tendencia', show_cols=['Ticker', 'Preço', 'Hurst'])
    print_group("MERCADO LATERAL/MEAN REVERSION (Hurst < 0.4)", 'Regime_Lateral', show_cols=['Ticker', 'Preço', 'Hurst', 'IFR'])

    # 3. CONSOLIDAÇÃO & SQUEEZE
    print("\n--- 3. ESTRUTURA E VOLATILIDADE ---")
    print_group("EM CONSOLIDAÇÃO (BB)", 'Filtro_Consolidacao', show_cols=['Ticker', 'Preço', 'Hurst'])
    print_group("POTENCIAL SQUEEZE (Explosão)", 'Potencial_Squeeze', show_cols=['Ticker', 'Preço', 'Hurst', 'Preco_Em_Compressao'])

    # 4. CANDIDATOS TÉCNICOS (SEM FILTRO)
    # Usa 'Potencial_Alta_Tecnico'
    print("\n--- 4. CANDIDATOS TÉCNICOS (SEM VALIDAÇÃO DE REGIME) ---")
    print_group("SETUP ALTA (Técnico Puro)", 'Potencial_Alta_Tecnico', show_cols=['Ticker', 'Preço', 'Hurst'])
    print_group("SETUP BAIXA (Técnico Puro)", 'Potencial_Baixa_Tecnico', show_cols=['Ticker', 'Preço', 'Hurst'])

    print("\n" + "="*80)
    print("Processamento concluído.")
    print("="*80)

if __name__ == "__main__":
    run_scanner()