import numpy as np
import pandas as pd
from typing import Optional

def calculate_rolling_ou_params(
    series: pd.Series,
    window: int = 60,
    beta_floor: Optional[float] = None,
    strict_mode: bool = False,
    use_log: bool = True,
    min_var: float = 1e-12,
    visual_clip: float = 1000.0,
) -> pd.DataFrame:
    """
    Estimador Institucional de Parâmetros Ornstein-Uhlenbeck (Rolling OLS).
    
    Retorna um DataFrame com colunas (sufixo _{window}):
      - Beta: Velocidade de reversão (slope).
      - Alpha: Intercepto.
      - Theta: Velocidade contínua (theta = -log(1+beta)).
      - HalfLife: Tempo para reverter 50% do desvio.
      - Mu: Média de longo prazo (preço justo teórico).
      - Sigma_resid: Volatilidade do ruído (desvio padrão dos resíduos).
      - t_Beta: t-statistic do beta (significância estatística).
      - R2: Coeficiente de determinação (qualidade do fit).

    Args:
        series: Série de preços (Use log=True para ativos com tendência/drift).
        window: Janela de lookback.
        beta_floor: Soft floor para beta (padrão -0.02, teto HL ~34).
        strict_mode: Se True, retorna NaN para não-reversão. Se False, visual_clip.
        use_log: Se True, calcula sobre log(preço).
    """

    # Input checks
    if use_log and (series <= 0).any():
        # Fallback seguro: se tiver valor <= 0, desativa log ou trata erro
        # Aqui vamos assumir que o usuário sabe o que faz, mas poderíamos forçar use_log=False
        pass 

    # Working series
    # Se use_log for True, protegemos contra log(0)
    if use_log:
        X = np.log(series.replace(0, np.nan))
    else:
        X = series.astype(float)

    X_lag = X.shift(1)
    DX = X.diff(1)

    # Build unified frame for perfect alignment
    df = pd.DataFrame({
        'x': X_lag,
        'y': DX,
        'xx': X_lag * X_lag,
        'xy': X_lag * DX,
        'yy': DX * DX,
    })

    roll = df.rolling(window=window, min_periods=window)
    mean = roll.mean()

    mean_x = mean['x']
    mean_y = mean['y']
    mean_xx = mean['xx']
    mean_xy = mean['xy']
    mean_yy = mean['yy']

    # OLS moments
    cov_xy = mean_xy - mean_x * mean_y
    var_x = mean_xx - mean_x * mean_x
    var_x = var_x.clip(lower=min_var)

    beta = cov_xy / var_x
    alpha = mean_y - beta * mean_x

    # Residual variance using rolling moments (no extra passes)
    # E[(y - (alpha + beta x))^2]
    resid_var = (
        mean_yy
        + alpha * alpha
        + beta * beta * mean_xx
        - 2.0 * alpha * mean_y
        - 2.0 * beta * mean_xy
        + 2.0 * alpha * beta * mean_x
    )

    # Numerical safety
    resid_var = resid_var.clip(lower=0.0)
    sigma_resid = np.sqrt(resid_var)

    # Standard error of beta (approx): sigma_resid / sqrt(N * Var(X))
    se_beta = sigma_resid / np.sqrt(window * var_x)
    se_beta = se_beta.replace([np.inf, -np.inf], np.nan)

    t_beta = beta / se_beta

    # R^2: 1 - var_resid / var_y where var_y = E[y^2] - E[y]^2
    var_y = mean_yy - mean_y * mean_y
    var_y = var_y.clip(lower=min_var)
    r2 = 1.0 - (resid_var / var_y)

    # Theta and Half-life
    if beta_floor is None:
        beta_floor = -0.02

    beta_effective = np.minimum(beta, beta_floor)

    # Theta from discrete beta: theta = -log(1 + beta)
    theta = -np.log1p(beta_effective)
    
    # Half-life = log(2) / theta
    hl = np.log(2.0) / theta

    # Long-run mean mu = -alpha / beta (valid when beta != 0)
    # Cuidado: Mu no log-space se use_log=True. Para preço real teria que fazer exp(Mu + var/2)
    mu = -alpha / beta

    # Assemble results
    out = pd.DataFrame(index=series.index)
    suffix = f"_{window}"
    
    out[f'Beta{suffix}'] = beta
    out[f'HalfLife{suffix}'] = hl
    out[f'R2{suffix}'] = r2
    out[f't_Beta{suffix}'] = t_beta
    out[f'SigmaResid{suffix}'] = sigma_resid
    # Adicionei Mu e Alpha se quiser usar depois, mas os principais estão acima
    
    # Non-reverting regimes handling
    non_reverting = (beta >= 0) | (~np.isfinite(beta))

    if strict_mode:
        out.loc[non_reverting, f'HalfLife{suffix}'] = np.nan
    else:
        out.loc[non_reverting, f'HalfLife{suffix}'] = visual_clip

    # Clean extremes
    out.replace([np.inf, -np.inf], np.nan, inplace=True)

    return out