import pandas as pd
from co_piloto_quant.data.indicator_engine import IndicatorEngine # Import para type hinting se necessário
from co_piloto_quant.indicators.names import IndicatorNames

# --- MODO LIVE (Para o Robô operar 1 vela por vez) ---
def check_rules_live(df: pd.DataFrame) -> dict:
    """
    Retorna decisão para a última vela disponível.
    """
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # Nomes padronizados (Certifique-se que o Engine calculou 'ww_ma')
    # Nota: No script de visualização você adicionou 'wwma', então vamos usar ele
    price_col = 'close'
    ma_col = IndicatorNames.wwma(20) # Usando Wilder pois foi o que adicionamos no engine

    if ma_col not in df.columns:
        return {'action': 'NEUTRO', 'reason': 'Indicador ausente'}

    # Cruzamento Alta
    buy_signal = previous[price_col] < previous[ma_col] and latest[price_col] > latest[ma_col]
    
    # Cruzamento Baixa
    sell_signal = previous[price_col] > previous[ma_col] and latest[price_col] < latest[ma_col]

    if buy_signal:
        return {'action': 'COMPRA', 'price': latest['close']}
    elif sell_signal:
        return {'action': 'VENDA', 'price': latest['close']}
    
    return {'action': 'NEUTRO'}

# --- MODO VETORIZADO (Para o Backtest rápido) ---
def check_rules_vectorized(df: pd.DataFrame) -> dict:
    """
    Retorna Séries booleanas para todo o histórico (VectorBT).
    """
    price = df['close']
    # Assumindo que o Engine calculou e nomeou como 'wwma_20'
    ma = df[IndicatorNames.wwma(20)]
    
    # Lógica Vetorizada (Rápida)
    # Crossover: Preço cruza acima da média
    entries = (price > ma) & (price.shift(1) <= ma.shift(1))
    
    # Crossunder: Preço cruza abaixo da média
    exits = (price < ma) & (price.shift(1) >= ma.shift(1))
    
    return {
        'entries': entries,
        'exits': exits,
        'short_entries': pd.Series(False, index=df.index), # Sem short nessa
        'short_exits': pd.Series(False, index=df.index)
    }

# Fallback genérico
check_rules = check_rules_live