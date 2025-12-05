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
    # --- CORREÇÃO DE ROBUSTEZ 1: Limpeza de Dados de Input ---
    #---------------------------------------------------------
    if 'close' in df.columns:
        df = df[df['close'] > 0].copy()

    # Remove linhas com índice duplicado que causam erros em cálculos de indicadores
    df = df[~df.index.duplicated(keep='first')]

    if len(df) < 200: return pd.DataFrame()

    if 'WWMA_200' not in df.columns:
        df['WWMA_200'] = ww_moving_average(df, period=200, column='close')

    df['IFR_120'] = ta.rsi(df['close'], length=120)
#----------------------------------------------------------------
    try:
        bb_df = bollinger_bands(df, period=BB_PERIOD, std_devs=PRICE_BB_DEVIATIONS)
        df = safe_join(df, bb_df)
    except Exception as e:
        print(f"ERRO BB: {e}")
        return pd.DataFrame()
#----------------------------------------------------------------
    try:
        stoch_df = calculate_stochastic_custom(df, k_period=STOCH_K_PERIOD, k_smooth=STOCH_K_SMOOTH, d_smooth=STOCH_D_SMOOTH)
        df = safe_join(df, stoch_df)
    except Exception as e:
        print(f"ERRO Stoch: {e}")
        return pd.DataFrame()
#----------------------------------------------------------------
    try:
        obtr_tpm = calculate_system_tpm(df, indicator='obtr', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, obtr_tpm)
        wad_tpm = calculate_system_tpm(df, indicator='wad', period=SYSTEM_PERIOD, deviations=SYSTEM_DEVIATIONS)
        df = safe_join(df, wad_tpm)
    except Exception as e:
        print(f"ERRO TPM: {e}")
        return pd.DataFrame()
#----------------------------------------------------------------
    # Hurst Exponent (Janela 72, Returns)
    try:
        hurst = calculate_rolling_hurst(df['close'], window=HURST_WINDOW, kind='returns')
        df = safe_join(df, pd.DataFrame(hurst))
    except Exception as e:
        print(f"ERRO Hurst: {e}")
        return pd.DataFrame()
#----------------------------------------------------------------    
   
    try:
       
        entropy_series = calculate_rolling_entropy(df['close'], window=20)
        entropy_series.name = 'Entropy_20' # Nome para referência
        df = safe_join(df, entropy_series.to_frame())
    except Exception as e:
        print(f"ERRO Entropia: {e}")
    
        return  pd.DataFrame()
#----------------------------------------------------------------
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
    try:
       
        hilbert_df = ehlers_sinewave(df, column='close')
        df = safe_join(df, hilbert_df)
    except Exception as e:
        print(f"ERRO Hilbert: {e}")
    
    return df
 
