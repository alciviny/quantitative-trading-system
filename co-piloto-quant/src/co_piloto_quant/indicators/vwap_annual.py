import pandas as pd
import numpy as np

class AnnualVWAPAnalyst:
    """
    Calcula VWAP anual ancorada e métricas contínuas de fluxo.
    Versão Robusta: Normaliza nomes de colunas automaticamente.
    """

    def __init__(self, price_col: str = "Close"):
        # O padrão interno será sempre Capitalizado
        self.price_col = price_col.capitalize() 

    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Padroniza colunas para o formato esperado (Capitalized),
        independente se vierem como 'time', 'DATE', 'close', etc.
        """
        df = df.copy()
        
        # Mapa de renomeação (de variações comuns para o padrão)
        rename_map = {
        # Data / Tempo (PT + EN)
        'time': 'Date',
        'date': 'Date',
        'datetime': 'Date',
        'timestamp': 'Date',
        'data': 'Date',
        'data_pregao': 'Date',
        'dt_pregao': 'Date',
        'pregao': 'Date',

        # OHLCV
        'open': 'Open',
        'high': 'High',
        'low': 'Low',
        'close': 'Close',
        'volume': 'Volume',
        'vol': 'Volume',
        'tick_volume': 'Volume',
        'real_volume': 'Volume'
    }

        
        # Renomeia colunas existentes (ignora case se possível, mas o map cobre lowercase)
        current_cols = {c.lower(): c for c in df.columns}
        
        new_names = {}
        for expected_lower, target_name in rename_map.items():
            if expected_lower in current_cols:
                original_name = current_cols[expected_lower]
                new_names[original_name] = target_name
                
        if new_names:
            df.rename(columns=new_names, inplace=True)
            
        return df

    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        required_cols = {"Date", "High", "Low", "Close", "Volume"}
        missing = required_cols - set(df.columns)
        if missing:
            # Mostra as colunas que TEM para ajudar no debug
            raise ValueError(
                f"Colunas obrigatórias faltando: {missing}. "
                f"Colunas encontradas: {list(df.columns)}"
            )

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        # 1. Normaliza nomes das colunas (blindagem)
        df = self._normalize_columns(df)
        
        # 2. Valida
        self._validate_dataframe(df)

        # 3. Garante datetime
        if not pd.api.types.is_datetime64_any_dtype(df["Date"]):
            df["Date"] = pd.to_datetime(df["Date"])
            
        df = df.sort_values("Date").reset_index(drop=True)

        # Ano de ancoragem
        df["anchor_year"] = df["Date"].dt.year

        # Preço típico (H+L+C)/3
        df["typical_price"] = (df["High"] + df["Low"] + df["Close"]) / 3.0
        
        # Proteção Volume Zero
        df["Volume"] = df["Volume"].clip(lower=1)

        # --- CÁLCULO VETORIZADO ---
        grouped = df.groupby("anchor_year", sort=False)
        
        # VWAP
        df["tp_x_vol"] = df["typical_price"] * df["Volume"]
        df["cum_tp_x_vol"] = grouped["tp_x_vol"].cumsum()
        df["cum_vol"] = grouped["Volume"].cumsum()
        
        df["vwap_annual"] = df["cum_tp_x_vol"] / df["cum_vol"]

        # Métrica 1: Distância Econômica (%)
        # Usa self.price_col (que já garantimos ser 'Close' capitalizado)
        df["vwap_dist_pct"] = (df[self.price_col] - df["vwap_annual"]) / df["vwap_annual"]

        # Métrica 2: Z-Score (Stress)
        df["price_sq_x_vol"] = (df["typical_price"] ** 2) * df["Volume"]
        df["cum_price_sq_x_vol"] = grouped["price_sq_x_vol"].cumsum()
        
        # Variância = E[X^2] - (E[X])^2
        df["vwap_variance"] = (df["cum_price_sq_x_vol"] / df["cum_vol"]) - (df["vwap_annual"] ** 2)
        df["vwap_variance"] = df["vwap_variance"].clip(lower=0)
        df["vwap_std"] = np.sqrt(df["vwap_variance"])

        df["vwap_z_score"] = np.where(
            df["vwap_std"] > 0,
            (df[self.price_col] - df["vwap_annual"]) / df["vwap_std"],
            0.0
        )

        # Limpeza
        drop_cols = ["tp_x_vol", "cum_tp_x_vol", "cum_vol", "price_sq_x_vol", 
                     "cum_price_sq_x_vol", "vwap_variance", "vwap_std", "typical_price", "anchor_year"]
        # Só dropa o que existe (para evitar erro se rodar 2x)
        cols_to_drop = [c for c in drop_cols if c in df.columns]
        df.drop(columns=cols_to_drop, inplace=True)

        return df