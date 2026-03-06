"""
Data Pipeline - Co-Piloto Quant
================================

Pipeline institucional unificado para dados e features.

Arquitetura:
    Raw Data (yfinance) → SQLite (OHLCV) → Feature Engineering → Parquet (Feature Store)

Responsabilidades:
    1. Download de dados (via data_manager com cache)
    2. Persistência raw em SQLite (backup + auditoria)
    3. Cálculo de TODAS as features disponíveis
    4. Persistência em Parquet (Feature Store para análises)
    5. Logging completo e profissional

Execução:
    python scripts/data_pipeline.py                              # Todos os ativos
    python scripts/data_pipeline.py --tickers PETR4.SA VALE3.SA  # Ativos específicos
    python scripts/data_pipeline.py --force-update               # Força re-download

Autor: Co-Piloto Quant Team
Data: 2026-02-08
"""

import sys
import os
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import argparse

import pandas as pd
import numpy as np
from tqdm import tqdm

# Adiciona o diretório raiz ao sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.co_piloto_quant.data.data_manager import data_manager
from src.co_piloto_quant.data.indicator_engine import IndicatorEngine
from src.co_piloto_quant.config import (
    BB_PERIOD, PRICE_BB_DEVIATIONS, IFR_PERIOD, SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
    STOCH_K_PERIOD, STOCH_K_SMOOTH, STOCH_D_SMOOTH, HURST_WINDOW, ENTROPY_WINDOW
)
from src.co_piloto_quant.universe import get_expanded_universe


# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

MIN_HISTORY = 300  # Mínimo de linhas necessárias


def setup_logging():
    """Configura logging profissional"""
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / 'data_pipeline.log', mode='a')
        ]
    )
    return logging.getLogger("DataPipeline")


logger = setup_logging()


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