""" 
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

    # --- Lógica Hilbert Sine Wave ---
    sine = latest_data.get('Hilbert_Sine', 0)
    lead = latest_data.get('Hilbert_Lead', 0)
    periodo_ciclo = latest_data.get('Hilbert_Period', 20)

    # 1. Cruzamento de Reversão (O gatilho "Sniper")
    # Sine cruzando Lead para CIMA = Fundo do Ciclo (Compra)
    # Sine cruzando Lead para BAIXO = Topo do Ciclo (Venda)
    # Como olhamos apenas o candle atual, usamos a posição relativa
    ciclo_alta = sine > lead
    ciclo_baixa = sine < lead
    
    # 2. Confirmação de Extremos (Evita operar no meio do caminho)
    # Só nos interessa se o Sine estiver nas pontas (-1 a +1)
    # Ex: Sine < -0.7 sugere que estamos na "bacia" do fundo
    fundo_confirmado = sine < -0.7
    topo_confirmado = sine > 0.7

    # 3. Filtro de Qualidade do Ciclo
    # Se o período estimado for muito curto (<10), o mercado está caótico.
    # Se for "saudável" (entre 10 e 60), o sinal é válido.
    ciclo_saudavel = (periodo_ciclo > 10) and (periodo_ciclo < 60)

    # COMBINAÇÃO (Exemplo de sinal final)
    # Compra se: Estivermos no fundo do ciclo E o ciclo virou pra cima E o ciclo é saudável
    sinal_entrada_ciclo = fundo_confirmado and ciclo_alta and ciclo_saudavel

    # 4. Criar Status de Ciclo (para o relatório)
    hilbert_status = "Neutro"
    if not ciclo_saudavel:
        hilbert_status = "Caótico"
    elif fundo_confirmado and ciclo_alta:
        hilbert_status = "Virada (Fundo)"
    elif topo_confirmado and ciclo_baixa:
        hilbert_status = "Virada (Topo)"
    elif fundo_confirmado:
        hilbert_status = "Fundo Extremo"
    elif topo_confirmado:
        hilbert_status = "Topo Extremo"
    elif ciclo_alta:
        hilbert_status = "Subindo"
    elif ciclo_baixa:
        hilbert_status = "Caindo"

    # Obter valor da Entropia
    entropy_val = latest_data.get('Entropy_20', 10.0) # Default alto (risco) se não calculado
    
    # Definição de Regimes de Qualidade
    # Abaixo de 2.8 bits geralmente indica estrutura operável em janela de 20
    is_orderly = entropy_val < 2.8 
    is_chaotic = entropy_val >= 2.8

    # Refinar o Score
    # Se o mercado for caótico, anulamos sinais fracos
    if is_chaotic:
        # Penalidade: Exige confirmação extra ou anula trade
        sinal_compra_final = sinal_compra_final and False # Exemplo radical: Não opera no caos
        # OU, versão mais suave:
        # sinal_compra_final = sinal_compra_final and (hurst_val > 0.6) # Exige tendência MUITO forte para compensar o caos

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
        'OU_R2': float(r2_val), # Útil para debug
        'Sinal_Entrada__Ciclo': bool(sinal_entrada_ciclo),
        'Hilbert_Ciclo': hilbert_status,
        'Hilbert_Sine': float(sine),
        'Hilbert_Periodo': float(periodo_ciclo),
        'Regime_Ordenado': bool(is_orderly),
        'Regime_Caotico': bool(is_chaotic),
        'Entropy_Score': float(entropy_val),
    }

 """

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica os sinais de compra e venda com base na estratégia unificada de backtest.
    A lógica é baseada em tendência, pullback para a 'meia banda' e confirmação do estocástico.
    """
    # --- 1. Definição de Nomes de Colunas ---
    # É crucial que estes nomes correspondam exatamente aos gerados em 'calculate_indicators'
    period = 200
    wwma_200 = 'WWMA_200'
    bb_upper_0_45 = f'BB_Upper_{period}_0.45'
    bb_lower_0_45 = f'BB_Lower_{period}_0.45'
    bb_middle = f'BB_Middle_{period}'
    # O nome da coluna do estocástico deve ser o mesmo usado nos backtests
    stoch_k = f'stoch_k_{STOCH_K_PERIOD}_{STOCH_K_SMOOTH}' 

    # --- 2. Verificação de Segurança ---
    # Garante que todos os dados necessários para a decisão estão presentes.
    required_cols = [
        'close', wwma_200, bb_upper_0_45, bb_lower_0_45, bb_middle, stoch_k
    ]
    if any(col not in latest_data or pd.isna(latest_data[col]) for col in required_cols):
        return {
            'Sinal_Compra': False,
            'Sinal_Venda': False,
            'Stop_Loss_Sugerido_Long': None,
            'Stop_Loss_Sugerido_Short': None,
        }

    # --- 3. Lógica de Sinais (Exatamente como no Backtest) ---

    # Condições de Compra (Long)
    is_uptrend = latest_data['close'] > latest_data[wwma_200]
    is_in_buy_zone = (latest_data['close'] <= latest_data[bb_upper_0_45]) and \
                     (latest_data['close'] >= latest_data[bb_middle])
    is_stoch_buy = latest_data[stoch_k] < 30

    sinal_compra_final = is_uptrend and is_in_buy_zone and is_stoch_buy

    # Condições de Venda (Short)
    is_downtrend = latest_data['close'] < latest_data[wwma_200]
    is_in_sell_zone = (latest_data['close'] >= latest_data[bb_lower_0_45]) and \
                      (latest_data['close'] <= latest_data[bb_middle])
    is_stoch_sell = latest_data[stoch_k] > 70

    sinal_venda_final = is_downtrend and is_in_sell_zone and is_stoch_sell
    
    # --- 4. Definição de Stops Sugeridos ---
    # O stop sugerido é a banda oposta da zona de entrada, que atuaria como
    # uma invalidação da condição de 'meia banda'.
    stop_long = latest_data[bb_lower_0_45]
    stop_short = latest_data[bb_upper_0_45]

    # --- 5. Montagem do Dicionário de Retorno ---
    return {
        'Sinal_Compra': bool(sinal_compra_final),
        'Sinal_Venda': bool(sinal_venda_final),
        'Stop_Loss_Sugerido_Long': float(stop_long) if sinal_compra_final else None,
        'Stop_Loss_Sugerido_Short': float(stop_short) if sinal_venda_final else None,
    }