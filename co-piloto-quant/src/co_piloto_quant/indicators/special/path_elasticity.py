import numpy as np
import pandas as pd

def path_elasticity_index(close: pd.Series, window: int = 21) -> pd.DataFrame:
    """
    Calcula o Path Elasticity Index (PEI) e métricas estruturais associadas.

    Parâmetros
    ----------
    close : pd.Series
        Série de preços de fechamento.
    window : int
        Janela rolling.

    Retorna
    -------
    pd.DataFrame com colunas:
        - pei: Path Elasticity Index
        - max_excursion: Máxima excursão contrária
        - trend_sign: Direção predominante (+1/-1)
        - curvature: Curvatura (segunda derivada suavizada)
    """
    log_close = np.log(close + 1e-12)
    pei_list = []
    max_excursion_list = []
    curvature_list = []
    trend_sign_list = []
    for i in range(len(close)):
        if i < window:
            pei_list.append(np.nan)
            max_excursion_list.append(np.nan)
            curvature_list.append(np.nan)
            trend_sign_list.append(np.nan)
            continue
        window_slice = close.iloc[i - window + 1:i + 1]
        log_window = log_close.iloc[i - window + 1:i + 1]
        # Retorno log acumulado
        ret_acum = log_window.iloc[-1] - log_window.iloc[0]
        trend = np.sign(ret_acum)
        trend_sign_list.append(trend)
        # Máxima excursão contrária
        if trend >= 0:
            peak = window_slice.cummax()
            drawdown = (peak - window_slice) / peak
            max_excursion = drawdown.max()
        else:
            trough = window_slice.cummin()
            drawup = (window_slice - trough) / trough
            max_excursion = drawup.max()
        max_excursion_list.append(max_excursion)
        # Elasticidade (proteção: log1p para suavizar cauda)
        elasticidade = np.abs(ret_acum) / (max_excursion + 1e-12)
        elasticidade = np.log1p(elasticidade)
        pei_list.append(elasticidade)
        # Curvatura: última aceleração
        curvature = log_window.diff().diff().iloc[-1]
        curvature_list.append(curvature)
    return pd.DataFrame({
        "pei": pei_list,
        "max_excursion": max_excursion_list,
        "trend_sign": trend_sign_list,
        "curvature": curvature_list
    }, index=close.index)
