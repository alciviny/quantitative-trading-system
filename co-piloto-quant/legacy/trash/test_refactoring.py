import pandas as pd
import os
import logging
from tqdm import tqdm
import concurrent.futures

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_strategy_on_ticker(ticker: str):
    """
    Carrega dados, calcula indicadores e avalia a estratégia para um único ativo.
    Este é o fluxo de ponta a ponta que valida a refatoração.
    """
    try:
        # 1. Carregar dados
        df_raw = load_price_data(ticker)
        if df_raw is None or df_raw.empty or len(df_raw) < 200:
            logger.warning(f"Dados insuficientes ou nulos para {ticker}. Pulando.")
            return None

        # 2. Calcular Indicadores (usa o analysis.py refatorado)
        df_indicators = calculate_indicators(df_raw)
        
        if df_indicators is None or df_indicators.empty:
            logger.warning(f"Cálculo de indicadores falhou para {ticker}. Pulando.")
            return None

        # 3. Avaliar Estratégia (usa o strategies/base.py refatorado)
        strategy = AdaptiveSniperStrategy()
        df_signals = strategy.evaluate(df_indicators)

        # 4. Verificação Simples
        if 'SIGNAL' in df_signals.columns and (df_signals['SIGNAL'] != 'HOLD').any():
            buy_signals = (df_signals['SIGNAL'] == 'BUY').sum()
            sell_signals = (df_signals['SIGNAL'] == 'SELL').sum()
            logger.info(f"Sucesso para {ticker}: Encontrados {buy_signals} sinais de COMPRA e {sell_signals} de VENDA.")
            return ticker # Retorna sucesso
        else:
            logger.info(f"Executado para {ticker}, mas nenhum sinal de Compra/Venda gerado.")
            return ticker # Retorna sucesso, pois rodou sem erros

    except Exception as e:
        # O erro mais provável de acontecer por uma refatoração mal sucedida seria um KeyError
        logger.error(f"ERRO CRÍTICO no processamento de {ticker}: {e}", exc_info=True)
        return None

if __name__ == "__main__":
    # Para um teste rápido e focado, usamos uma lista pequena de ativos conhecidos.
    test_tickers = ["PETR4.SA", "VALE3.SA", "MGLU3.SA", "ITUB4.SA", "BBDC4.SA"]
    
    successful_tickers = []
    
    logger.info(f"--- INICIANDO TESTE DE INTEGRAÇÃO PÓS-REFATORAÇÃO PARA {len(test_tickers)} ATIVOS ---")
    
    # O teste pode ser sequencial para facilitar a leitura dos logs
    for ticker in tqdm(test_tickers, desc="Testando Ativos"):
        result = run_strategy_on_ticker(ticker)
        if result:
            successful_tickers.append(result)

    logger.info("-" * 50)
    logger.info("--- RESULTADO DO TESTE ---")
    
    if len(successful_tickers) == len(test_tickers):
        logger.info(f"✅ SUCESSO! Todos os {len(test_tickers)} ativos foram processados sem erros.")
        logger.info("A refatoração parece ter sido bem-sucedida. Os nomes das colunas estão consistentes.")
    else:
        failed_count = len(test_tickers) - len(successful_tickers)
        logger.error(f"❌ FALHA! {failed_count} de {len(test_tickers)} ativos falharam durante o processamento.")
        logger.error("Verifique os logs de erro acima para encontrar um 'ERRO CRÍTICO', que provavelmente será um 'KeyError' se a refatoração for a causa.")

    logger.info("-" * 50)
