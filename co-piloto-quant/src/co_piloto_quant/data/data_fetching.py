"""
Módulo para buscar dados de mercado usando a API yfinance.
"""
import yfinance as yf
import pandas as pd
import logging
from typing import Optional
import os
import sys
from contextlib import contextmanager

# Configura um logger para este módulo
logger = logging.getLogger(__name__)

@contextmanager
def suppress_stdout_stderr():
    """A context manager that redirects stdout and stderr to devnull"""
    with open(os.devnull, 'w') as fnull:
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = fnull, fnull
        try:
            yield
        finally:
            sys.stdout, sys.stderr = old_stdout, old_stderr

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
        with suppress_stdout_stderr():
            data = yf.download(
                ticker,
                start=start,
                end=end,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,  # Preço de 'close' já ajustado (yfinance >=0.2.36)
            )

        # Garantia: se auto_adjust=True, o campo 'close' já é ajustado por splits/dividendos.
        # Se por algum motivo vier 'adjclose', priorize ele como 'close'.
        if 'adjclose' in data.columns:
            data['close'] = data['adjclose']

        # Normalização: se MultiIndex, pega apenas o nível 0 (colunas simples)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

        # Renomeia colunas para padrão minúsculo
        rename_map = {c: c.lower() for c in data.columns}
        data.rename(columns=rename_map, inplace=True)

        # Seleciona apenas as colunas OHLCV se existirem
        ohlcv = ['open', 'high', 'low', 'close', 'volume']
        cols = [c for c in ohlcv if c in data.columns]
        if cols:
            data = data[cols]

        # LOG: Mostra se o close é ajustado
        logger.info(f"[DEBUG FETCH] {ticker} campo 'close' é ajustado por splits/dividendos (auto_adjust=True). Se adjclose existir, foi priorizado.")

        # LOG DETALHADO PARA DEBUG
        logger.info(f"[DEBUG FETCH] {ticker} baixado: shape={data.shape}, columns={list(data.columns)}")
        if not data.empty:
            logger.info(f"[DEBUG FETCH] {ticker} primeiras linhas:\n{data.head(3)}")

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
