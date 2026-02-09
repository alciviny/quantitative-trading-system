"""
API FastAPI Otimizada - Co-Piloto Quant
Lê dados direto dos arquivos Parquet + CSVs existentes

Instale: pip install fastapi uvicorn pyarrow

Execute: python api_backend.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from pathlib import Path
from typing import List, Optional
import logging

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CopiloAPI")

app = FastAPI(title="Co-Piloto Quant API", version="2.0")

# CORS para aceitar requisições do React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== CAMINHOS DOS DADOS ==========
BASE_PATH = Path(__file__).parent / "co-piloto-quant"
PARQUET_PATH = BASE_PATH / "data" / "processed"
FEATURES_PATH = BASE_PATH / "data" / "features"  # Feature Store
RESULTS_PATH = BASE_PATH / "data" / "results"

# Cache simples em memória
_cache = {}

# Flag para indicar se Feature Store está disponível
FEATURE_STORE_ENABLED = FEATURES_PATH.exists()


def get_available_tickers() -> List[str]:
    """Busca automaticamente todas as ações dos arquivos parquet"""
    if "tickers" in _cache:
        return _cache["tickers"]
    
    # Prioriza features se disponível, senão usa processed
    if FEATURE_STORE_ENABLED:
        feature_files = list(FEATURES_PATH.glob("*_enriched.parquet"))
        if feature_files:
            tickers = [f.stem.replace("_enriched", "") for f in feature_files]
            _cache["tickers"] = sorted(tickers)
            logger.info(f"✅ {len(tickers)} ações encontradas em Feature Store")
            return tickers
    
    # Fallback para processed
    parquet_files = list(PARQUET_PATH.glob("*_SA.parquet"))
    tickers = [f.stem for f in parquet_files]
    _cache["tickers"] = sorted(tickers)
    logger.info(f"✅ {len(tickers)} ações encontradas em {PARQUET_PATH}")
    return tickers


def load_stock_data(ticker: str, use_features: bool = True) -> Optional[pd.DataFrame]:
    """Carrega dados de um ticker com fallback automático
    
    Args:
        ticker: Código do ticker (ex: PETR4_SA)
        use_features: Se True, tenta carregar de features/ primeiro
    
    Returns:
        DataFrame com os dados ou None se não encontrar
    """
    # 1. Tenta carregar do Feature Store (dados enriquecidos)
    if use_features and FEATURE_STORE_ENABLED:
        feature_file = FEATURES_PATH / f"{ticker}_enriched.parquet"
        if feature_file.exists():
            try:
                df = pd.read_parquet(feature_file)
                logger.debug(f"✅ {ticker}: Carregado do Feature Store ({len(df)} linhas, {len(df.columns)} features)")
                return df
            except Exception as e:
                logger.warning(f"⚠️  {ticker}: Erro ao ler Feature Store, usando fallback - {e}")
    
    # 2. Fallback: Carrega dados processados (sem features avançadas)
    processed_file = PARQUET_PATH / f"{ticker}.parquet"
    if processed_file.exists():
        try:
            df = pd.read_parquet(processed_file)
            logger.debug(f"✅ {ticker}: Carregado de processed/ ({len(df)} linhas)")
            return df
        except Exception as e:
            logger.error(f"❌ {ticker}: Erro ao ler arquivo - {e}")
            return None
    
    logger.warning(f"❌ {ticker}: Arquivo não encontrado")
    return None


# ========== ENDPOINTS ==========

@app.get("/api/health")
async def health_check():
    """Verificação de saúde da API"""
    
    # Verifica quantos features enriched existem
    feature_count = len(list(FEATURES_PATH.glob("*_enriched.parquet"))) if FEATURES_PATH.exists() else 0
    
    return {
        "status": "ok",
        "service": "Co-Piloto Quant API",
        "version": "3.0",
        "feature_store": {
            "enabled": FEATURE_STORE_ENABLED,
            "path": str(FEATURES_PATH),
            "enriched_files": feature_count
        },
        "data_sources": {
            "features": str(FEATURES_PATH),
            "processed": str(PARQUET_PATH),
            "results": str(RESULTS_PATH)
        }
    }


@app.get("/api/stocks")
async def get_stocks() -> List[str]:
    """Retorna lista de ações disponíveis"""
    try:
        tickers = get_available_tickers()
        return tickers
    except Exception as e:
        logger.error(f"Erro ao listar ações: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock}/price-history")
async def get_price_history(stock: str, days: int = 365):
    """
    Retorna histórico de preços (usa Feature Store se disponível)
    """
    try:
        # Usa função helper com fallback automático
        df = load_stock_data(stock, use_features=True)
        
        if df is None:
            raise HTTPException(status_code=404, detail=f"Ação {stock} não encontrada")
        
        # Pega últimos N dias
        df = df.tail(days)
        
        # Prepara dados para o frontend
        data = []
        for idx, row in df.iterrows():
            data.append({
                'date': str(idx) if isinstance(idx, pd.Timestamp) else str(row.get('date', idx)),
                'open': float(row.get('open', 0)),
                'high': float(row.get('high', 0)),
                'low': float(row.get('low', 0)),
                'close': float(row.get('close', 0)),
                'volume': int(row.get('volume', 0))
            })
        
        logger.info(f"✅ {stock}: {len(data)} registros de preço")
        return data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar histórico de {stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock}/metrics")
async def get_stock_metrics(stock: str, horizon: str = "5d"):
    """
    Retorna métricas de um ativo por horizonte
    Horizontes: 5d, 10d, 20d, 40d
    """
    try:
        filename = f"{stock}_metrics_{horizon}.csv"
        filepath = RESULTS_PATH / filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Métricas não encontradas: {filename}")
        
        df = pd.read_csv(filepath)
        logger.info(f"✅ {stock}: Métricas {horizon} carregadas")
        return df.to_dict(orient='records')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar métricas de {stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock}/vwap")
async def get_vwap_data(stock: str, period: str = "global"):
    """
    Retorna dados VWAP de um ativo
    Períodos: global, yearly
    """
    try:
        filename = f"{stock}_vwap_lab_{period}.csv"
        filepath = RESULTS_PATH / filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"VWAP não encontrado: {filename}")
        
        df = pd.read_csv(filepath)
        logger.info(f"✅ {stock}: VWAP {period} carregado")
        return df.to_dict(orient='records')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar VWAP de {stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock}/returns")
async def get_forward_returns(stock: str, horizon: str = "5d"):
    """
    Retorna retornos futuros de um ativo
    Horizontes: 5d, 10d, 20d, 40d
    """
    try:
        filename = f"{stock}_fwd_ret_{horizon}.csv"
        filepath = RESULTS_PATH / filename
        
        if not filepath.exists():
            raise HTTPException(status_code=404, detail=f"Retornos não encontrados: {filename}")
        
        df = pd.read_csv(filepath)
        logger.info(f"✅ {stock}: Retornos {horizon} carregados")
        return df.to_dict(orient='records')
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar retornos de {stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stocks/{stock}/indicators")
async def get_technical_indicators(stock: str, days: int = 90):
    """
    Retorna indicadores técnicos (Feature Store com todos os indicadores avançados)
    Inclui: Hurst, Entropy, Half-Life, Fractal Dimension, Lempel-Ziv, etc.
    """
    try:
        # Prioriza Feature Store para ter indicadores completos
        df = load_stock_data(stock, use_features=True)
        
        if df is None:
            raise HTTPException(status_code=404, detail=f"Ação {stock} não encontrada")
        
        # Pega últimos N dias
        df = df.tail(days)
        
        # Lista de indicadores técnicos disponíveis
        indicator_columns = []
        all_columns = df.columns.tolist()
        
        # Indicadores do Feature Store (complexos)
        advanced_indicators = [
            'hurst_exponent', 'market_entropy', 'fractal_dimension',
            'lempel_ziv', 'half_life', 'mean_reversion_speed', 'frac_diff',
            'regime_trend', 'regime_volatility', 'regime_efficiency'
        ]
        
        # Indicadores básicos
        basic_indicators = [
            'returns', 'log_returns', 'volatility', 'atr', 'roc',
            'sma', 'ema', 'rsi', 'bollinger', 'volume_ratio'
        ]
        
        # Combina todos os padrões
        all_indicator_patterns = advanced_indicators + basic_indicators
        
        # Filtra colunas que existem (ignora OHLCV básico)
        basic_cols = {'open', 'high', 'low', 'close', 'volume', 'date', 'timestamp'}
        for col in all_columns:
            if col.lower() in basic_cols:
                continue
            col_lower = col.lower()
            if any(ind.lower() in col_lower for ind in all_indicator_patterns):
                indicator_columns.append(col)
        
        if not indicator_columns:
            return {
                "message": "Nenhum indicador técnico encontrado no arquivo",
                "available_columns": all_columns[:20]  # Mostra primeiras 20 colunas
            }
        
        # Prepara dados para o frontend
        data = []
        for idx, row in df.iterrows():
            record = {
                'date': str(idx) if isinstance(idx, pd.Timestamp) else str(row.get('date', idx)),
                'close': float(row.get('close', 0))
            }
            
            # Adiciona todos os indicadores encontrados
            for col in indicator_columns:
                value = row.get(col)
                if pd.notna(value):
                    # Se é numérico, converte para float; senão mantém como string
                    try:
                        record[col] = float(value)
                    except (ValueError, TypeError):
                        record[col] = str(value)
            
            data.append(record)
        
        logger.info(f"✅ {stock}: {len(indicator_columns)} indicadores, {len(data)} registros")
        
        return {
            "data": data,
            "indicators": indicator_columns,
            "count": len(data)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar indicadores de {stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_global_stats(horizon: str = "5d"):
    """Retorna estatísticas globais"""
    try:
        filename = f"global_stats_fwd_ret_{horizon}.csv"
        filepath = RESULTS_PATH / filename
        
        if filepath.exists():
            df = pd.read_csv(filepath)
            logger.info(f"✅ Estatísticas globais {horizon} carregadas")
            return df.to_dict(orient='records')
        
        raise HTTPException(status_code=404, detail="Estatísticas globais não encontradas")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar estatísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== ENDPOINTS ADICIONAIS ==========

@app.get("/api/assets")
async def get_assets():
    """Retorna lista de ativos disponíveis com métricas"""
    try:
        tickers = get_available_tickers()[:20]  # Limita a 20 para performance
        assets = []
        
        for ticker in tickers:
            try:
                parquet_file = PARQUET_PATH / f"{ticker}.parquet"
                if not parquet_file.exists():
                    continue
                    
                df = pd.read_parquet(parquet_file)
                if df.empty:
                    continue
                
                # Pega última linha
                latest = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else latest
                
                # Calcula variação percentual
                close = float(latest.get('close', 0))
                prev_close = float(prev.get('close', close))
                change_pct = ((close - prev_close) / prev_close * 100) if prev_close > 0 else 0
                
                asset = {
                    "ticker": ticker,
                    "name": ticker,
                    "price": close,
                    "change_pct": change_pct,
                    "volume": float(latest.get('volume', 0)),
                    "hurst": float(latest.get('hurst_val', 0.5)),
                    "fractal_dim": float(latest.get('close_frac', 1.5)),
                    "entropy": float(latest.get('entropy_val', 0.5)),
                    "half_life": float(latest.get('half_life', 10.0)),
                    "rsi": float(latest.get('rsi_14', 50.0)),
                    "strategy_status": "NEUTRAL",  # TODO: calcular baseado em indicadores
                    "regime": "LATERAL",
                    "ml_probability": 50.0,
                    "last_signal": pd.Timestamp.now().isoformat()
                }
                
                # Determina status da estratégia baseado em RSI
                rsi = asset["rsi"]
                if rsi < 30:
                    asset["strategy_status"] = "BUY"
                    asset["ml_probability"] = 70.0
                elif rsi > 70:
                    asset["strategy_status"] = "SELL"
                    asset["ml_probability"] = 65.0
                
                assets.append(asset)
            except Exception as e:
                logger.warning(f"Erro ao processar {ticker}: {e}")
                continue
        
        logger.info(f"✅ {len(assets)} ativos retornados")
        return assets
    except Exception as e:
        logger.error(f"Erro ao listar ativos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/assets/{asset_id}/ohlcv")
async def get_asset_ohlcv(asset_id: str, days: int = 365):
    """Retorna dados OHLCV (Open, High, Low, Close, Volume) do ativo"""
    try:
        # Carrega dados (features ou processed)
        df = load_stock_data(asset_id, use_features=True)
        
        if df is None:
            raise HTTPException(status_code=404, detail=f"Ativo {asset_id} não encontrado")
        df = df.tail(days)
        
        # Coluna de data (se existir)
        if 'data_pregao' in df.columns:
            df['date'] = df['data_pregao']
        elif 'Date' in df.columns:
            df['date'] = df['Date']
        elif df.index.name == 'Date':
            df['date'] = df.index
        else:
            df['date'] = df.index
        
        # Formata resposta
        data = []
        for idx, row in df.iterrows():
            record = {
                'date': str(row.get('date', idx)),
                'open': float(row['open']) if 'open' in row and pd.notna(row['open']) else None,
                'high': float(row['high']) if 'high' in row and pd.notna(row['high']) else None,
                'low': float(row['low']) if 'low' in row and pd.notna(row['low']) else None,
                'close': float(row['close']) if 'close' in row and pd.notna(row['close']) else None,
                'volume': float(row['volume']) if 'volume' in row and pd.notna(row['volume']) else None,
            }
            data.append(record)
        
        return {
            "asset_id": asset_id,
            "data": data,
            "count": len(data)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar OHLCV de {asset_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/correlation")
async def get_market_correlation():
    """Retorna matriz de correlação do mercado"""
    try:
        logger.info(f"Buscando correlação em: {RESULTS_PATH}")
        
        # Tenta carregar arquivo de correlação dos resultados
        correlation_files = list(RESULTS_PATH.glob("*correlation*.csv"))
        logger.info(f"Arquivos de correlação encontrados: {len(correlation_files)}")
        
        if correlation_files:
            df = pd.read_csv(correlation_files[0], index_col=0)
            logger.info("✅ Matriz de correlação carregada do arquivo")
            return {
                "tickers": df.index.tolist(),
                "matrix": df.values.tolist()
            }
        
        # Se não encontrar arquivo, tenta calcular a partir dos dados
        logger.info("Calculando correlação a partir dos dados...")
        tickers = get_available_tickers()[:10]  # Limita a 10 ativos para performance
        logger.info(f"Tickers para correlação: {tickers}")
        
        price_data = {}
        for ticker in tickers:
            try:
                parquet_file = PARQUET_PATH / f"{ticker}.parquet"
                logger.info(f"Tentando ler: {parquet_file}, existe={parquet_file.exists()}")
                
                if parquet_file.exists():
                    df = pd.read_parquet(parquet_file)
                    logger.info(f"{ticker}: {len(df)} linhas, colunas={list(df.columns)}")
                    
                    if 'close' in df.columns and len(df) > 0:
                        prices = df['close'].tail(252).dropna()
                        if len(prices) > 10:  # Precisa ter pelo menos 10 pontos
                            price_data[ticker] = prices
                            logger.info(f"{ticker}: {len(prices)} preços válidos")
                        else:
                            logger.warning(f"{ticker}: poucos dados ({len(prices)} pontos)")
            except Exception as e:
                logger.warning(f"Erro ao ler {ticker}: {e}")
        
        logger.info(f"Total de ativos com dados: {len(price_data)}")
        
        if len(price_data) >= 2:  # Precisa de pelo menos 2 ativos
            prices_df = pd.DataFrame(price_data)
            correlation = prices_df.corr().fillna(0)
            logger.info(f"✅ Correlação calculada para {len(price_data)} ativos")
            return {
                "tickers": correlation.index.tolist(),
                "matrix": correlation.values.tolist()
            }
        
        # Se não conseguiu calcular, retorna dados mock
        logger.warning("Retornando correlação mock (dados insuficientes)")
        mock_tickers = tickers[:5] if tickers else ['PETR4_SA', 'VALE3_SA', 'ITUB4_SA', 'BBDC4_SA', 'ABEV3_SA']
        import numpy as np
        n = len(mock_tickers)
        # Cria correlação mock com valores realistas
        mock_corr = np.eye(n)  # Diagonal = 1
        for i in range(n):
            for j in range(i+1, n):
                val = np.random.uniform(0.2, 0.7)  # Correlação moderada
                mock_corr[i,j] = val
                mock_corr[j,i] = val
        
        return {
            "tickers": mock_tickers,
            "matrix": mock_corr.tolist()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao carregar correlação: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market/regime")
async def get_market_regime():
    """Retorna regime de mercado"""
    try:
        # Tenta carregar arquivo de regime dos resultados
        regime_files = list(RESULTS_PATH.glob("*regime*.csv"))
        
        if regime_files:
            df = pd.read_csv(regime_files[0])
            logger.info("✅ Regime de mercado carregado do arquivo")
            # Se tiver coluna 'regime', usa ela, senão cria um padrão
            if not df.empty and 'regime' in df.columns:
                latest = df.iloc[-1]
                return {
                    "regime": str(latest.get('regime', 'LATERAL')).upper(),
                    "confidence": float(latest.get('confidence', 50.0)),
                    "volatility": float(latest.get('volatility', 15.0)),
                    "trend_strength": float(latest.get('trend_strength', 0.5)),
                    "hurst_avg": float(latest.get('hurst_avg', 0.5)),
                    "updated_at": pd.Timestamp.now().isoformat()
                }
        
        # Retorna regime padrão se não encontrar arquivo
        logger.info("⚠️ Arquivo de regime não encontrado, retornando dados padrão")
        return {
            "regime": "LATERAL",
            "confidence": 60.0,
            "volatility": 18.5,
            "trend_strength": 0.45,
            "hurst_avg": 0.52,
            "updated_at": pd.Timestamp.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Erro ao carregar regime: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== INICIALIZAÇÃO ==========

if __name__ == "__main__":
    import uvicorn
    
    # Verifica se os diretórios existem
    if not PARQUET_PATH.exists():
        logger.error(f"❌ Diretório não encontrado: {PARQUET_PATH}")
        logger.error("Execute primeiro: python co-piloto-quant/scripts/update_market_data.py")
    
    if not RESULTS_PATH.exists():
        logger.warning(f"⚠️ Diretório de resultados não encontrado: {RESULTS_PATH}")
    
    logger.info("=" * 60)
    logger.info("🚀 Co-Piloto Quant API v2.0")
    logger.info("=" * 60)
    logger.info(f"📦 Parquet: {PARQUET_PATH}")
    logger.info(f"📊 Results: {RESULTS_PATH}")
    logger.info(f"🌐 URL: http://localhost:8001")
    logger.info(f"📖 Docs: http://localhost:8001/docs")
    logger.info("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001, log_level="info")
