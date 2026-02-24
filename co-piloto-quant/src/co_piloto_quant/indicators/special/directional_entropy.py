import numpy as np
import pandas as pd

def _shannon_entropy_binary(p: float) -> float:
    """
    Entropia de Shannon para variável binária.
    Normalizada entre 0 e 1.
    """
    if p <= 0 or p >= 1:
        return 0.0
    entropy = -(p * np.log(p) + (1 - p) * np.log(1 - p))
    return entropy / np.log(2)  # normalização

def directional_entropy(close: pd.Series, window: int = 21) -> pd.DataFrame:
    """
    Calcula métricas de Entropia Direcional e APD.

    Parâmetros
    ----------
    close : pd.Series
        Série de preços de fechamento.
    window : int
        Janela rolling.

    Retorna
    -------
    pd.DataFrame com colunas:
        - dir_entropy
        - sign_change_rate
        - directional_coherence
        - apd_score
    """

    returns = close.pct_change()

    # Sinal direcional binário
    sign = (returns > 0).astype(int)

    # =========================
    # 1. Entropia Direcional
    # =========================
    entropy_list = []

    for i in range(len(sign)):
        if i < window:
            entropy_list.append(np.nan)
            continue

        window_slice = sign.iloc[i - window:i]
        p = window_slice.mean()
        entropy_list.append(_shannon_entropy_binary(p))

    dir_entropy = pd.Series(entropy_list, index=close.index)

    # =========================
    # 2. Sign Change Rate
    # =========================
    sign_changes = sign.diff().abs()
    sign_change_rate = (
        sign_changes.rolling(window).sum() / (window - 1)
    )

    # =========================
    # 3. Directional Coherence
    # =========================
    abs_returns = returns.abs()

    cumulative_return = returns.rolling(window).sum()
    sum_abs_returns = abs_returns.rolling(window).sum()

    directional_coherence = (
        cumulative_return.abs() / (sum_abs_returns + 1e-12)
    )

    # =========================
    # 4. APD Score
    # =========================
    apd_score = (
        directional_coherence
        * (1 - dir_entropy)
        * (1 - sign_change_rate)
    )

    return pd.DataFrame({
        "dir_entropy": dir_entropy,
        "sign_change_rate": sign_change_rate,
        "directional_coherence": directional_coherence,
        "apd_score": apd_score
    })
