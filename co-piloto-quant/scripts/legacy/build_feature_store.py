"""
Feature Store Builder - Co-Piloto Quant
========================================

Pipeline profissional de pré-processamento de features para trading quantitativo.

Arquitetura:
    Raw Data → Feature Engineering → Feature Store → API → Frontend

Execução:
    python scripts/build_feature_store.py
    python scripts/build_feature_store.py --tickers PETR4_SA VALE3_SA
    python scripts/build_feature_store.py --workers 8
"""

import sys
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from datetime import datetime
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings

import pandas as pd
import numpy as np
from tqdm import tqdm

# Importações dos indicadores
INDICATORS_AVAILABLE = False
try:
    # Adiciona src/ ao path para importações
    import sys
    from pathlib import Path
    src_path = Path(__file__).parent.parent / "src"
    if src_path.exists():
        sys.path.insert(0, str(src_path))
    
    # Import direto sem passar pelo __init__.py que tem dependências problemáticas
    from co_piloto_quant.indicators.special import fractal_dimension
    from co_piloto_quant.indicators.special import lempel_ziv
    from co_piloto_quant.indicators.special import market_entropy
    from co_piloto_quant.indicators.special import hurst_exponent
    from co_piloto_quant.indicators.special import half_life
    from co_piloto_quant.indicators.special import frac_diff
    
    calculate_rolling_fdi = fractal_dimension.calculate_rolling_fdi
    calculate_rolling_lzc = lempel_ziv.calculate_rolling_lzc
    calculate_rolling_entropy = market_entropy.calculate_rolling_entropy
    calculate_rolling_hurst = hurst_exponent.calculate_rolling_hurst
    calculate_rolling_ou_params = half_life.calculate_rolling_ou_params
    fractional_diff_fixed_window = frac_diff.fractional_diff_fixed_window
    
    INDICATORS_AVAILABLE = True
    logging.info("✅ Indicadores especiais carregados com sucesso")
except ImportError as e:
    logging.warning(f"⚠️  Indicadores especiais não encontrados: {e}")
    logging.warning(f"   Verifique se src/co_piloto_quant/ existe")
    INDICATORS_AVAILABLE = False

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURAÇÃO
# ============================================================================

@dataclass
class FeatureStoreConfig:
    """Configuração do Feature Store"""
    base_path: Path
    processed_path: Path
    features_path: Path
    lookback_days: int = 252  # 1 ano de dados para indicadores
    parallel_workers: int = 4
    chunk_size: int = 10
    
    # Parâmetros dos indicadores
    hurst_window: int = 100
    entropy_window: int = 20
    fdi_window: int = 50
    lzc_window: int = 60
    halflife_window: int = 50
    fracdiff_d: float = 0.5
    fracdiff_window: int = 20


