import pandas as pd
import numpy as np

def calculate_rolling_hurst(data: pd.Series, window: int = 100, kind: str = 'returns') -> pd.Series:
    """
    Calcula o Expoente de Hurst Móvel (Rolling Hurst Exponent) com opções robustas de input.

    Modos ('kind'):
    1. 'returns' (Recomendado):
       - Aplica R/S sobre Log-Retornos.
       - Z = cumsum(Y) reconstrói o perfil do preço (detrended pela média).
       - H=0.5 indica Random Walk.
       - Ideal para detectar persistência na volatilidade/direção dos incrementos.

    2. 'detrended_price' (Híbrido/Robustez):
       - Aplica R/S sobre os *Resíduos* do Log-Preço (após remover tendência linear local).
       - Remove o viés de "dupla integração" causado por tendências de alta/baixa simples.
       - Ótimo para ver se o preço oscila em torno da tendência de forma persistente ou mean-reverting.

    3. 'price' (Cuidado):
       - Aplica R/S sobre o Log-Preço bruto.
       - Tende a superestimar H (> 0.9) em tendências fortes devido à soma cumulativa sobre níveis.
       - Útil apenas para comparar regimes extremos.

    Args:
        data (pd.Series): Série temporal de preços de fechamento.
        window (int): Tamanho da janela deslizante.
        kind (str): 'returns', 'detrended_price' ou 'price'.

    Returns:
        pd.Series: Série temporal com o Hurst estimado.
    """
    
    # 1. Preparação dos Dados
    if kind == 'returns':
        # Log Returns: ln(P_t / P_{t-1})
        series = np.log(data / data.shift(1))
    elif kind in ['price', 'detrended_price']:
        # Log Prices: ln(P_t)
        # Usamos Log para estabilizar a variância através de diferentes níveis de preço
        series = np.log(data)
    else:
        raise ValueError(f"Kind '{kind}' não suportado. Use 'returns', 'price' ou 'detrended_price'.")

    # 2. Definição da Função Local (Closure para capturar 'kind')
    def get_hurst_rs(chunk):
        # Proteção estatística mínima (8 pontos é arbitrário, mas < 4 quebra o polyfit/std)
        if len(chunk) < 8:
            return np.nan
            
        X = chunk.values
        
        # --- Tratamento de Tendência (O "Pulo do Gato") ---
        if kind == 'detrended_price':
            # Regressão Linear Local: X ~ at + b
            x_axis = np.arange(len(X))
            coeffs = np.polyfit(x_axis, X, 1) # Grau 1 (Linear)
            trend = coeffs[0] * x_axis + coeffs[1]
            
            # Trabalhamos com os Resíduos (Desvios da Tendência)
            # Isso substitui o "Mean Centering" tradicional
            Y = X - trend
        else:
            # Método Clássico: Apenas centraliza na média
            mean_X = np.mean(X)
            Y = X - mean_X
        
        # --- Algoritmo R/S Clássico ---
        
        # 3. Cumulative Deviations (Z)
        # Se input=returns, Z é o "caminho do preço" (detrended).
        # Se input=residuals, Z é a "integral dos erros".
        Z = np.cumsum(Y)
        
        # 4. Range (R)
        R = np.max(Z) - np.min(Z)
        
        # 5. Desvio Padrão (S)
        # Importante: Calcular sobre a série de desvios Y, não sobre a bruta X
        S = np.std(Y, ddof=1)
        
        # Proteção matemática
        if S == 0 or R == 0:
            return 0.5
            
        # 6. Hurst Estimado
        # H = log(R/S) / log(T)
        H = np.log(R / S) / np.log(len(chunk))
        
        return H

    # 3. Aplicação Rolling
    # min_periods=window garante que só calculamos janelas completas (evita ruído inicial)
    hurst_series = series.rolling(window=window, min_periods=window).apply(get_hurst_rs, raw=False)
    
    hurst_series.name = f'Hurst_{window}_{kind}'
    return hurst_series