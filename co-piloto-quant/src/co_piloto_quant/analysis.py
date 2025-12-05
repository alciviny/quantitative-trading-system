import pandas as pd
import pandas_ta as ta
from co_piloto_quant.config import (PROCESSED_DATA_PATH, STOCH_K_PERIOD,
                                     STOCH_K_SMOOTH, STOCH_D_SMOOTH,
                                     SYSTEM_PERIOD, SYSTEM_DEVIATIONS,
                                     BB_PERIOD, PRICE_BB_DEVIATIONS)
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.ehlers_hilbert import ehlers_sinewave

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

def calculate_indicators(df: pd.DataFrame, calculate_hurst: bool = True) -> pd.DataFrame:
    if 'close' in df.columns:
        df = df[df['close'] > 0].copy()

    df = df[~df.index.duplicated(keep='first')]

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
    try:
        hurst = calculate_rolling_hurst(df['close'], window=HURST_WINDOW, kind='returns')
        df = safe_join(df, pd.DataFrame(hurst))
    except Exception as e:
        print(f"ERRO Hurst: {e}")
        return pd.DataFrame()
    try:
       
        entropy_series = calculate_rolling_entropy(df['close'], window=20)
        entropy_series.name = 'Entropy_20'
        df = safe_join(df, entropy_series.to_frame())
    except Exception as e:
        print(f"ERRO Entropia: {e}")
        return  pd.DataFrame()
    try:
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
    try:
        hilbert_df = ehlers_sinewave(df, column='close')
        df = safe_join(df, hilbert_df)
    except Exception as e:
        print(f"ERRO Hilbert: {e}")
    
    return df


# No arquivo src/co_piloto_quant/analysis.py

def check_rules(latest_data: pd.Series) -> dict:

    """

    Verifica os sinais de compra/venda com uma camada de "Veto por Regime de Mercado".

    1. Filtra ativos com comportamento indesejado (lateral, ruidoso, sem sustentação).

    2. Se aprovado no regime, aplica a lógica de sinal técnico (bandas, estocástico).

    """

    # --- 1. VETO POR REGIME DE MERCADO ("Porteiros") ---

    hurst_col = 'Hurst_72_returns'

    entropy_col = 'Entropy_20'

    halflife_col = 'HalfLife_60'



    # Checagem de segurança para dados de regime

    regime_cols = [hurst_col, entropy_col, halflife_col]

    if any(col not in latest_data or pd.isna(latest_data[col]) for col in regime_cols):

        missing_cols = [col for col in regime_cols if col not in latest_data or pd.isna(latest_data[col])]

        return {

            'Sinal_Compra': False, 'Sinal_Venda': False, 'Stop_Loss_Sugerido_Long': None,

            'Stop_Loss_Sugerido_Short': None, 'Motivo_Bloqueio': f"Dados de regime insuficientes ({', '.join(missing_cols)})"

        }



    # Regra 1: Filtro de Tendência (Hurst)

    hurst_val = latest_data[hurst_col]

    if hurst_val < 0.53:

        return {

            'Sinal_Compra': False, 'Sinal_Venda': False, 'Stop_Loss_Sugerido_Long': None,

            'Stop_Loss_Sugerido_Short': None, 'Motivo_Bloqueio': f"Reprovado por Hurst Baixo: {hurst_val:.2f}"

        }



    # Regra 2: Filtro de Ruído (Entropia)

    entropy_val = latest_data[entropy_col]

    if entropy_val > 3.2:

        return {

            'Sinal_Compra': False, 'Sinal_Venda': False, 'Stop_Loss_Sugerido_Long': None,

            'Stop_Loss_Sugerido_Short': None, 'Motivo_Bloqueio': f"Reprovado por Entropia Alta: {entropy_val:.2f}"

        }



    # Regra 3: Filtro de Sustentabilidade (Half-Life)

    halflife_val = latest_data[halflife_col]

    if halflife_val < 15:

        return {

            'Sinal_Compra': False, 'Sinal_Venda': False, 'Stop_Loss_Sugerido_Long': None,

            'Stop_Loss_Sugerido_Short': None, 'Motivo_Bloqueio': f"Reprovado por Half-Life Baixo: {halflife_val:.0f} dias"

        }



    # --- 2. LÓGICA DE SINAL TÉCNICO (Executada apenas se o ativo for aprovado) ---

    

    wwma_200 = 'WWMA_200'

    bb_upper_0_45 = f'BB_Upper_{BB_PERIOD}_0.45'

    bb_lower_0_45 = f'BB_Lower_{BB_PERIOD}_0.45'

    bb_middle = f'BB_Middle_{BB_PERIOD}'

    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}'

    

    strategy_cols = ['close', wwma_200, bb_upper_0_45, bb_lower_0_45, bb_middle, stoch_k]

    if any(col not in latest_data or pd.isna(latest_data[col]) for col in strategy_cols):

        missing_cols = [col for col in strategy_cols if col not in latest_data or pd.isna(latest_data[col])]

        return {

            'Sinal_Compra': False, 'Sinal_Venda': False, 'Stop_Loss_Sugerido_Long': None,

            'Stop_Loss_Sugerido_Short': None, 'Motivo_Bloqueio': f"Dados de estratégia insuficientes ({', '.join(missing_cols)})"

        }



    is_uptrend = latest_data['close'] > latest_data[wwma_200]

    is_in_buy_zone = (latest_data['close'] <= latest_data[bb_upper_0_45]) and (latest_data['close'] >= latest_data[bb_middle])

    is_stoch_buy = latest_data[stoch_k] < 30

    sinal_compra_final = is_uptrend and is_in_buy_zone and is_stoch_buy



    is_downtrend = latest_data['close'] < latest_data[wwma_200]

    is_in_sell_zone = (latest_data['close'] >= latest_data[bb_lower_0_45]) and (latest_data['close'] <= latest_data[bb_middle])

    is_stoch_sell = latest_data[stoch_k] > 70

    sinal_venda_final = is_downtrend and is_in_sell_zone and is_stoch_sell

    

    # --- 3. MONTAGEM DO DICIONÁRIO DE RETORNO ---

    motivo = "Aprovado no regime, sem gatilho técnico"

    if sinal_compra_final:

        motivo = "Aprovado para Compra"

    elif sinal_venda_final:

        motivo = "Aprovado para Venda"



    return {

        'Sinal_Compra': bool(sinal_compra_final),

        'Sinal_Venda': bool(sinal_venda_final),

        'Stop_Loss_Sugerido_Long': float(latest_data[bb_lower_0_45]) if sinal_compra_final else None,

        'Stop_Loss_Sugerido_Short': float(latest_data[bb_upper_0_45]) if sinal_venda_final else None,

        'Motivo_Bloqueio': motivo

    }
