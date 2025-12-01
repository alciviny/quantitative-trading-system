import numpy as np
import pandas as pd

def calculate_rolling_entropy(close_prices: pd.Series, window: int = 20, bins: int = 10) -> pd.Series:
    """
    Calcula a Entropia de Shannon (base 2) sobre os LOG-RETORNOS do ativo.
    
    Esta métrica quantifica a 'Desordem' ou 'Imprevisibilidade' do fluxo de ordens.
    
    Args:
        close_prices (pd.Series): Série de preços de fechamento.
        window (int): Janela de lookback (Padrão: 20 dias).
        bins (int): Número de faixas do histograma (Resolução da análise).
        
    Returns:
        pd.Series: Série temporal da Entropia (Bits de informação).
        
    Interpretação:
        📉 Entropia < 2.0: Mercado Eficiente/Ordenado. Tendências são limpas. (Sinal Verde para operar)
        📈 Entropia > 3.0: Mercado Caótico/Ruído. O preço é um "Random Walk". (Sinal Vermelho)
    """
    
    # 1. Pré-processamento: Converter Preço -> Log Retorno
    # A entropia mede a incerteza da MUDANÇA, não do valor absoluto.
    # fillna(0) garante que o primeiro dado não quebre o cálculo.
    returns = np.log(close_prices / close_prices.shift(1)).fillna(0)
    
    def get_shannon_entropy(x):
        # Se a janela for muito constante (ex: feriado/sem liquidez), entropia é zero.
        if np.all(x == 0):
            return 0.0

        # 1. Histograma (Discretização da Distribuição)
        counts, _ = np.histogram(x, bins=bins)
        
        # 2. Filtrar bins vazios para evitar log(0)
        counts = counts[counts > 0]
        
        # Segurança extra
        if len(counts) == 0:
            return 0.0
        
        # 3. Cálculo das Probabilidades (p)
        probs = counts / counts.sum()
        
        # 4. Fórmula de Shannon: -sum(p * log2(p))
        # Usamos numpy puro para não depender do scipy
        entropy_val = -np.sum(probs * np.log2(probs))
        
        return entropy_val

    # Aplicação rolante com raw=True para performance máxima
    return returns.rolling(window=window).apply(get_shannon_entropy, raw=True)