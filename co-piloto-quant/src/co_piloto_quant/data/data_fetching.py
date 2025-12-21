"""
Módulo para buscar dados de mercado usando a API yfinance.
"""
import yfinance as yf
import pandas as pd
import logging
from typing import Optional

# Configura um logger para este módulo
logger = logging.getLogger(__name__)

def fetch_data(
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "max",
    interval: str = "1d",
) -> pd.DataFrame:
    """
    Busca dados históricos de um único ativo de forma robusta.

    Args:
        ticker: O símbolo do ativo (ex: "PETR4.SA").
        start: Data de início (formato 'YYYY-MM-DD').
        end: Data de fim (formato 'YYYY-MM-DD').
        period: Período a ser baixado (ex: "1y", "max"). Ignorado se start/end for fornecido.
        interval: Frequência dos dados (ex: "1d", "1h").

    Returns:
        Um DataFrame do pandas com os dados OHLCV ou um DataFrame vazio em caso de falha.
    """
    try:
        logger.debug(f"Iniciando download para {ticker}...")
        
        # yfinance lida com a priorização de start/end sobre period
        data = yf.download(
            ticker,
            start=start,
            end=end,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,  # Geralmente recomendado para obter preços ajustados
        )

        if data.empty:
            logger.warning(f"Nenhum dado retornado para {ticker} no período solicitado.")
            return pd.DataFrame()

        logger.debug(f"Download para {ticker} concluído. {len(data)} registros encontrados.")
        return data

    except Exception as e:
        # Captura exceções comuns do yfinance (YFTzMissingError, HTTPError, etc.)
        # e outras exceções inesperadas.
        logger.error(f"Falha ao baixar dados para {ticker}. Razão: {e}")
        return pd.DataFrame()
