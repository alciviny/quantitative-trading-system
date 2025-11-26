# src/co_piloto_quant/analysis.py

import pandas as pd
import pandas_ta as ta
from co_piloto_quant.config import PROCESSED_DATA_PATH

# Imports da arquitetura do projeto
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average

def load_processed_data(ticker: str) -> pd.DataFrame:
    """Carrega os dados processados de um arquivo CSV."""
    file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
    if not file_path.exists():
        print(f"Arquivo de dados processados não encontrado para {ticker} em {file_path}")
        return pd.DataFrame()
    
    print(f"Carregando dados processados de {file_path}...")
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df

def safe_join(df_original: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """
    Função auxiliar para fazer join apenas das colunas que ainda não existem.
    Evita o erro 'columns overlap but no suffix specified'.
    """
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos os indicadores técnicos necessários para as novas regras.
    """
    # Se o DataFrame não tiver dados suficientes para a maior janela (200), retorne vazio.
    if len(df) < 200:
        return pd.DataFrame()

    # 0. Garante Tendência Macro (WWMA_200) se ainda não existir
    if 'WWMA_200' not in df.columns:
        df['WWMA_200'] = ww_moving_average(df, period=200, column='close')

    # 1. IFR (RSI) com período 120
    df['IFR_120'] = ta.rsi(df['close'], length=120)

    # 2. Bandas de Bollinger de PREÇO
    #    Adicionamos os desvios 0.45 e 1.0 conforme solicitado nas novas regras
    try:
        bb_df = bollinger_bands(df, period=200, std_devs=[0.45, 1.0])
        df = safe_join(df, bb_df)
    except Exception as e:
        print(f"ERRO ao calcular Bandas de Bollinger: {e}")
        return pd.DataFrame()

    # 3. Oscilador: Estocástico Customizado
    try:
        stoch_df = calculate_stochastic_custom(df)
        df = safe_join(df, stoch_df)
    except Exception as e:
        print(f"ERRO ao calcular Estocástico: {e}")

    # 4. System TPM com OBTR (Bandas 0.45, 1.0, 1.5, 2.0 já são padrão)
    try:
        obtr_tpm = calculate_system_tpm(df, indicator='obtr')
        df = safe_join(df, obtr_tpm)
    except Exception as e:
        print(f"ERRO ao calcular System TPM (OBTR): {e}")

    # 5. System TPM com WAD (Bandas 0.45, 1.0, 1.5, 2.0 já são padrão)
    try:
        wad_tpm = calculate_system_tpm(df, indicator='wad')
        df = safe_join(df, wad_tpm)
    except Exception as e:
        print(f"ERRO ao calcular System TPM (WAD): {e}")
    
    return df

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica as novas regras da estratégia (Potencial Alta, Baixa, Squeeze, etc).
    """
    period = 200
    
    # --- Mapeamento de Colunas ---
    # Tendência Macro
    wwma_200 = 'WWMA_200'

    # Bandas de Preço (std 1.0 e 0.45)
    # Nota: A função bollinger_bands usa o float no nome (ex: 1.0)
    bb_upper_1_0 = f'BB_Upper_{period}_1.0'
    bb_lower_1_0 = f'BB_Lower_{period}_1.0'
    bb_upper_0_45 = f'BB_Upper_{period}_0.45'
    bb_lower_0_45 = f'BB_Lower_{period}_0.45'
    
    # System TPM (OBTR e WAD)
    # Nota: A função multi_bollinger_bands substitui ponto por underline (ex: 0_45)
    obtr_mid = 'obtr_bb_middle_band'
    wad_mid = 'wad_bb_middle_band'
    
    obtr_upper_0_45 = 'obtr_bb_upper_band_0_45'
    obtr_lower_0_45 = 'obtr_bb_lower_band_0_45'
    
    wad_upper_0_45 = 'wad_bb_upper_band_0_45'
    wad_lower_0_45 = 'wad_bb_lower_band_0_45'
    
    # Osciladores
    stoch_k = 'stoch_k_80_3'
    ifr = 'IFR_120'

    # Verifica colunas essenciais
    required_cols = [bb_upper_1_0, bb_lower_1_0, stoch_k, ifr, 'close', 'obtr', 'wad', wwma_200]
    missing = [c for c in required_cols if c not in latest_data]
    if missing:
        raise KeyError(f"Colunas ausentes para verificação: {missing}")

    # --- LÓGICA DAS REGRAS ---

    # 1. Potencial Alta
    # Preço dentro do desvio 1.0
    preco_dentro_1_0 = (latest_data['close'] <= latest_data[bb_upper_1_0]) & \
                       (latest_data['close'] >= latest_data[bb_lower_1_0])
    # OBTR > Media200 E/OU Williams > Media200
    fluxo_alta = (latest_data['obtr'] > latest_data[obtr_mid]) | \
                 (latest_data['wad'] > latest_data[wad_mid])
    # Preço acima da Média de 200 para confirmar tendência
    tendencia_alta = latest_data['close'] > latest_data[wwma_200]
    
    potencial_alta = preco_dentro_1_0 & fluxo_alta & tendencia_alta

    # 2. Potencial Baixa
    # Preço dentro do desvio 1.0 (já calculado acima)
    # OBTR < Media200 E/OU Williams < Media200
    fluxo_baixa = (latest_data['obtr'] < latest_data[obtr_mid]) | \
                  (latest_data['wad'] < latest_data[wad_mid])
    # Preço abaixo da Média de 200 para confirmar tendência
    tendencia_baixa = latest_data['close'] < latest_data[wwma_200]
    
    potencial_baixa = preco_dentro_1_0 & fluxo_baixa & tendencia_baixa

    # 3. Potencial Squeeze (Compressão Extrema)
    # Preço dentro do desvio 0.45
    preco_squeeze = (latest_data['close'] <= latest_data[bb_upper_0_45]) & \
                    (latest_data['close'] >= latest_data[bb_lower_0_45])
    
    # Williams dentro do desvio 0.45
    wad_squeeze = (latest_data['wad'] <= latest_data[wad_upper_0_45]) & \
                  (latest_data['wad'] >= latest_data[wad_lower_0_45])
    
    # E/OU OBTR dentro do desvio 0.45
    obtr_squeeze = (latest_data['obtr'] <= latest_data[obtr_upper_0_45]) & \
                   (latest_data['obtr'] >= latest_data[obtr_lower_0_45])
                   
    potencial_squeeze = preco_squeeze & (wad_squeeze | obtr_squeeze)

    # 4. Potencial Squeeze IFR Alta
    ifr_neutro = (latest_data[ifr] >= 48) & (latest_data[ifr] <= 52)
    squeeze_ifr_alta = ifr_neutro & (latest_data[stoch_k] < 30)

    # 5. Potencial Squeeze IFR Baixa
    squeeze_ifr_baixa = ifr_neutro & (latest_data[stoch_k] > 70)

    # Para compatibilidade com o scanner, definimos Sinal_Compra e Sinal_Venda
    # baseados nas regras de Potencial Alta/Baixa
    return {
        # Sinais Principais (usados pelo scanner para classificar Compra/Venda)
        'Sinal_Compra': bool(potencial_alta),
        'Sinal_Venda': bool(potencial_baixa),
        
        # Sinais Específicos para o Relatório Detalhado
        'Potencial_Alta': bool(potencial_alta),
        'Potencial_Baixa': bool(potencial_baixa),
        'Potencial_Squeeze': bool(potencial_squeeze),
        'Squeeze_IFR_Alta': bool(squeeze_ifr_alta),
        'Squeeze_IFR_Baixa': bool(squeeze_ifr_baixa),
        
        # Variaveis de Debug
        'Filtro_Consolidacao': bool(preco_dentro_1_0), # Reutilizando nome para compatibilidade visual
        'Preco_Em_Compressao': bool(preco_squeeze)     # Reutilizando nome para compatibilidade visual
    }