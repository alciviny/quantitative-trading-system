import pandas as pd
import logging
from datetime import datetime, timedelta
from threading import Lock
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import hashlib

from co_piloto_quant.data.database import load_price_data, save_price_data
from co_piloto_quant.data.data_fetching import fetch_data

logger = logging.getLogger(__name__)


class DataManager:
    """
    DataManager Profissional (Infra de Dados)

    Inclui:
    - Fonte Única da Verdade (SSOT)
    - Atualização incremental
    - Cache LRU em memória
    - Invalidação inteligente de cache
    - Versionamento lógico de dataset (hash)
    - Batch multiprocessing
    """

    _locks = {}

    def __init__(
        self,
        source: str = "yahoo",
        max_age_days: int = 2,
        cache_size: int = 128,
        max_workers: int | None = None,
    ):
        self.source = source
        self.max_age = timedelta(days=max_age_days)
        self.max_workers = max_workers or max(cpu_count() - 1, 1)

        # Guarda hash do último dataset salvo por ticker
        self._dataset_hash: dict[str, str] = {}

        # Cache LRU aplicado ao core
        self._cached_get_data = lru_cache(maxsize=cache_size)(
            self._get_data_internal
        )

    # ===============================================================
    # API PÚBLICA
    # ===============================================================

    def get_data(self, ticker: str, force_update: bool = False) -> pd.DataFrame:
        """
        Único ponto de acesso aos dados.
        """
        df = self._cached_get_data(ticker, force_update)
        return df.copy()  # proteção contra mutação externa
    def _fetch_external(
        self, ticker: str, df_local: pd.DataFrame, force_update: bool = False
    ) -> pd.DataFrame:
        if force_update:
            return fetch_data(ticker, period="max")
        if df_local is not None and not df_local.empty:
            df_local = self._normalize_index(df_local)
            start_date = df_local.index.max().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            return fetch_data(ticker, start=start_date, end=end_date)
        else:
            # Se não há dados locais, buscar um período padrão
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
            return fetch_data(ticker, start=start_date, end=end_date)

    def get_data_batch(
        self, tickers: list[str], force_update: bool = False
    ) -> dict[str, pd.DataFrame]:
        """
        Busca múltiplos tickers em paralelo (multiprocessing).
        """
        results = {}

        logger.info(f"⚡ Batch fetch: {len(tickers)} ativos")

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(
                    _worker_get_data, ticker, force_update
                ): ticker
                for ticker in tickers
            }

            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    results[ticker] = future.result()
                except Exception as e:
                    logger.exception(f"❌ Erro no batch ({ticker}): {e}")
                    results[ticker] = pd.DataFrame()

        return results

    # ===============================================================
    # CORE INTERNO (CACHEADO)
    # ===============================================================

    def _get_data_internal(self, ticker: str, force_update: bool) -> pd.DataFrame:
        lock = self._get_lock(ticker)

        with lock:
            df_local = load_price_data(ticker)

            if self._needs_update(df_local, force_update):
                df_external = self._fetch_external(ticker, df_local, force_update)

                if df_external is not None and not df_external.empty:
                    df_merged = self._merge_data(df_local, df_external)
                    df_cleaned = self._clean_price_data(df_merged)
                    self.save_data(ticker, df_cleaned)
                    return df_cleaned

            if df_local is not None:
                return self._clean_price_data(df_local)

            return pd.DataFrame()

    # ===============================================================
    # PERSISTÊNCIA + VERSIONAMENTO
    # ===============================================================

    def save_data(self, ticker: str, df: pd.DataFrame):
        if df is None or df.empty:
            return

        df = self._normalize_index(df)

        dataset_hash = self._compute_hash(df)
        previous_hash = self._dataset_hash.get(ticker)

        # Evita escrita desnecessária
        if previous_hash == dataset_hash:
            logger.info(f"🟡 Dataset inalterado ({ticker})")
            return

        save_price_data(df, ticker)

        self._dataset_hash[ticker] = dataset_hash

        # Invalidação total do cache (segurança > performance)
        self._cached_get_data.cache_clear()

        logger.info(
            f"💾 Dataset salvo | {ticker} | "
            f"linhas={len(df)} | hash={dataset_hash[:10]}"
        )

    # ===============================================================
    # FETCH / UPDATE
    # ===============================================================

    def _needs_update(self, df: pd.DataFrame, force_update: bool) -> bool:
        if df is None or df.empty:
            return True

        if force_update:
            return True

        df = self._normalize_index(df)
        last_date = df.index.max()

        return datetime.now() - last_date > self.max_age

    def _fetch_external(
        self, ticker: str, df_local: pd.DataFrame, force_update: bool = False
    ) -> pd.DataFrame:
        if force_update:
            return fetch_data(ticker, period="max")
        if df_local is not None and not df_local.empty:
            df_local = self._normalize_index(df_local)
            start_date = df_local.index.max().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
            return fetch_data(ticker, start=start_date, end=end_date)
        else:
            # Se não há dados locais, buscar um período padrão
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y-%m-%d')
            return fetch_data(ticker, start=start_date, end=end_date)

    # ===============================================================
    # UTILITÁRIOS
    # ===============================================================

    @staticmethod
    def _clean_price_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Preenche dados faltantes usando apenas ffill para evitar lookahead bias.
        Garante que as colunas OHLC existam.
        """
        if df.empty:
            return df

        # Normaliza colunas (remove MultiIndex se houver)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Converte colunas para lowercase
        df.columns = [str(col).lower() for col in df.columns]

        cols = ['open', 'high', 'low', 'close', 'volume']
        # Garante que as colunas existam, preenchendo com NaN se necessário
        for col in cols:
            if col not in df.columns:
                df[col] = float('nan')
        
        # CRITICAL: Only ffill used to prevent lookahead bias
        df[cols] = df[cols].ffill()

        # Remove quaisquer linhas restantes com NaN no 'close' (geralmente no início)
        df.dropna(subset=['close'], inplace=True)

        return df

    @staticmethod
    def _merge_data(
        df_old: pd.DataFrame, df_new: pd.DataFrame
    ) -> pd.DataFrame:
        if df_old is None or df_old.empty:
            return df_new

        df_old = DataManager._normalize_index(df_old)
        df_new = DataManager._normalize_index(df_new)

        # Remove datas de df_old que já existem em df_new
        idx_new = set(df_new.index)
        df_old_valid = df_old[~df_old.index.isin(idx_new)].copy()

        # Remove linhas de df_old com OHLCV todos zero ou NaN
        ohlcv_cols = ['open', 'high', 'low', 'close', 'volume']
        if all(col in df_old_valid.columns for col in ohlcv_cols):
            mask_valid = (~df_old_valid[ohlcv_cols].isna()).all(axis=1) & (df_old_valid[ohlcv_cols] != 0).all(axis=1)
            df_old_valid = df_old_valid[mask_valid]

        df = pd.concat([df_old_valid, df_new])
        df = df[~df.index.duplicated(keep="last")]
        return df.sort_index()

    @staticmethod
    def _normalize_index(df: pd.DataFrame) -> pd.DataFrame:
        if not isinstance(df.index, pd.DatetimeIndex):
            for col in ("Date", "datetime", "time"):
                if col in df.columns:
                    df = df.set_index(col)
                    break

        df.index = pd.to_datetime(df.index)
        return df.sort_index()

    @staticmethod
    def _compute_hash(df: pd.DataFrame) -> str:
        """
        Hash determinístico do conteúdo do dataset.
        """
        data_bytes = df.to_csv().encode()
        return hashlib.sha256(data_bytes).hexdigest()

    @classmethod
    def _get_lock(cls, ticker: str) -> Lock:
        if ticker not in cls._locks:
            cls._locks[ticker] = Lock()
        return cls._locks[ticker]


# ===============================================================
# WORKER PARA MULTIPROCESSING
# ===============================================================

def _worker_get_data(ticker: str, force_update: bool):
    dm = DataManager()
    return dm.get_data(ticker, force_update=force_update)


# Singleton
data_manager = DataManager()
