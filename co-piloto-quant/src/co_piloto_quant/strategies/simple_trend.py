import pandas as pd
from co_piloto_quant.data.names import IndicatorNames

def check_rules(df: pd.DataFrame) -> str:
    """
    Estratégia de exemplo: Simple Trend Follower.
    - Compra: Se o preço de fechamento cruzar acima da Média Móvel de 20 períodos.
    - Vende: Se o preço de fechamento cruzar abaixo da Média Móvel de 20 períodos.
    
    Args:
        df (pd.DataFrame): DataFrame com dados de mercado e indicadores. 
                           Deve conter 'close' e 'SMA_20'.
                           
    Returns:
        str: 'COMPRA', 'VENDA' ou 'NEUTRO'.
    """
    # Acessa a última vela (a mais recente)
    latest = df.iloc[-1]
    
    # Acessa a penúltima vela para checar o cruzamento
    previous = df.iloc[-2]

    # Nomes das colunas usando IndicatorNames para robustez
    price_col = 'close' # Usamos o fechamento como referência de preço
    ma_col = IndicatorNames.SMA(20) # Média Móvel Simples de 20 períodos

    # Verifica se as colunas necessárias existem
    if price_col not in df.columns or ma_col not in df.columns:
        # Retorna NEUTRO se o indicador não estiver presente para evitar erros
        return 'NEUTRO'

    # --- Lógica de Cruzamento ---
    
    # Cruzamento para CIMA (Compra)
    # Preço na vela anterior estava ABAIXO da média
    # Preço na vela atual está ACIMA da média
    buy_signal = previous[price_col] < previous[ma_col] and latest[price_col] > latest[ma_col]

    # Cruzamento para BAIXO (Venda)
    # Preço na vela anterior estava ACIMA da média
    # Preço na vela atual está ABAIXO da média
    sell_signal = previous[price_col] > previous[ma_col] and latest[price_col] < latest[ma_col]

    if buy_signal:
        return 'COMPRA'
    elif sell_signal:
        return 'VENDA'
    
    return 'NEUTRO'
