"""
Módulo de Processamento de Dados.
Atua como uma "calculadora pura" em memória, sincronizada com a estratégia.
"""

import pandas as pd
import logging
from typing import Dict, Any, Callable

# --- IMPORTAÇÕES DOS INDICADORES ---
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average

# Importa as configurações para garantir consistência
from co_piloto_quant.config import (
    BB_PERIOD, 
    PRICE_BB_DEVIATIONS, 
    IFR_PERIOD,
    SYSTEM_PERIOD
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Mapeamento Sincronizado com a Estratégia ---
INDICATOR_MAPPING: Dict[str, Dict[str, Any]] = {
    "bollinger_bands": {
        "function": bollinger_bands,
        "params": {
            "period": BB_PERIOD, 
            "std_devs": PRICE_BB_DEVIATIONS 
        }
    },
    "ifr_tpm": {
        "function": calculate_ifr_tpm,
        "params": {"period": IFR_PERIOD}
    },
    "stochastic_custom": {
        "function": calculate_stochastic_custom,
        "params": {} 
    },
    "system_tpm_obtr": {
        "function": calculate_system_tpm,
        "params": {"indicator": "obtr", "period": SYSTEM_PERIOD}
    },
    "system_tpm_wad": {
        "function": calculate_system_tpm,
        "params": {"indicator": "wad", "period": SYSTEM_PERIOD}
    },
    "ww_moving_average": {
        "function": ww_moving_average,
        "params": {"period": 200}
    },
}

def process_data(data: pd.DataFrame, ticker: str = None) -> pd.DataFrame:
    """Aplica indicadores técnicos ao DataFrame em memória."""
    if not isinstance(data.index, pd.DatetimeIndex):
        raise ValueError("O índice do DataFrame deve ser DatetimeIndex.")

    if data.empty:
        logging.warning(f"DataFrame vazio para '{ticker}'.")
        return data

    processed_data = data.copy()
    processed_data.columns = processed_data.columns.str.lower()
    
    # --- LIMPEZA CRÍTICA (CORREÇÃO DA ESTICADA) ---
    # 1. Remove NaNs iniciais
    processed_data.dropna(inplace=True)
    
    # 2. Remove preços zerados ou negativos (Bug comum do yfinance no último candle)
    # Isso evita que o gráfico desenhe uma linha até o zero.
    cols_to_check = ['open', 'high', 'low', 'close']
    for col in cols_to_check:
        if col in processed_data.columns:
            processed_data = processed_data[processed_data[col] > 0]
            
    # ---------------------------------------------
    
    # Calcula retorno diário
    if 'close' in processed_data.columns:
        processed_data['daily_return'] = processed_data['close'].pct_change()
        # Remove a primeira linha que fica NaN após o cálculo do retorno
        processed_data.dropna(subset=['daily_return'], inplace=True)

    if processed_data.empty:
        return processed_data

    log_ticker = f" [{ticker}]" if ticker else ""
    logging.info(f"Processando indicadores{log_ticker}...")

    for name, config in INDICATOR_MAPPING.items():
        try:
            func: Callable = config["function"]
            params: Dict = config["params"]
            
            result = func(processed_data, **params)
            
            if isinstance(result, pd.DataFrame):
                cols_to_use = result.columns.difference(processed_data.columns)
                processed_data = processed_data.join(result[cols_to_use])
            elif isinstance(result, pd.Series):
                processed_data[result.name] = result

            logging.info(f"Indicador '{name}' calculado.")

        except Exception as e:
            logging.error(f"Erro no indicador '{name}'{log_ticker}: {e}")
            continue

    # Limpeza Final: Remove linhas que ficaram com NaN por causa do período dos indicadores
    # (Ex: As primeiras 200 linhas costumam ficar vazias por causa da Média Móvel 200)
    processed_data.dropna(inplace=True)

    return processed_data