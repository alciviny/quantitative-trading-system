import numpy as np
import pandas as pd

def calculate_rolling_hurst(data: pd.Series, window: int = 100, kind: str = 'returns', min_lag: int = 8) -> pd.Series:
    """
    Calcula o Expoente de Hurst Móvel usando o método da inclinação Log-Log (R/S Analysis).
    
    Esta implementação é mais robusta que a estimativa de ponto único, pois calcula o R/S 
    em múltiplas escalas de tempo dentro da janela e extrai o Hurst da inclinação da regressão linear.

    Modos ('kind'):
    1. 'returns' (Recomendado):
       - Input: Log-Retornos.
       - Analisa a persistência da volatilidade/magnitude.
       
    2. 'detrended_price':
       - Input: Log-Preços.
       - Remove a tendência linear global da janela antes de calcular o R/S.
       - Foca na oscilação em torno da tendência (Reversão vs Persistência).

    3. 'price':
       - Input: Log-Preços brutos.
       - Menos robusto em tendências fortes, mas útil para análise bruta.

    Args:
        data (pd.Series): Série temporal de preços de fechamento.
        window (int): Tamanho da janela deslizante (Recomendado > 100 para significância estatística).
        kind (str): 'returns', 'detrended_price' ou 'price'.
        min_lag (int): Tamanho mínimo da sub-janela para o cálculo R/S (padrão 8).

    Returns:
        pd.Series: Série temporal com o Hurst estimado via regressão.
    """
    
    # 1. Preparação dos Dados
    if kind == 'returns':
        series = np.log(data / data.shift(1))
    elif kind in ['price', 'detrended_price']:
        series = np.log(data)
    else:
        raise ValueError(f"Kind '{kind}' não suportado. Use 'returns', 'price' ou 'detrended_price'.")

    # Função interna otimizada para ser usada no apply
    def get_hurst_loglog(chunk):
        # Conversão rápida para numpy
        X = chunk.values
        N = len(X)
        
        # --- Pré-processamento Específico ---
        if kind == 'detrended_price':
            # Remove tendência linear global da janela atual
            x_axis = np.arange(N)
            coeffs = np.polyfit(x_axis, X, 1)
            trend = coeffs[0] * x_axis + coeffs[1]
            X = X - trend
        
        # --- Definição das Escalas (Lags) ---
        # Geramos escalas de potência de 2 ou divisores lógicos (ex: 8, 16, 32...)
        # Limitamos a max_lag a N/2 para ter pelo menos 2 pontos de dados
        max_lag = N // 2
        if max_lag < min_lag:
            return np.nan
            
        # Cria lista de escalas (powers of 2 é comum, mas steps lineares também funcionam)
        # Aqui usamos logspace para distribuir bem os pontos na régua log-log
        # Ex: para window=100, lags ~ [8, 11, 16, 22, 32, 45]
        num_points = int(np.log2(max_lag / min_lag)) + 2
        lags = np.unique(np.geomspace(min_lag, max_lag, num=num_points).astype(int))
        lags = lags[lags < N] # Segurança
        
        if len(lags) < 3:
            # Pontos insuficientes para uma regressão confiável
            return np.nan

        rs_values = []
        
        # --- Loop R/S sobre as Escalas ---
        for lag in lags:
            # Dividir a série X em pedaços de tamanho 'lag'
            # Cortamos o final que não cabe (floor division)
            num_chunks = N // lag
            if num_chunks < 1: 
                continue
                
            # Reshape para (num_chunks, lag) ignorando sobras
            cutoff = num_chunks * lag
            X_reshaped = X[:cutoff].reshape(num_chunks, lag)
            
            # Cálculo vetorizado para todos os blocos desse lag
            # 1. Média de cada bloco (axis=1)
            means = np.mean(X_reshaped, axis=1, keepdims=True)
            
            # 2. Desvios da média (Y)
            Y = X_reshaped - means
            
            # 3. Série Acumulada (Z)
            Z = np.cumsum(Y, axis=1)
            
            # 4. Range (R)
            R = np.max(Z, axis=1) - np.min(Z, axis=1)
            
            # 5. Desvio Padrão (S)
            S = np.std(X_reshaped, axis=1, ddof=1)
            
            # Evitar divisão por zero
            S[S == 0] = 1e-9 
            
            # 6. R/S Médio para essa escala
            rs_avg = np.mean(R / S)
            rs_values.append(rs_avg)

        # --- Regressão Log-Log ---
        if not rs_values:
            return np.nan
            
        # y = log(R/S), x = log(lag)
        log_rs = np.log(rs_values)
        log_lags = np.log(lags)
        
        # Regressão linear: polyfit grau 1 retorna [slope, intercept]
        try:
            slope, _ = np.polyfit(log_lags, log_rs, 1)
            return slope
        except:
            return np.nan

    # 3. Aplicação Rolling
    # min_periods=window garante janelas completas
    hurst_series = series.rolling(window=window, min_periods=window).apply(get_hurst_loglog, raw=False)
    
   # Mantivemos o nome antigo para compatibilidade com analysis.py e run_scanner.py
    hurst_series.name = f'Hurst_{window}_{kind}' 
    return hurst_series