def setup_logging():
    """Configura logging profissional"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/feature_store.log', mode='a')
        ]
    )
    return logging.getLogger(__name__)


# ============================================================================
# FEATURE ENGINEERING
# ============================================================================

class FeatureEngineer:
    """Engine de cálculo de features"""
    
    def __init__(self, config: FeatureStoreConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def load_raw_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """Carrega dados brutos do Parquet"""
        try:
            file_path = self.config.processed_path / f"{ticker}.parquet"
            if not file_path.exists():
                self.logger.warning(f"❌ {ticker}: Arquivo não encontrado")
                return None
            
            df = pd.read_parquet(file_path)
            
            # Validação básica
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            if not all(col in df.columns for col in required_cols):
                self.logger.error(f"❌ {ticker}: Colunas inválidas")
                return None
            
            # Garantir índice temporal
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'date' in df.columns:
                    df = df.set_index('date')
                elif 'timestamp' in df.columns:
                    df = df.set_index('timestamp')
            
            return df.sort_index()
            
        except Exception as e:
            self.logger.error(f"❌ {ticker}: Erro ao carregar - {e}")
            return None
    
    def calculate_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula features básicas (rápidas)"""
        try:
            # Retornos
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
            
            # Volatilidade
            df['volatility_20'] = df['returns'].rolling(20).std()
            df['volatility_60'] = df['returns'].rolling(60).std()
            
            # Volume
            df['volume_ma_20'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma_20']
            
            # Ranges
            df['true_range'] = np.maximum.reduce([
                df['high'] - df['low'],
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            ])
            df['atr_14'] = df['true_range'].rolling(14).mean()
            
            # Momentum
            df['roc_10'] = (df['close'] / df['close'].shift(10) - 1) * 100
            df['roc_20'] = (df['close'] / df['close'].shift(20) - 1) * 100
            
            # Médias Móveis
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()
            df['sma_200'] = df['close'].rolling(200).mean()
            
            # Distância das médias
            df['dist_sma_20'] = (df['close'] - df['sma_20']) / df['sma_20'] * 100
            df['dist_sma_50'] = (df['close'] - df['sma_50']) / df['sma_50'] * 100
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro em features básicas: {e}")
            return df
    
    def calculate_advanced_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula features avançadas (indicadores complexos)"""
        if not INDICATORS_AVAILABLE:
            self.logger.warning("⚠️  Indicadores avançados não disponíveis")
            return df
        
        try:
            close = df['close']
            
            # Hurst Exponent (Persistência)
            try:
                df['hurst_exponent'] = calculate_rolling_hurst(
                    close, 
                    window=self.config.hurst_window,
                    kind='returns'
                )
            except Exception as e:
                self.logger.warning(f"Hurst falhou: {e}")
                df['hurst_exponent'] = np.nan
            
            # Market Entropy (Caos/Ordem)
            try:
                df['market_entropy'] = calculate_rolling_entropy(
                    close,
                    window=self.config.entropy_window
                )
            except Exception as e:
                self.logger.warning(f"Entropy falhou: {e}")
                df['market_entropy'] = np.nan
            
            # Fractal Dimension Index (Complexidade)
            try:
                df['fractal_dimension'] = calculate_rolling_fdi(
                    close,
                    window=self.config.fdi_window
                )
            except Exception as e:
                self.logger.warning(f"FDI falhou: {e}")
                df['fractal_dimension'] = np.nan
            
            # Lempel-Ziv Complexity
            try:
                returns = close.pct_change().fillna(0)
                df['lempel_ziv'] = calculate_rolling_lzc(
                    returns,
                    window=self.config.lzc_window
                )
            except Exception as e:
                self.logger.warning(f"LZC falhou: {e}")
                df['lempel_ziv'] = np.nan
            
            # Half-Life (Mean Reversion)
            try:
                ou_params = calculate_rolling_ou_params(
                    close,
                    window=self.config.halflife_window
                )
                if isinstance(ou_params, pd.DataFrame):
                    df['half_life'] = ou_params['half_life']
                    df['mean_reversion_speed'] = ou_params['theta']
            except Exception as e:
                self.logger.warning(f"Half-Life falhou: {e}")
                df['half_life'] = np.nan
                df['mean_reversion_speed'] = np.nan
            
            # Fractional Differentiation (Estacionariedade)
            try:
                df['frac_diff'] = fractional_diff_fixed_window(
                    close,
                    d=self.config.fracdiff_d,
                    window=self.config.fracdiff_window
                )
            except Exception as e:
                self.logger.warning(f"FracDiff falhou: {e}")
                df['frac_diff'] = np.nan
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro em features avançadas: {e}")
            return df
    
    def calculate_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta regime de mercado"""
        try:
            # Trending vs Mean-Reverting
            if 'hurst_exponent' in df.columns:
                df['regime_trend'] = np.where(
                    df['hurst_exponent'] > 0.55, 'trending',
                    np.where(df['hurst_exponent'] < 0.45, 'mean_reverting', 'random')
                )
            
            # Volatility Regime
            if 'volatility_20' in df.columns:
                vol_median = df['volatility_20'].rolling(60).median()
                df['regime_volatility'] = np.where(
                    df['volatility_20'] > vol_median * 1.5, 'high_vol',
                    np.where(df['volatility_20'] < vol_median * 0.5, 'low_vol', 'normal_vol')
                )
            
            # Market Efficiency (via Entropy)
            if 'market_entropy' in df.columns:
                df['regime_efficiency'] = np.where(
                    df['market_entropy'] < 2.0, 'efficient',
                    np.where(df['market_entropy'] > 3.0, 'chaotic', 'mixed')
                )
            
            return df
            
        except Exception as e:
            self.logger.error(f"Erro em regime features: {e}")
            return df
    
    def add_metadata(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Adiciona metadados ao DataFrame"""
        df.attrs['ticker'] = ticker
        df.attrs['feature_timestamp'] = datetime.now().isoformat()
        df.attrs['lookback_days'] = self.config.lookback_days
        df.attrs['version'] = '1.0'
        return df
    
    def process_ticker(self, ticker: str) -> Dict[str, Any]:
        """Pipeline completo para um ticker"""
        start_time = datetime.now()
        
        try:
            # 1. Carrega dados
            df = self.load_raw_data(ticker)
            if df is None:
                return {'ticker': ticker, 'status': 'failed', 'error': 'load_error'}
            
            # 2. Features básicas
            df = self.calculate_basic_features(df)
            
            # 3. Features avançadas
            df = self.calculate_advanced_features(df)
            
            # 4. Regime detection
            df = self.calculate_regime_features(df)
            
            # 5. Metadados
            df = self.add_metadata(df, ticker)
            
            # 6. Salva
            output_path = self.config.features_path / f"{ticker}_enriched.parquet"
            df.to_parquet(output_path, compression='snappy', index=True)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            return {
                'ticker': ticker,
                'status': 'success',
                'rows': len(df),
                'features': len(df.columns),
                'elapsed_seconds': elapsed,
                'output_file': str(output_path)
            }
            
        except Exception as e:
            self.logger.error(f"❌ {ticker}: Erro no processamento - {e}")
            return {'ticker': ticker, 'status': 'failed', 'error': str(e)}


# ============================================================================
# PIPELINE PRINCIPAL
# ============================================================================

class FeatureStorePipeline:
    """Orquestrador do pipeline de features"""
    
    def __init__(self, config: FeatureStoreConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.engineer = FeatureEngineer(config)
    
    def get_tickers(self, ticker_list: Optional[List[str]] = None) -> List[str]:
        """Obtém lista de tickers para processar"""
        if ticker_list:
            return ticker_list
        
        # Descobre todos os parquets em processed/
        parquet_files = list(self.config.processed_path.glob("*.parquet"))
        tickers = [f.stem for f in parquet_files]
        return sorted(tickers)
    
    def run_sequential(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Execução sequencial (para debug)"""
        results = []
        
        with tqdm(total=len(tickers), desc="📊 Processando Features", unit="ticker") as pbar:
            for ticker in tickers:
                result = self.engineer.process_ticker(ticker)
                results.append(result)
                
                # Atualiza barra com status
                status_icon = "✅" if result['status'] == 'success' else "❌"
                pbar.set_postfix_str(f"{status_icon} {ticker}")
                pbar.update(1)
        
        return results
    
    def run_parallel(self, tickers: List[str]) -> List[Dict[str, Any]]:
        """Execução paralela (para produção)"""
        results = []
        
        with ProcessPoolExecutor(max_workers=self.config.parallel_workers) as executor:
            # Submete jobs
            futures = {
                executor.submit(self.engineer.process_ticker, ticker): ticker
                for ticker in tickers
            }
            
            # Coleta resultados com progress bar
            with tqdm(total=len(tickers), desc="📊 Processando Features", unit="ticker") as pbar:
                for future in as_completed(futures):
                    ticker = futures[future]
                    try:
                        result = future.result()
                        results.append(result)
                        
                        status_icon = "✅" if result['status'] == 'success' else "❌"
                        pbar.set_postfix_str(f"{status_icon} {ticker}")
                    except Exception as e:
                        self.logger.error(f"❌ {ticker}: Crash - {e}")
                        results.append({'ticker': ticker, 'status': 'crashed', 'error': str(e)})
                    
                    pbar.update(1)
        
        return results
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Imprime sumário da execução"""
        successful = [r for r in results if r['status'] == 'success']
        failed = [r for r in results if r['status'] != 'success']
        
        total_rows = sum(r.get('rows', 0) for r in successful)
        total_time = sum(r.get('elapsed_seconds', 0) for r in successful)
        avg_time = total_time / len(successful) if successful else 0
        
        self.logger.info("\n" + "="*80)
        self.logger.info("📊 FEATURE STORE - SUMÁRIO DA EXECUÇÃO")
        self.logger.info("="*80)
        self.logger.info(f"✅ Processados com sucesso: {len(successful)}/{len(results)}")
        self.logger.info(f"❌ Falhas: {len(failed)}")
        self.logger.info(f"📈 Total de linhas processadas: {total_rows:,}")
        self.logger.info(f"⏱️  Tempo médio por ticker: {avg_time:.2f}s")
        self.logger.info(f"💾 Arquivos salvos em: {self.config.features_path}")
        
        if failed:
            self.logger.warning("\n❌ Tickers com falhas:")
            for r in failed:
                self.logger.warning(f"   - {r['ticker']}: {r.get('error', 'unknown')}")
        
        self.logger.info("="*80 + "\n")
    
    def run(self, tickers: Optional[List[str]] = None, parallel: bool = True):
        """Executa pipeline completo"""
        self.logger.info("🚀 Iniciando Feature Store Pipeline...")
        
        # Descobre tickers
        tickers_to_process = self.get_tickers(tickers)
        self.logger.info(f"📊 {len(tickers_to_process)} tickers para processar")
        
        # Executa
        if parallel and len(tickers_to_process) > 1:
            results = self.run_parallel(tickers_to_process)
        else:
            results = self.run_sequential(tickers_to_process)
        
        # Sumário
        self.print_summary(results)
        
        return results


# ============================================================================
# CLI
# ============================================================================

def main():
    """Entry point CLI"""
    parser = argparse.ArgumentParser(
        description="Feature Store Builder - Co-Piloto Quant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  # Processar todas as ações
  python scripts/build_feature_store.py
  
  # Processar ações específicas
  python scripts/build_feature_store.py --tickers PETR4_SA VALE3_SA
  
  # Processar com 8 workers em paralelo
  python scripts/build_feature_store.py --workers 8
  
  # Modo sequencial (debug)
  python scripts/build_feature_store.py --no-parallel
        """
    )
    
    parser.add_argument(
        '--tickers',
        nargs='+',
        help='Lista de tickers para processar (default: todos)'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=4,
        help='Número de workers paralelos (default: 4)'
    )
    
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Desabilita processamento paralelo'
    )
    
    parser.add_argument(
        '--lookback',
        type=int,
        default=252,
        help='Dias de lookback para indicadores (default: 252)'
    )
    
    args = parser.parse_args()
    
    # Setup
    logger = setup_logging()
    
    # Caminhos
    base_path = Path(__file__).parent.parent
    processed_path = base_path / "data" / "processed"
    features_path = base_path / "data" / "features"
    
    # Cria diretórios
    features_path.mkdir(parents=True, exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)
    
    # Configuração
    config = FeatureStoreConfig(
        base_path=base_path,
        processed_path=processed_path,
        features_path=features_path,
        lookback_days=args.lookback,
        parallel_workers=args.workers
    )
    
    # Pipeline
    pipeline = FeatureStorePipeline(config)
    
    try:
        results = pipeline.run(
            tickers=args.tickers,
            parallel=not args.no_parallel
        )
        
        # Exit code baseado em sucesso
        failed_count = len([r for r in results if r['status'] != 'success'])
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Pipeline interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        logger.error(f"\n💥 Erro fatal: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
