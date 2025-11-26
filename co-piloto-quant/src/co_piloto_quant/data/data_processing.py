"""
Módulo de Processamento de Dados.
Atua como uma "calculadora pura" em memória, sincronizada com a estratégia.
"""

import pandas as pd
import logging
from typing import Dict, Any, Callable

# --- IMPORTAÇÕES EXPLÍCITAS (CORREÇÃO DE BUG) ---
# Importamos diretamente de cada arquivo para garantir que o Python encontre as funções
# mesmo que elas não estejam no __init__.py
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.ifr_tpm import calculate_ifr_tpm
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Mapeamento Sincronizado com a Estratégia (analysis.py) ---
INDICATOR_MAPPING: Dict[str, Dict[str, Any]] = {
    # Bandas de Preço (Para Squeeze e Volatilidade)
    "bollinger_bands": {
        "function": bollinger_bands,
        # A estratégia pede periodo 200 e desvio 0.75 para o squeeze
        "params": {"period": 200, "std_devs": [0.75, 2.0]}
    },
    
    # Indicador de Momento (Longo Prazo)
    "ifr_tpm": {
        "function": calculate_ifr_tpm,
        "params": {"period": 120}
    },
    
    # Oscilador para Gatilhos (Stoch K 80, 3)
    "stochastic_custom": {
        "function": calculate_stochastic_custom,
        "params": {} 
    },
    
    # System TPM - Baseado em OBTR
    "system_tpm_obtr": {
        "function": calculate_system_tpm,
        "params": {"indicator": "obtr", "period": 200}
    },

    # System TPM - Baseado em WAD
    "system_tpm_wad": {
        "function": calculate_system_tpm,
        "params": {"indicator": "wad", "period": 200}
    },
    
    # Tendência Macro (WWMA 200)
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
    processed_data.dropna(inplace=True)
    
    # Calcula retorno diário (útil para métricas futuras)
    if 'close' in processed_data.columns:
        processed_data['daily_return'] = processed_data['close'].pct_change()
        processed_data.dropna(inplace=True)

    if processed_data.empty:
        return processed_data

    log_ticker = f" [{ticker}]" if ticker else ""
    logging.info(f"Processando indicadores{log_ticker}...")

    for name, config in INDICATOR_MAPPING.items():
        try:
            func: Callable = config["function"]
            params: Dict = config["params"]
            
            # Executa a função do indicador
            result = func(processed_data, **params)
            
            # Tratamento robusto do retorno (DataFrame ou Series)
            if isinstance(result, pd.DataFrame):
                # Evita duplicidade de colunas no join
                cols_to_use = result.columns.difference(processed_data.columns)
                processed_data = processed_data.join(result[cols_to_use])
            elif isinstance(result, pd.Series):
                processed_data[result.name] = result

            logging.info(f"Indicador '{name}' calculado.")

        except Exception as e:
            logging.error(f"Erro no indicador '{name}'{log_ticker}: {e}")
            continue

    return processed_data