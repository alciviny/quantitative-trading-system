# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm
import concurrent.futures
import os
from pathlib import Path

# Imports do Projeto
from co_piloto_quant.data.recorder import init_recorder_db, record_signal
from co_piloto_quant.config import PROCESSED_DATA_PATH
from co_piloto_quant.data.data_fetching import fetch_batch_data
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.utils import get_expanded_universe
from co_piloto_quant.data.data_processing import process_data
from co_piloto_quant.analysis import calculate_indicators

# --- IMPORTAÇÃO DA NOVA ESTRATÉGIA ---
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_single_ticker(ticker):
    """
    Processa um único ativo: carrega dados, calcula indicadores e aplica a estratégia.
    """
    try:
        # 1. Carregamento
        raw_df = load_price_data(ticker)
        if raw_df.empty:
            return None

        # 2. Processamento Básico
        processed_df = process_data(raw_df, ticker)
        
        # 3. Cálculo de Indicadores (Pesado)
        df_with_indicators = calculate_indicators(processed_df)

        if df_with_indicators.empty or df_with_indicators.iloc[-1].isnull().all():
            return None

        # 4. --- APLICAÇÃO DA ESTRATÉGIA (NOVO) ---
        # Instancia a estratégia e executa o evaluate (vetorizado)
        strategy = AdaptiveSniperStrategy()
        df_analyzed = strategy.evaluate(df_with_indicators)

        # Salva o resultado processado (agora com colunas SIGNAL e STOP_LOSS)
        PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)
        file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
        df_analyzed.to_csv(file_path)

        # Pega apenas a última linha para o relatório do dia
        latest_data = df_analyzed.iloc[-1]

        return ticker, latest_data

    except Exception as e:
        logger.error(f"Erro ao processar {ticker}: {e}", exc_info=False)
        return None

def run_scanner():
    """
    Executa o scanner de mercado utilizando a AdaptiveSniperStrategy.
    """
    tickers = get_expanded_universe()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers.")

    # 1. Atualização da Base de Dados
    logger.info("Verificando atualizações de dados...")
    try:
        fetch_batch_data(tickers, period="max", interval="1d")
    except Exception as e:
        logger.error(f"Erro no download em lote: {e}")
        # Não retorna, tenta processar com o que tem

    all_results = []
    logger.info("Iniciando análise paralela (Strategy Pattern)...")

    # 2. Análise em Paralelo
    # Usa todos os núcleos da CPU para calcular indicadores e rodar a estratégia
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_ticker = {executor.submit(process_single_ticker, t): t for t in tickers}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Analisando"):
            result = future.result()
            if result:
                all_results.append(result)

    logger.info("Análise concluída. Gerando relatório...")

    # 3. Processamento e Relatório
    report_data = []
    
    for ticker, latest in all_results:
        # Extrai o sinal da nova coluna 'SIGNAL'
        signal = latest.get('SIGNAL', 'HOLD')
        close_price = latest.get('close')
        
        # Adaptador para manter compatibilidade com o recorder.py existente
        # Simula o dicionário que a check_rules antiga retornava
        rules_check_simulated = {
            'Sinal_Compra': signal == 'BUY',
            'Sinal_Venda': signal == 'SELL',
            'Stop_Loss_Sugerido_Long': latest.get('STOP_LOSS') if signal == 'BUY' else None,
            'Stop_Loss_Sugerido_Short': latest.get('STOP_LOSS') if signal == 'SELL' else None,
            'Motivo_Bloqueio': 'Strategy Evaluated'
        }

        # Gravação no Banco (se houver sinal)
        if signal == 'BUY':
            record_signal(ticker, 'COMPRA_FINAL', close_price, rules_check_simulated)
        elif signal == 'SELL':
            record_signal(ticker, 'VENDA_FINAL', close_price, rules_check_simulated)

        # Dados para o Relatório de Console
        hurst_val = latest.get('Hurst_72_returns', 0.5)
        entropy_val = latest.get('Entropy_20', 10.0)
        
        status_info = {
            'Ticker': ticker,
            'Preço': close_price,
            'Hurst': hurst_val,
            'Estocástico': latest.get(f'stoch_k_{80}_{3}'),
            'Entropy_Score': entropy_val,
            
            # Sinais Finais (Vindos da Estratégia)
            'Sinal_Compra_Final': signal == 'BUY',
            'Sinal_Venda_Final': signal == 'SELL',
            
            # Stops (Vindos da Estratégia)
            'Stop Sugerido Compra': rules_check_simulated['Stop_Loss_Sugerido_Long'],
            'Stop Sugerido Venda': rules_check_simulated['Stop_Loss_Sugerido_Short'],

            # Diagnósticos de Regime
            'Regime_Tendencia': hurst_val > 0.54,
            'Regime_Lateral': hurst_val < 0.46,
            'Regime_Caotico': entropy_val >= 3.2, # Entropia alta
            'Potencial_Squeeze': (
                latest.get('close') <= latest.get('BB_Upper_200_0.45', float('inf')) and
                latest.get('close') >= latest.get('BB_Lower_200_0.45', float('-inf'))
            )
        }
        report_data.append(status_info)

    # --- EXIBIÇÃO DO RELATÓRIO ---
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')
    pd.set_option('display.max_rows', None) 
    pd.set_option('display.width', 1000)

    print("\n" + "="*80)
    print(f"      RAIO-X DE MERCADO - STRATEGY PATTERN ({pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')})")
    print("="*80)

    if not report_data:
        print("Nenhum dado processado.")
        return

    df = pd.DataFrame(report_data)

    def print_group(title, query_expr, show_cols, sort_col='Ticker'):
        try:
            subset = df.query(query_expr)
            print(f"\n>> {title} (Total: {len(subset)})")
            if not subset.empty:
                valid_cols = [c for c in show_cols if c in subset.columns]
                print(subset[valid_cols].sort_values(by=sort_col).to_string(index=False))
            else:
                print("   - Nenhum ativo.")
        except Exception as e:
            print(f"Erro ao filtrar {title}: {e}")

    # 1. SINAIS
    print("\n--- 1. SINAIS CONFIRMADOS (ADAPTIVE SNIPER) ---")
    print_group("COMPRAS", "Sinal_Compra_Final == True", ['Ticker', 'Preço', 'Stop Sugerido Compra', 'Estocástico', 'Hurst'])
    print_group("VENDAS", "Sinal_Venda_Final == True", ['Ticker', 'Preço', 'Stop Sugerido Venda', 'Estocástico', 'Hurst'])

    # 2. REGIMES
    print("\n--- 2. CONTEXTO DE MERCADO ---")
    print_group("ALTA TENDÊNCIA (Hurst > 0.54)", "Regime_Tendencia == True", ['Ticker', 'Preço', 'Hurst'])
    print_group("LATERAL / REVERSÃO (Hurst < 0.46)", "Regime_Lateral == True", ['Ticker', 'Preço', 'Hurst', 'Estocástico'])
    print_group("SQUEEZE (Volatilidade Comprimida)", "Potencial_Squeeze == True", ['Ticker', 'Preço', 'Hurst'])
    print_group("PERIGO (Caos/Ruído Alto)", "Regime_Caotico == True", ['Ticker', 'Entropy_Score', 'Hurst'])

    print("\n" + "="*80)
    print("Scanner finalizado com sucesso.")

if __name__ == "__main__":
    init_recorder_db()
    run_scanner()