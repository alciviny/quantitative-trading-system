# scripts/run_scanner.py

import pandas as pd
import logging
from tqdm import tqdm
import concurrent.futures
import os

# --- NOVAS IMPORTAÇÕES DO PROJETO ---
from co_piloto_quant.data.recorder import init_recorder_db, record_signal
from co_piloto_quant.data.data_fetching import fetch_batch_data
from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.universe import get_expanded_universe

from co_piloto_quant.data.indicator_engine import IndicatorEngine
from co_piloto_quant.strategies.loader import load_strategy
from co_piloto_quant import config
from co_piloto_quant.utils.math_tools import calculate_z_score
from co_piloto_quant.indicators.names import IndicatorNames

# Configuração do logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_single_ticker(ticker):
    """
    Processa um único ativo: carrega dados, calcula indicadores e aplica a estratégia.
    """
    try:
        # 1. Carregamento e Processamento Básico
        raw_df = load_price_data(ticker)
        if raw_df is None or raw_df.empty or len(raw_df) < config.HURST_WINDOW:
            return None
        # 1.5. Utiliza o DataFrame bruto diretamente para o IndicatorEngine
        df_for_indicators = raw_df

        # 2. Cálculo de Indicadores com IndicatorEngine
        engine = IndicatorEngine(df_for_indicators)
        engine.add_indicator(
            'bollinger_bands', 
            period=config.BB_PERIOD, 
            std_devs=[config.BB_ENTRY_STD_DEV_DEFAULT, 2.0]
        ).add_indicator(
            'stochastic',
            k_period=config.STOCH_K_PERIOD,
            k_smooth=config.STOCH_K_SMOOTH,
            d_smooth=config.STOCH_D_SMOOTH
        ).add_indicator(
            'system_tpm',
            indicator='obtr',
            period=config.SYSTEM_PERIOD
        ).add_indicator(
            'hurst',
            window=config.HURST_WINDOW,
            kind='price'
        ).add_indicator(
            'entropy',
            window=config.ENTROPY_WINDOW
        )
        
        df_with_indicators = engine.get_data()

        # 3. Cálculo de Z-Scores (separadamente, como no backtest)
        hurst_col = IndicatorNames.hurst(config.HURST_WINDOW, kind='price')
        entropy_col = IndicatorNames.entropy(config.ENTROPY_WINDOW)
        hurst_z_col = IndicatorNames.hurst_z(config.HURST_WINDOW, kind='price')
        entropy_z_col = IndicatorNames.entropy_z(config.ENTROPY_WINDOW)

        if hurst_col in df_with_indicators.columns:
            df_with_indicators[hurst_z_col] = calculate_z_score(df_with_indicators[hurst_col], window=config.HURST_WINDOW)

        if entropy_col in df_with_indicators.columns:
            df_with_indicators[entropy_z_col] = calculate_z_score(df_with_indicators[entropy_col], window=config.ENTROPY_WINDOW)

        if df_with_indicators.empty or df_with_indicators.iloc[-1].isnull().all():
            return None

        # 4. Aplicação da Estratégia (Modo Live)
        check_rules = load_strategy(mode='live')
        sinal = check_rules(df_with_indicators) # A estratégia live pega os dados que precisa

        latest_data = df_with_indicators.iloc[-1]

        return ticker, sinal, latest_data

    except Exception as e:
        logger.error(f"Erro ao processar {ticker}: {e}", exc_info=False)
        return None

def run_scanner():
    """
    Executa o scanner de mercado utilizando a estratégia ativa via loader.
    """
    tickers = get_expanded_universe()
    logger.info(f"Scanner iniciado para {len(tickers)} tickers com a estratégia '{config.ACTIVE_STRATEGY}'.")

    # 1. Atualização da Base de Dados
    logger.info("Verificando atualizações de dados...")
    try:
        fetch_batch_data(tickers, period="1y", interval="1d") # Busca um período menor para agilizar
    except Exception as e:
        logger.error(f"Erro no download em lote: {e}")

    all_results = []
    logger.info("Iniciando análise paralela...")

    # 2. Análise em Paralelo
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_ticker = {executor.submit(process_single_ticker, t): t for t in tickers}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Analisando Ativos"):
            result = future.result()
            if result:
                all_results.append(result)

    logger.info("Análise concluída. Gerando relatório...")

    # 3. Processamento e Relatório
    report_data = []
    
    for ticker, sinal, latest in all_results:
        action = sinal.get('action', 'NEUTRO')
        close_price = latest.get('close')
        
        # Gravação no Banco (se houver sinal)
        if action == 'COMPRA':
            record_signal(ticker, 'COMPRA_FINAL', close_price, sinal)
        elif action == 'VENDA':
            record_signal(ticker, 'VENDA_FINAL', close_price, sinal)

        # Dados para o Relatório de Console
        hurst_col = IndicatorNames.hurst(config.HURST_WINDOW, kind='price')
        entropy_col = IndicatorNames.entropy(config.ENTROPY_WINDOW)
        stoch_k_col = IndicatorNames.stochastic_k(config.STOCH_K_PERIOD, config.STOCH_K_SMOOTH)
        
        status_info = {
            'Ticker': ticker,
            'Preço': close_price,
            'Hurst': latest.get(hurst_col, 0.5),
            'Estocástico': latest.get(stoch_k_col),
            'Entropy_Score': latest.get(entropy_col, 10.0),
            'Ação': action,
            'Stop': sinal.get('stop_loss'),
            'Motivo': sinal.get('motivo', '')
        }
        report_data.append(status_info)

    # --- EXIBIÇÃO DO RELATÓRIO ---
    pd.set_option('display.float_format', lambda x: f'{x:.2f}')
    pd.set_option('display.max_rows', None) 
    pd.set_option('display.width', 120)

    print("\n" + "="*120)
    print(f"      RAIO-X DE MERCADO - ESTRATÉGIA ATIVA: {config.ACTIVE_STRATEGY} ({pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')})")
    print("="*120)

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
    print("\n--- 1. SINAIS IDENTIFICADOS ---")
    print_group("COMPRAS", "Ação == 'COMPRA'", ['Ticker', 'Preço', 'Stop', 'Estocástico', 'Hurst', 'Motivo'])
    print_group("VENDAS", "Ação == 'VENDA'", ['Ticker', 'Preço', 'Stop', 'Estocástico', 'Hurst', 'Motivo'])

    # 2. REGIMES
    hurst_query_tendencia = f"Hurst > {config.HURST_THRESHOLD_TREND}"
    hurst_query_reversao = f"Hurst < {config.HURST_THRESHOLD_REVERSION}"
    
    print("\n--- 2. CONTEXTO DE MERCADO (DIAGNÓSTICO) ---")
    print_group(f"ALTA TENDÊNCIA (Hurst > {config.HURST_THRESHOLD_TREND})", hurst_query_tendencia, ['Ticker', 'Preço', 'Hurst'])
    print_group(f"LATERAL / REVERSÃO (Hurst < {config.HURST_THRESHOLD_REVERSION})", hurst_query_reversao, ['Ticker', 'Preço', 'Hurst', 'Estocástico'])
    
    print("\n" + "="*120)
    print("Scanner finalizado com sucesso.")

if __name__ == "__main__":
    init_recorder_db()
    run_scanner()
