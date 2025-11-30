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

# --- NOVO IMPORT ---
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst

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

    # 5. Expoente de Hurst (Filtro de Regime) - ATUALIZADO
    try:
        # kind='detrended_price' remove a tendência linear local para analisar a "qualidade" do movimento
        # Window=100 é o padrão estatístico robusto
        hurst = calculate_rolling_hurst(df['close'], window=100, kind='detrended_price')
        df = safe_join(df, pd.DataFrame(hurst))
    except Exception as e:
        print(f"ERRO ao calcular Hurst: {e}")
    
    return df

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica as regras da estratégia.
    Atualização: Inclui Filtro de Regime via Hurst Exponent (Detrended).
    """
    period = 200
    
    # --- Mapeamento de Colunas (Nomes exatos) ---
    wwma_200 = 'WWMA_200'
    
    # Bandas de Preço
    bb_upper_1_0 = f'BB_Upper_{period}_1.0'
    bb_lower_1_0 = f'BB_Lower_{period}_1.0'
    bb_upper_0_45 = f'BB_Upper_{period}_0.45'
    bb_lower_0_45 = f'BB_Lower_{period}_0.45'
    
    # TPM (OBTR/WAD)
    obtr_mid = 'obtr_bb_middle_band'
    wad_mid = 'wad_bb_middle_band'
    
    obtr_upper_0_45 = 'obtr_bb_upper_band_0_45'
    obtr_lower_0_45 = 'obtr_bb_lower_band_0_45'
    wad_upper_0_45 = 'wad_bb_upper_band_0_45'
    wad_lower_0_45 = 'wad_bb_lower_band_0_45'
    
    # Osciladores
    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    ifr = 'IFR_120'

    # Hurst (Detrended) - Nome da coluna baseado nos parâmetros do calculate_indicators
    hurst_col = 'Hurst_100_detrended_price'

    # Verifica integridade básica
    required_cols = [bb_upper_1_0, bb_lower_1_0, 'close', 'obtr', 'wad', wwma_200, stoch_k]
    if any(col not in latest_data or pd.isna(latest_data[col]) for col in required_cols):
        return {} 

    # =========================================================================
    # 1. ANÁLISE DO REGIME (HURST)
    # =========================================================================
    
    # Recupera o Hurst (usa 0.5 como neutro se não existir por algum motivo)
    hurst_val = latest_data.get(hurst_col, 0.5)

    # Definição dos Regimes (Para Detrended Price)
    # > 0.60: Tendência Persistente (Momentum forte, seguro para rompimentos)
    # < 0.40: Mean Reversion (Preço "preso" ou elástico, seguro para comprar fundos/vender topos)
    is_trending = hurst_val > 0.60
    is_mean_reversion = hurst_val < 0.40

    # =========================================================================
    # 2. ANÁLISE TÉCNICA (SETUP ORIGINAL)
    # =========================================================================

    # --- Setup de Alta (Agressivo) ---
    preco_dentro_1_0 = (latest_data['close'] <= latest_data[bb_upper_1_0]) & \
                       (latest_data['close'] >= latest_data[bb_lower_1_0])
                       
    fluxo_alta = (latest_data['obtr'] > latest_data[obtr_mid]) | \
                 (latest_data['wad'] > latest_data[wad_mid])
                 
    tendencia_alta = latest_data['close'] > latest_data[wwma_200]
    
    potencial_alta_tecnico = tendencia_alta & preco_dentro_1_0 & fluxo_alta

    # --- Setup de Baixa (Agressivo) ---
    fluxo_baixa = (latest_data['obtr'] < latest_data[obtr_mid]) | \
                  (latest_data['wad'] < latest_data[wad_mid])
                  
    tendencia_baixa = latest_data['close'] < latest_data[wwma_200]
    
    potencial_baixa_tecnico = tendencia_baixa & preco_dentro_1_0 & fluxo_baixa

    # --- Setup de Squeeze ---
    preco_squeeze = (latest_data['close'] <= latest_data[bb_upper_0_45]) & \
                    (latest_data['close'] >= latest_data[bb_lower_0_45])
    
    wad_squeeze = (latest_data['wad'] <= latest_data[wad_upper_0_45]) & \
                  (latest_data['wad'] >= latest_data[wad_lower_0_45])
    
    obtr_squeeze = (latest_data['obtr'] <= latest_data[obtr_upper_0_45]) & \
                   (latest_data['obtr'] >= latest_data[obtr_lower_0_45])
                   
    potencial_squeeze = preco_squeeze & (wad_squeeze | obtr_squeeze)

    # --- Setups de IFR ---
    ifr_neutro = (latest_data[ifr] >= 48) & (latest_data[ifr] <= 52)
    squeeze_ifr_alta = ifr_neutro & (latest_data[stoch_k] < 30)
    squeeze_ifr_baixa = ifr_neutro & (latest_data[stoch_k] > 70)

    # =========================================================================
    # 3. FILTRAGEM FINAL PELO REGIME
    # =========================================================================

    # Regra de Ouro: Sinais de TENDÊNCIA só passam se Hurst confirmar TENDÊNCIA.
    # Se o mercado estiver lateral (Hurst baixo), o sinal de rompimento é ignorado (falso rompimento provável).
    
    sinal_compra_final = potencial_alta_tecnico and is_trending
    sinal_venda_final = potencial_baixa_tecnico and is_trending

    return {
        'Potencial_Alta': bool(sinal_compra_final),
        'Potencial_Baixa': bool(sinal_venda_final),
        
        # Sinais originais (sem filtro, para debug)
        'Potencial_Alta_Tecnico': bool(potencial_alta_tecnico),
        'Potencial_Baixa_Tecnico': bool(potencial_baixa_tecnico),
        'Potencial_Squeeze': bool(potencial_squeeze),
        
        'Squeeze_IFR_Alta': bool(squeeze_ifr_alta),
        'Squeeze_IFR_Baixa': bool(squeeze_ifr_baixa),
        
        # --- Metadados de Regime (Para o Dashboard) ---
        'Regime_Tendencia': bool(is_trending),
        'Regime_Lateral': bool(is_mean_reversion),
        'Hurst_Score': float(hurst_val),
        
        # Flags Visuais
        'Filtro_Consolidacao': bool(preco_dentro_1_0),
        'Preco_Em_Compressao': bool(preco_squeeze)
    }