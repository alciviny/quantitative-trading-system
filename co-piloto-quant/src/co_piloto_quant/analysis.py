import pandas as pd
import pandas_ta as ta
from co_piloto_quant.config import (PROCESSED_DATA_PATH, STOCH_K_PERIOD,
                                     STOCH_K_SMOOTH, STOCH_D_SMOOTH,
                                     SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
                                     BB_PERIOD, PRICE_BB_DEVIATIONS)

# Procure a linha antiga e mude para:
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst

# === CONFIGURAÇÃO DE SENSIBILIDADE DO HURST ===
HURST_WINDOW = 72 
HURST_TREND_THRESHOLD = 0.54 
HURST_MEAN_REV_THRESHOLD = 0.46

def load_processed_data(ticker: str) -> pd.DataFrame:
    file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
    if not file_path.exists():
        print(f"Arquivo não encontrado: {file_path}")
        return pd.DataFrame()
    return pd.read_csv(file_path, index_col=0, parse_dates=True)

def safe_join(df_original: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    cols_to_use = df_new.columns.difference(df_original.columns)
    return df_original.join(df_new[cols_to_use])

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < 200: return pd.DataFrame()

    if 'WWMA_200' not in df.columns:
        df['WWMA_200'] = ww_moving_average(df, period=200, column='close')

    df['IFR_120'] = ta.rsi(df['close'], length=120)

    try:
        bb_df = bollinger_bands(df, period=BB_PERIOD, std_devs=PRICE_BB_DEVIATIONS)
        df = safe_join(df, bb_df)
    except Exception as e:
        print(f"ERRO BB: {e}")
        return pd.DataFrame()

    try:
        stoch_df = calculate_stochastic_custom(df, k_period=STOCH_K_PERIOD, k_smooth=STOCH_K_SMOOTH, d_smooth=STOCH_D_SMOOTH)
        df = safe_join(df, stoch_df)
    except Exception as e:
        print(f"ERRO Stoch: {e}")
        return pd.DataFrame()

    try:
        obtr_tpm = calculate_system_tpm(df, indicator='obtr', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, obtr_tpm)
        wad_tpm = calculate_system_tpm(df, indicator='wad', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, wad_tpm)
    except Exception as e:
        print(f"ERRO TPM: {e}")
        return pd.DataFrame()

    # Hurst Exponent (Janela 72, Returns)
    try:
        hurst = calculate_rolling_hurst(df['close'], window=HURST_WINDOW, kind='returns')
        df = safe_join(df, pd.DataFrame(hurst))
    except Exception as e:
        print(f"ERRO Hurst: {e}")
        return pd.DataFrame()
    
    # ... Dentro de calculate_indicators ...

# --- NOVO BLOCO OU/HALF-LIFE INSTITUCIONAL ---
    try:
    # Retorna DataFrame com Beta, HalfLife, R2, t_Beta...
        ou_stats = calculate_rolling_ou_params(
        df['close'], 
        window=60, 
        beta_floor=-0.02, 
        strict_mode=False,
        use_log=True
    )
        df = safe_join(df, ou_stats)
    except Exception as e:
        print(f"ERRO OU Params: {e}")
        return pd.DataFrame()
# ---------------------------------------------
    
    return df
    

def check_rules(latest_data: pd.Series) -> dict:
    period = 200
    wwma_200 = 'WWMA_200'
    bb_upper_1_0 = f'BB_Upper_{period}_1.0'
    bb_lower_1_0 = f'BB_Lower_{period}_1.0'
    bb_upper_0_45 = f'BB_Upper_{period}_0.45'
    bb_lower_0_45 = f'BB_Lower_{period}_0.45'
    obtr_mid = 'obtr_bb_middle_band'
    wad_mid = 'wad_bb_middle_band'
    obtr_upper_0_45 = 'obtr_bb_upper_band_0_45'
    obtr_lower_0_45 = 'obtr_bb_lower_band_0_45'
    wad_upper_0_45 = 'wad_bb_upper_band_0_45'
    wad_lower_0_45 = 'wad_bb_lower_band_0_45'
    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'
    ifr = 'IFR_120'

    # Nome da coluna ajustado para a nova janela
    hurst_col = f'Hurst_{HURST_WINDOW}_returns'

    required_cols = [bb_upper_1_0, bb_lower_1_0, 'close', 'obtr', 'wad', wwma_200, stoch_k]
    if any(col not in latest_data or pd.isna(latest_data[col]) for col in required_cols):
        return {} 

    # 1. Regime (Hurst)
    hurst_val = latest_data.get(hurst_col, 0.5)
    is_trending = hurst_val > HURST_TREND_THRESHOLD  
    is_mean_reversion = hurst_val < HURST_MEAN_REV_THRESHOLD

    # 2. Técnica
    preco_dentro_1_0 = (latest_data['close'] <= latest_data[bb_upper_1_0]) & (latest_data['close'] >= latest_data[bb_lower_1_0])
    fluxo_alta = (latest_data['obtr'] > latest_data[obtr_mid]) | (latest_data['wad'] > latest_data[wad_mid])
    tendencia_alta = latest_data['close'] > latest_data[wwma_200]
    potencial_alta_tecnico = tendencia_alta & preco_dentro_1_0 & fluxo_alta

    fluxo_baixa = (latest_data['obtr'] < latest_data[obtr_mid]) | (latest_data['wad'] < latest_data[wad_mid])
    tendencia_baixa = latest_data['close'] < latest_data[wwma_200]
    potencial_baixa_tecnico = tendencia_baixa & preco_dentro_1_0 & fluxo_baixa

    preco_squeeze = (latest_data['close'] <= latest_data[bb_upper_0_45]) & (latest_data['close'] >= latest_data[bb_lower_0_45])
    wad_squeeze = (latest_data['wad'] <= latest_data[wad_upper_0_45]) & (latest_data['wad'] >= latest_data[wad_lower_0_45])
    obtr_squeeze = (latest_data['obtr'] <= latest_data[obtr_upper_0_45]) & (latest_data['obtr'] >= latest_data[obtr_lower_0_45])
    potencial_squeeze = preco_squeeze & (wad_squeeze | obtr_squeeze)

    ifr_val = latest_data.get(ifr, 50)
    ifr_neutro = (ifr_val >= 48) & (ifr_val <= 52)
    squeeze_ifr_alta = ifr_neutro & (latest_data[stoch_k] < 30)
    squeeze_ifr_baixa = ifr_neutro & (latest_data[stoch_k] > 70)

    # 3. Filtragem Final
    sinal_compra_final = potencial_alta_tecnico and is_trending
    sinal_venda_final = potencial_baixa_tecnico and is_trending

    # --- LÓGICA REFINADA ---

    # Nomes das colunas (Sufixo _60 pois window=60)
    hl_col = 'HalfLife_60'
    r2_col = 'R2_60'

    # Obter valores
    hl_val = latest_data.get(hl_col, 1000)
    r2_val = latest_data.get(r2_col, 0)

    # 1. Pullback Sniper (Agora com Filtro de Qualidade)
    # Half-Life curto (< 25) E fit de qualidade razoável (R2 > 5%)
    # R2 muito baixo em Mean Reversion significa que a "força" da mola é aleatória.
    cond_elasticidade = (hl_val < 25) and (r2_val > 0.05)

    # ... (Resto das suas condições de IFR e Hurst) ...

    sinal_pullback_sniper = cond_elasticidade and (hurst_val > 0.55) and (ifr_val < 48)

    return {
        'Sinal_Compra': bool(sinal_compra_final),
        'Sinal_Venda': bool(sinal_venda_final),
        'Potencial_Alta': bool(sinal_compra_final),
        'Potencial_Baixa': bool(sinal_venda_final),
        'Potencial_Alta_Tecnico': bool(potencial_alta_tecnico),
        'Potencial_Baixa_Tecnico': bool(potencial_baixa_tecnico),
        'Potencial_Squeeze': bool(potencial_squeeze),
        'Squeeze_IFR_Alta': bool(squeeze_ifr_alta),
        'Squeeze_IFR_Baixa': bool(squeeze_ifr_baixa),
        'Regime_Tendencia': bool(is_trending),
        'Regime_Lateral': bool(is_mean_reversion),
        'Hurst_Score': float(hurst_val),
        'Filtro_Consolidacao': bool(preco_dentro_1_0),
        'Preco_Em_Compressao': bool(preco_squeeze),
        'Sinal_Pullback_Sniper': bool(sinal_pullback_sniper),
        'Half_Life_Val': float(hl_val),
        'OU_R2': float(r2_val) # Útil para debug
    }

