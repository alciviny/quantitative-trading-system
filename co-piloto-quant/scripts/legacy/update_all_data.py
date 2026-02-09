"""
Update All Data - Co-Piloto Quant
===================================

Pipeline completo usando a MESMA LÓGICA do build_dna_b3.py:
1. Baixa dados do yfinance via data_manager
2. Calcula indicadores via IndicatorEngine (entropy, hurst, half_life)
3. Salva no banco via data_manager.save_data()

Uso:
    python scripts/update_all_data.py
    python scripts/update_all_data.py --tickers PETR4.SA VALE3.SA
"""

import sys
import os
import logging
from pathlib import Path
from tqdm import tqdm
import argparse
import pandas as pd
import numpy as np

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.co_piloto_quant.data.data_manager import data_manager
from src.co_piloto_quant.data.indicator_engine import IndicatorEngine
from src.co_piloto_quant.universe import get_expanded_universe

# Configuração do Logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UpdateAllData")

MIN_HISTORY = 300  # Mínimo de linhas necessárias


def process_ticker_with_indicators(ticker: str, df: pd.DataFrame) -> dict:
    """
    Processa um ticker usando a MESMA LÓGICA do build_dna_b3.py:
    1. Valida dados
    2. Calcula indicadores via IndicatorEngine
    3. Salva via data_manager.save_data()
    """
    try:
        # 1. Validação (mesma do build_dna_b3.py)
        if df.empty or len(df) < MIN_HISTORY:
            return {
                'ticker': ticker,
                'status': 'no_data',
                'rows': len(df) if not df.empty else 0
            }
        
        # Limpeza básica (mesma do build_dna_b3.py)
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        
        df = df[[col for col in df.columns if not (isinstance(col, str) and col.startswith('('))]]
        df.columns = [str(col).lower() if not isinstance(col, str) else col.lower() for col in df.columns]
        
        if 'adj close' in df.columns: 
            df.rename(columns={'adj close': 'close'}, inplace=True)
        
        # 2. Calcula TODOS OS INDICADORES DISPONÍVEIS
        engine = IndicatorEngine(df)
        
        # --- Indicadores Especiais (Microestrutura) ---
        try:
            engine.add_indicator('entropy', window=20)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular entropy - {e}")
        
        try:
            engine.add_indicator('hurst', window=72, kind='returns')
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular hurst - {e}")
        
        try:
            engine.add_indicator('half_life', window=60)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular half_life - {e}")
        
        # --- Volatilidade ---
        try:
            engine.add_indicator('volatility', period=21)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular volatility - {e}")
        
        # --- Bollinger Bands ---
        try:
            engine.add_indicator('bollinger_bands', period=20, std_devs=[2.0, 3.0])
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular bollinger_bands - {e}")
        
        # --- IFR (RSI) ---
        try:
            engine.add_indicator('ifr', period=14)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ifr - {e}")
        
        # --- WWMA (Welles Wilder Moving Average) ---
        try:
            engine.add_indicator('ww_ma', period=14)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ww_ma - {e}")
        
        # --- Stochastic ---
        try:
            engine.add_indicator('stochastic', k_period=14, k_smooth=3, d_smooth=3)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular stochastic - {e}")
        
        # --- System TPM ---
        try:
            engine.add_indicator('system_tpm', period=14)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular system_tpm - {e}")
        
        # --- Ehlers Hilbert Sinewave ---
        try:
            engine.add_indicator('ehlers_hilbert')
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ehlers_hilbert - {e}")
        
        # --- Choppiness Index ---
        try:
            engine.add_indicator('choppiness', window=14)
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular choppiness - {e}")
        
        # Pega DataFrame enriquecido
        df_enriched = engine.get_data()
        
        # 3. Salva em Parquet (Feature Store - padrão profissional)
        features_path = Path(__file__).parent.parent / "data" / "features"
        features_path.mkdir(parents=True, exist_ok=True)
        
        # Normaliza nome do arquivo (remove .SA e substitui caracteres especiais)
        safe_ticker = ticker.replace('.SA', '_SA').replace('^', '_').replace('=', '_')
        output_file = features_path / f"{safe_ticker}_enriched.parquet"
        
        df_enriched.to_parquet(output_file, compression='snappy', index=True)
        
        return {
            'ticker': ticker,
            'status': 'success',
            'rows': len(df_enriched),
            'columns': len(df_enriched.columns),
            'output_file': str(output_file)
        }
        
    except Exception as e:
        logger.error(f"❌ {ticker}: Erro - {e}")
        return {
            'ticker': ticker,
            'status': 'error',
            'error': str(e)
        }


