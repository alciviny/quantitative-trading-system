import pandas as pd
import pandas_ta as ta
from co_piloto_quant.config import (PROCESSED_DATA_PATH, STOCH_K_PERIOD,
                                    STOCH_K_SMOOTH, STOCH_D_SMOOTH,
                                    SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
                                    BB_PERIOD, PRICE_BB_DEVIATIONS)

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
    """
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos os indicadores técnicos necessários.
    """
    if len(df) < 200:
        return pd.DataFrame()

    # 0. Garante Tendência Macro (WWMA_200)
    if 'WWMA_200' not in df.columns:
        df['WWMA_200'] = ww_moving_average(df, period=200, column='close')

    # 1. IFR (RSI) 120
    df['IFR_120'] = ta.rsi(df['close'], length=120)

    # 2. Bandas de Bollinger de PREÇO
    try:
        bb_df = bollinger_bands(df, period=BB_PERIOD, std_devs=PRICE_BB_DEVIATIONS)
        df = safe_join(df, bb_df)
    except Exception as e:
        print(f"ERRO ao calcular Bandas de Bollinger: {e}")
        return pd.DataFrame()

    # 3. Oscilador: Estocástico Customizado
    try:
        stoch_df = calculate_stochastic_custom(
            df,
            k_period=STOCH_K_PERIOD,
            k_smooth=STOCH_K_SMOOTH,
            d_smooth=STOCH_D_SMOOTH
        )
        df = safe_join(df, stoch_df)
    except Exception as e:
        print(f"ERRO ao calcular Estocástico: {e}")

    # 4. System TPM (OBTR e WAD)
    try:
        obtr_tpm = calculate_system_tpm(df, indicator='obtr', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, obtr_tpm)
        
        wad_tpm = calculate_system_tpm(df, indicator='wad', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, wad_tpm)
    except Exception as e:
        print(f"ERRO TPM: {e}")
    
    return df

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica as regras da estratégia.
    Atualização: Filtros de Estocástico REMOVIDOS para Alta e Baixa.
    """
    period = 200
    
    # --- Mapeamento de Colunas (Nomes exatos gerados pelos indicadores) ---
    wwma_200 = 'WWMA_200'
    
    # Bandas de Preço
    bb_upper_1_0 = f'BB_Upper_{period}_1.0'
    bb_lower_1_0 = f'BB_Lower_{period}_1.0'
    bb_upper_0_45 = f'BB_Upper_{period}_0.45'
    bb_lower_0_45 = f'BB_Lower_{period}_0.45'
    
    # TPM (OBTR/WAD) - Nomes com underline no decimal
    obtr_mid = 'obtr_bb_middle_band'
    wad_mid = 'wad_bb_middle_band'
    
    obtr_upper_0_45 = 'obtr_bb_upper_band_0_45'
    obtr_lower_0_45 = 'obtr_bb_lower_band_0_45'
    wad_upper_0_45 = 'wad_bb_upper_band_0_45'
    wad_lower_0_45 = 'wad_bb_lower_band_0_45'
    
    # Osciladores
    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    ifr = 'IFR_120'

    # Verifica integridade
    required_cols = [bb_upper_1_0, bb_lower_1_0, 'close', 'obtr', 'wad', wwma_200, stoch_k]
    if any(col not in latest_data or pd.isna(latest_data[col]) for col in required_cols):
        return {} # Retorna vazio se faltar dados críticos ou se houver NaN

    # =========================================================================
    # LÓGICA DAS REGRAS (ATUALIZADA)
    # =========================================================================

    # 1. Potencial Alta (Agressivo)
    # -------------------------------------------------------------------------
    # - Preço > Média 200 (Tendência Alta)
    # - Preço dentro da Banda 1.0 (Não esticado/Consolidado)
    # - Fluxo (OBTR ou WAD) > Banda Central (Força Compradora)
    # - REMOVIDO: Estocástico < 50
    
    preco_dentro_1_0 = (latest_data['close'] <= latest_data[bb_upper_1_0]) & \
                       (latest_data['close'] >= latest_data[bb_lower_1_0])
                       
    fluxo_alta = (latest_data['obtr'] > latest_data[obtr_mid]) | \
                 (latest_data['wad'] > latest_data[wad_mid])
                 
    tendencia_alta = latest_data['close'] > latest_data[wwma_200]
    
    potencial_alta = tendencia_alta & preco_dentro_1_0 & fluxo_alta

    # 2. Potencial Baixa (Agressivo)
    # -------------------------------------------------------------------------
    # - Preço < Média 200 (Tendência Baixa)
    # - Preço dentro da Banda 1.0 (Não esticado/Consolidado)
    # - Fluxo (OBTR ou WAD) < Banda Central (Força Vendedora)
    # - REMOVIDO: Estocástico > 50
    
    fluxo_baixa = (latest_data['obtr'] < latest_data[obtr_mid]) | \
                  (latest_data['wad'] < latest_data[wad_mid])
                  
    tendencia_baixa = latest_data['close'] < latest_data[wwma_200]
    
    potencial_baixa = tendencia_baixa & preco_dentro_1_0 & fluxo_baixa

    # 3. Potencial Squeeze (Explosão)
    # -------------------------------------------------------------------------
    preco_squeeze = (latest_data['close'] <= latest_data[bb_upper_0_45]) & \
                    (latest_data['close'] >= latest_data[bb_lower_0_45])
    
    wad_squeeze = (latest_data['wad'] <= latest_data[wad_upper_0_45]) & \
                  (latest_data['wad'] >= latest_data[wad_lower_0_45])
    
    obtr_squeeze = (latest_data['obtr'] <= latest_data[obtr_upper_0_45]) & \
                   (latest_data['obtr'] >= latest_data[obtr_lower_0_45])
                   
    potencial_squeeze = preco_squeeze & (wad_squeeze | obtr_squeeze)

    # 4. Setups de IFR (Reversão/Oportunidade)
    # -------------------------------------------------------------------------
    ifr_neutro = (latest_data[ifr] >= 48) & (latest_data[ifr] <= 52)
    squeeze_ifr_alta = ifr_neutro & (latest_data[stoch_k] < 30)
    squeeze_ifr_baixa = ifr_neutro & (latest_data[stoch_k] > 70)

    return {
        'Sinal_Compra': bool(potencial_alta),
        'Sinal_Venda': bool(potencial_baixa),
        
        'Potencial_Alta': bool(potencial_alta),
        'Potencial_Baixa': bool(potencial_baixa),
        'Potencial_Squeeze': bool(potencial_squeeze),
        
        'Squeeze_IFR_Alta': bool(squeeze_ifr_alta),
        'Squeeze_IFR_Baixa': bool(squeeze_ifr_baixa),
        
        # Flags Visuais
        'Filtro_Consolidacao': bool(preco_dentro_1_0),
        'Preco_Em_Compressao': bool(preco_squeeze)
    }