def calculate_all_features(df: pd.DataFrame, ticker: str) -> Optional[pd.DataFrame]:
    """
    Calcula TODAS as features disponíveis usando IndicatorEngine.
    
    Features incluídas:
        - Microestrutura: entropy, hurst, half_life
        - Volatilidade: volatility
        - Bandas: bollinger_bands
        - Momentum: ifr (RSI), stochastic
        - Médias: ww_ma (Welles Wilder)
        - Sistemas: system_tpm
        - Ciclos: ehlers_hilbert
        - Tendência: choppiness
    
    Args:
        df: DataFrame com OHLCV
        ticker: Nome do ativo (para logging)
    
    Returns:
        DataFrame enriquecido com features ou None se erro
    """
    try:
        engine = IndicatorEngine(df)
        
        # --- Indicadores Especiais (Microestrutura) ---

        try:
            engine.add_indicator('entropy', window=ENTROPY_WINDOW)
            logger.debug(f"{ticker}: ✓ Entropy calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular entropy - {e}")

        try:
            engine.add_indicator('hurst', window=HURST_WINDOW, kind='returns')
            logger.debug(f"{ticker}: ✓ Hurst calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular hurst - {e}")

        try:
            engine.add_indicator('half_life', window=60)
            logger.debug(f"{ticker}: ✓ Half-Life calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular half_life - {e}")

        # --- Volatilidade ---
        try:
            engine.add_indicator('volatility', period=21)
            logger.debug(f"{ticker}: ✓ Volatility calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular volatility - {e}")

        # --- Bollinger Bands ---
        try:
            engine.add_indicator('bollinger_bands', period=BB_PERIOD, std_devs=PRICE_BB_DEVIATIONS)
            logger.debug(f"{ticker}: ✓ Bollinger Bands calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular bollinger_bands - {e}")

        # --- IFR (RSI) ---
        try:
            engine.add_indicator('ifr', period=IFR_PERIOD)
            logger.debug(f"{ticker}: ✓ IFR/RSI calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ifr - {e}")

        # --- WWMA (Welles Wilder Moving Average) ---
        try:
            engine.add_indicator('ww_ma', period=IFR_PERIOD)
            logger.debug(f"{ticker}: ✓ WWMA calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ww_ma - {e}")

        # --- Stochastic ---
        try:
            engine.add_indicator('stochastic', k_period=STOCH_K_PERIOD, k_smooth=STOCH_K_SMOOTH, d_smooth=STOCH_D_SMOOTH)
            logger.debug(f"{ticker}: ✓ Stochastic calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular stochastic - {e}")

        # --- System TPM ---
        try:
            engine.add_indicator('system_tpm', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
            logger.debug(f"{ticker}: ✓ System TPM calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular system_tpm - {e}")

        # --- Ehlers Hilbert Sinewave ---
        try:
            engine.add_indicator('ehlers_hilbert')
            logger.debug(f"{ticker}: ✓ Ehlers Hilbert calculado")
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular ehlers_hilbert - {e}")

        # NOTA: Choppiness Index removido (requer pandas-ta não instalado)

        # Retorna DataFrame enriquecido
        df_enriched = engine.get_data()

        # Remove colunas duplicadas (mantém primeira ocorrência)
        df_enriched = df_enriched.loc[:, ~df_enriched.columns.duplicated()]

        logger.info(f"{ticker}: ✅ {len(df_enriched.columns)} colunas totais ({len(df_enriched)} linhas)")

        return df_enriched
        
    except Exception as e:
        logger.error(f"{ticker}: ❌ Erro fatal no cálculo de features - {e}")
        return None


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

def process_single_ticker(ticker: str, force_update: bool = False) -> Dict[str, Any]:
    """
    Processa um único ticker através de todo o pipeline.
    
    Pipeline:
        1. Download/cache (data_manager)
        2. Validação de dados
        3. Limpeza e normalização
        4. Cálculo de features
        5. Persistência SQLite (data_manager.save_data)
        6. Persistência Parquet (Feature Store)
    
    Args:
        ticker: Símbolo do ativo
        force_update: Se True, força re-download (ignora cache)
    
    Returns:
        Dict com status do processamento
    """
    try:
        # 1. Download/Cache via data_manager
        logger.info(f"{ticker}: Iniciando download/cache...")
        df = data_manager.get_data(ticker, force_update=force_update)
        
        # 2. Validação básica
        if df is None or df.empty:
            return {
                'ticker': ticker,
                'status': 'no_data',
                'rows': 0,
                'error': 'Sem dados retornados'
            }
        
        if len(df) < MIN_HISTORY:
            return {
                'ticker': ticker,
                'status': 'insufficient_data',
                'rows': len(df),
                'error': f'Histórico insuficiente ({len(df)} < {MIN_HISTORY})'
            }
        
        logger.info(f"{ticker}: ✓ {len(df)} linhas baixadas/carregadas")
        
        # 3. Limpeza e normalização (mesma do build_dna_b3.py)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df = df[[col for col in df.columns if not (isinstance(col, str) and col.startswith('('))]]
        df.columns = [str(col).lower() if not isinstance(col, str) else col.lower() for col in df.columns]
        
        if 'adj close' in df.columns:
            df.rename(columns={'adj close': 'close'}, inplace=True)
        
        logger.debug(f"{ticker}: ✓ Dados normalizados")
        
        # 4. Cálculo de TODAS as features
        logger.info(f"{ticker}: Calculando features...")
        df_enriched = calculate_all_features(df, ticker)
        
        if df_enriched is None:
            return {
                'ticker': ticker,
                'status': 'calculation_error',
                'rows': len(df),
                'error': 'Erro no cálculo de features'
            }
        
        # 5. Persistência em SQLite (dados brutos OHLCV - via data_manager)
        # NOTA: data_manager.save_data() automaticamente limpa indicadores,
        # mantendo apenas OHLCV no SQLite (por design)
        try:
            data_manager.save_data(ticker, df[['open', 'high', 'low', 'close', 'volume']])
            logger.debug(f"{ticker}: ✓ Dados brutos salvos em SQLite")
        except Exception as e:
            logger.warning(f"{ticker}: Aviso ao salvar SQLite - {e}")
        
        # 6. Persistência em Parquet (Feature Store - dados enriquecidos)
        features_path = Path(__file__).parent.parent / "src" / "co_piloto_quant" / "data" / "features"
        features_path.mkdir(parents=True, exist_ok=True)
        
        safe_ticker = ticker.replace('.SA', '_SA').replace('^', '_').replace('=', '_')
        output_file = features_path / f"{safe_ticker}_enriched.parquet"
        
        df_enriched.to_parquet(output_file, compression='snappy', index=True)
        logger.info(f"{ticker}: ✅ Feature Store atualizado → {output_file.name}")
        
        return {
            'ticker': ticker,
            'status': 'success',
            'rows': len(df_enriched),
            'columns': len(df_enriched.columns),
            'sqlite_path': 'src/co_piloto_quant/data/raw/market_data.db',
            'parquet_path': str(output_file.relative_to(Path(__file__).parent.parent))
        }
        
    except Exception as e:
        logger.error(f"{ticker}: ❌ Erro fatal no pipeline - {e}", exc_info=True)
        return {
            'ticker': ticker,
            'status': 'error',
            'error': str(e)
        }


def run_pipeline(tickers: Optional[List[str]] = None, force_update: bool = False):
    """
    Executa o pipeline completo para múltiplos ativos.
    
    Args:
        tickers: Lista de tickers (None = todos do universo)
        force_update: Se True, força re-download
    """
    logger.info("="*80)
    logger.info("🚀 DATA PIPELINE - Co-Piloto Quant")
    logger.info("="*80)
    logger.info("")
    logger.info("Pipeline:")
    logger.info("  1. Download via yfinance (cache via data_manager)")
    logger.info("  2. Persistência OHLCV em SQLite")
    logger.info("  3. Cálculo de TODAS as features (11 indicadores)")
    logger.info("  4. Persistência em Parquet (Feature Store)")
    logger.info("")
    
    # Determina lista de tickers
    if tickers:
        ticker_list = tickers
        logger.info(f"📊 Modo: Ativos específicos ({len(ticker_list)} tickers)")
    else:
        ticker_list = get_expanded_universe()
        logger.info(f"📊 Modo: Universo completo ({len(ticker_list)} tickers)")
    
    if force_update:
        logger.info("⚠️  Force Update: ON (ignorando cache)")
    
    logger.info("")
    logger.info("="*80)
    
    # Passo 1: Busca em lote (com cache)
    logger.info("⚡ FASE 1/2: Download/Cache em lote...")
    all_data = data_manager.get_data_batch(ticker_list)
    
    valid_data = {t: df for t, df in all_data.items() if df is not None and not df.empty}
    logger.info(f"✓ {len(valid_data)}/{len(ticker_list)} ativos com dados válidos")
    logger.info("")
    
    # Passo 2: Processa cada um
    logger.info("⚡ FASE 2/2: Feature Engineering + Persistência...")
    # Determina lista de tickers
    if tickers:
        ticker_list = tickers
        logger.info(f"\U0001f4ca Modo: Ativos específicos ({len(ticker_list)} tickers)")
    else:
        ticker_list = get_expanded_universe()
        logger.info(f"\U0001f4ca Modo: Universo completo ({len(ticker_list)} tickers)")


    # Filtra apenas ativos brasileiros (.SA)
    br_ticker_list = [t for t in ticker_list if isinstance(t, str) and t.upper().endswith('.SA')]
    logger.info(f"Universo filtrado para ativos brasileiros: {len(br_ticker_list)} ativos (.SA)")
    if not br_ticker_list:
        logger.error("Nenhum ativo brasileiro (.SA) encontrado. Abortando pipeline.")
        return []

    if force_update:
        logger.info("\u26a0\ufe0f  Force Update: ON (ignorando cache)")

    logger.info("")
    logger.info("="*80)

    # Passo 1: Busca em lote (com cache)
    logger.info("\u26a1 FASE 1/2: Download/Cache em lote...")
    try:
        all_data = data_manager.get_data_batch(br_ticker_list)
    except Exception as e:
        logger.error(f"Erro ao baixar dados em batch: {e}", exc_info=True)
        return []


    valid_data = {t: df for t, df in all_data.items() if df is not None and not df.empty}
    logger.info(f"\u2713 {len(valid_data)}/{len(br_ticker_list)} ativos com dados válidos")
    logger.info("")

    if not valid_data:
        logger.error("Nenhum ativo com dados válidos foi baixado. Pipeline encerrado sem cálculo de features.")
        return []

    # Passo 2: Processa cada um
    logger.info("\u26a1 FASE 2/2: Feature Engineering + Persistência...")
    results = []

    with tqdm(total=len(valid_data), desc="Pipeline", unit="ticker") as pbar:
        for ticker in valid_data.keys():
            try:
                logger.info(f"Iniciando processamento do ticker: {ticker}")
                result = process_single_ticker(ticker, force_update)
                logger.info(f"Resultado do processamento de {ticker}: {result}")
                results.append(result)
            except Exception as e:
                logger.error(f"Erro inesperado ao processar {ticker}: {e}")
            pbar.update(1)

    # Resumo final
    logger.info("")
    logger.info("="*80)
    logger.info("\U0001f4ca RESUMO DA EXECUÇÃO")
    logger.info("="*80)

    success = [r for r in results if r['status'] == 'success']
    no_data = [r for r in results if r['status'] == 'no_data']
    insufficient = [r for r in results if r['status'] == 'insufficient_data']
    errors = [r for r in results if r['status'] == 'error']

    logger.info(f"\u2705 Processados com sucesso: {len(success)}/{len(br_ticker_list)}")
    logger.info(f"\u26a0\ufe0f  Sem dados suficientes: {len(no_data) + len(insufficient)}")
    logger.info(f"\u274c Erros: {len(errors)}")

    if success:
        total_rows = sum(r['rows'] for r in success)
        logger.info(f"\U0001f4c8 Total de linhas processadas: {total_rows:,}")

    logger.info("")
    logger.info("\U0001f4e6 Persistência:")
    logger.info("   \U0001f4ca Dados brutos (OHLCV): src/co_piloto_quant/data/raw/market_data.db")
    logger.info("   \U0001f3af Features computadas: src/co_piloto_quant/data/features/*_enriched.parquet")
    logger.info("")

    if errors:
        logger.warning("\u274c Ativos com erro:")
        for r in errors[:10]:  # Mostra apenas os 10 primeiros
            logger.warning(f"   - {r['ticker']}: {r.get('error', 'Erro desconhecido')}")
        if len(errors) > 10:
            logger.warning(f"   ... e mais {len(errors) - 10} erros")
        logger.info("")

    logger.info("="*80)
    logger.info("\u2705 Pipeline concluído!")
    logger.info("="*80)

    return results
    
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='Força re-download dos dados (ignora cache)'
    )
    
    args = parser.parse_args()
    
    # Executa pipeline
    start_time = datetime.now()
    
    try:
        run_pipeline(
            tickers=args.tickers,
            force_update=args.force_update
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal no pipeline: {e}", exc_info=True)
        sys.exit(1)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️  Tempo total: {elapsed:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Data Pipeline - Co-Piloto Quant")
    parser.add_argument(
        '--tickers',
        nargs='*',
        help='Lista de tickers a processar (ex: PETR4.SA VALE3.SA). Se omitido, processa todos.'
    )
    parser.add_argument(
        '--force-update',
        action='store_true',
        help='Força re-download dos dados (ignora cache)'
    )
    args = parser.parse_args()

    # Executa pipeline
    start_time = datetime.now()

    try:
        run_pipeline(
            tickers=args.tickers,
            force_update=args.force_update
        )
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal no pipeline: {e}", exc_info=True)
        sys.exit(1)

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"⏱️  Tempo total: {elapsed:.1f}s")

if __name__ == "__main__":
    main()