def update_all_data(tickers=None):
    """
    Pipeline completo usando a MESMA ESTRATÉGIA do build_dna_b3.py:
    - Usa data_manager.get_data_batch() para buscar em lote (rápido + cache)
    - Processa cada um com IndicatorEngine
    - Salva via data_manager.save_data()
    """
    logger.info("="*80)
    logger.info("🚀 UPDATE ALL DATA - Pipeline Completo")
    logger.info("="*80)
    
    # Determina lista de tickers
    if tickers:
        ticker_list = tickers
    else:
        ticker_list = get_expanded_universe()
    
    logger.info(f"📊 Processando {len(ticker_list)} ativos")
    logger.info("   1. Baixando/atualizando dados via data_manager (batch)")
    logger.info("   2. Calculando indicadores via IndicatorEngine")
    logger.info("   3. Salvando no SQLite via data_manager.save_data()")
    logger.info("")
    
    # PASSO 1: Busca em lote (MESMA LÓGICA do build_dna_b3.py linha 150)
    logger.info("⚡ Buscando dados em lote...")
    all_data = data_manager.get_data_batch(ticker_list)
    
    valid_data = {t: df for t, df in all_data.items() if df is not None and not df.empty}
    logger.info(f"✓ {len(valid_data)} ativos com dados válidos")
    logger.info("")
    
    # PASSO 2: Processa cada um (MESMA LÓGICA do build_dna_b3.py)
    results = []
    
    with tqdm(total=len(valid_data), desc="Processando", unit="ticker") as pbar:
        for ticker, df in valid_data.items():
            result = process_ticker_with_indicators(ticker, df)
            results.append(result)
            
            # Atualiza barra com status
            if result['status'] == 'success':
                status = f"✅ {ticker} ({result['rows']} linhas)"
            elif result['status'] == 'no_data':
                status = f"⚠️  {ticker} (histórico insuficiente)"
            else:
                status = f"❌ {ticker}"
            
            pbar.set_postfix_str(status)
            pbar.update(1)
    
    # Sumário
    success = [r for r in results if r['status'] == 'success']
    no_data = [r for r in results if r['status'] == 'no_data']
    errors = [r for r in results if r['status'] == 'error']
    
    logger.info("")
    logger.info("="*80)
    logger.info("📊 SUMÁRIO DA EXECUÇÃO")
    logger.info("="*80)
    logger.info(f"✅ Processados com sucesso: {len(success)}/{len(ticker_list)}")
    logger.info(f"⚠️  Sem dados suficientes: {len(no_data)}")
    logger.info(f"❌ Erros: {len(errors)}")
    
    if success:
        total_rows = sum(r['rows'] for r in success)
        logger.info(f"📈 Total de linhas processadas: {total_rows:,}")
    
    if errors:
        logger.info("")
        logger.info("❌ Tickers com erro:")
        for r in errors:
            logger.info(f"   - {r['ticker']}: {r.get('error', 'unknown')}")
    
    logger.info("="*80)
    logger.info("✅ Processo concluído!")
    logger.info("   📊 Dados brutos: data/raw/market_data.db")
    logger.info("   🎯 Features computadas: data/features/*_enriched.parquet")
    logger.info("   📈 Use build_dna_b3.py para gerar relatórios")
    logger.info("="*80)
    
    return results


def main():
    """Entry point CLI"""
    parser = argparse.ArgumentParser(
        description="Update All Data - Baixa dados e calcula indicadores",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Atualizar todos os ativos do universo
  python scripts/update_all_data.py
  
  # Atualizar apenas ativos específicos
  python scripts/update_all_data.py --tickers PETR4.SA VALE3.SA ITUB4.SA
        """
    )
    
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Lista de tickers para processar (default: todos do universo)'
    )
    
    args = parser.parse_args()
    
    try:
        results = update_all_data(tickers=args.tickers)
        
        # Exit code baseado em sucesso
        errors = len([r for r in results if r['status'] == 'error'])
        sys.exit(0 if errors == 0 else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Processo interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
