import vectorbt as vbt
import pandas as pd
import numpy as np
import warnings
import os
import logging
from tqdm import tqdm
import concurrent.futures
from datetime import datetime

from co_piloto_quant.data.database import load_price_data
from co_piloto_quant.analysis import calculate_indicators
from co_piloto_quant.utils import get_expanded_universe
from co_piloto_quant.config import BB_PERIOD, STOCH_K_PERIOD, STOCH_K_SMOOTH
from co_piloto_quant.indicators.names import IndicatorNames


# --- CONFIGURAÇÕES DO BACKTEST ---
INITIAL_CAPITAL = 100000
STOP_LOSS_PCT = 0.06
FEES_PCT = 0.0006
SLIPPAGE_PCT = 0.001

# --- CONFIGURAÇÕES DA ESTRATÉGIA E FILTROS ---
BB_EXIT_STD_DEV = 2.0
ENTROPY_CHAOS_THRESHOLD = 4.5
LIMIT_VOL_VOL = 0.050
LIMIT_RAW_VOL = 0.060

# --- CONFIGURAÇÃO DE LOGS ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

warnings.filterwarnings('ignore')

def run_stability_analysis(ticker: str):
    """
    Executa uma análise de estabilidade de parâmetros para um único ativo,
    varrendo uma faixa de desvios padrão da Banda de Bollinger.
    """
    df_raw = load_price_data(ticker)
    if df_raw is None or df_raw.empty or len(df_raw) < 252: # Aumentado para ter mais dados para z-score
        return None

    # 1. Calcula todos os indicadores necessários, exceto as bandas que serão vetorizadas
    df = calculate_indicators(df_raw, bb_entry_deviation=0) # Passamos 0 para não interferir
    if df is None or df.empty:
        return None

    # --- PROFISSIONALISMO 1: VARREDURA DE PARÂMETROS ---
    bb_dev_range = np.arange(0.2, 0.85, 0.05)
    closes = df['close']

    # 2. Cálculo Vetorizado das Bandas de Bollinger para a varredura
    bb_bands_sweep = vbt.BBANDS.run(closes, window=BB_PERIOD, alpha=bb_dev_range)
    bb_lower_sweep = bb_bands_sweep.lower
    bb_upper_sweep = bb_bands_sweep.upper
    
    # A banda de saída permanece fixa, conforme lógica original
    bb_upper_exit = vbt.BBANDS.run(closes, window=BB_PERIOD, alpha=BB_EXIT_STD_DEV).upper

    # 3. Construção Vetorizada dos Sinais
    # Nomes das colunas para os filtros
    col_stoch_k  = IndicatorNames.stochastic_k(STOCH_K_PERIOD, STOCH_K_SMOOTH)
    col_hurst_z  = IndicatorNames.hurst_z()
    col_entropy_z = IndicatorNames.entropy_z(20)

    # Filtros de regime e estocástico (colunas únicas que serão broadcast)
    mask_regime_ok = (df[col_hurst_z].fillna(0) >= -0.5) & \
                     (df[col_entropy_z].fillna(10) <= ENTROPY_CHAOS_THRESHOLD)
    mask_stoch_buy = df[col_stoch_k] < 30

    # Lógica de entrada vetorizada (multi-coluna)
    mask_buy_zone = (closes.values[:, None] >= bb_lower_sweep) & (closes.values[:, None] <= bb_upper_sweep)
    entries = mask_buy_zone & mask_stoch_buy.values[:, None] & mask_regime_ok.values[:, None]

    # --- CAMADA DE SEGURANÇA ADAPTATIVA (QUANTILE-BASED) ---
    returns = df['close'].pct_change()
    df['VolVol'] = returns.rolling(20).std().diff().abs()
    df['RawVol'] = returns.rolling(20).std()
    
    # Lógica "Profissional" (Adaptativa)
    # Calcula o percentil 90 da volatilidade e entropia nos últimos 500 dias
    rolling_vol_thresh = df['RawVol'].rolling(500, min_periods=30).quantile(0.90)
    
    col_entropy_raw = IndicatorNames.entropy(20)
    rolling_entropy_thresh = df[col_entropy_raw].rolling(500, min_periods=30).quantile(0.90)

    # Condições de filtro adaptativas
    vol_vol_cond = df['VolVol'] <= LIMIT_VOL_VOL # Mantido como filtro de choque de curto prazo
    raw_vol_cond = df['RawVol'] <= rolling_vol_thresh
    raw_entropy_cond = df[col_entropy_raw] <= rolling_entropy_thresh

    # Máscara final de risco:
    risk_safe = vol_vol_cond & raw_vol_cond & raw_entropy_cond
    
    # Aplica o filtro de risco do backtest sobre os sinais de entrada
    entries = entries & risk_safe.values[:, None]
    
    # Lógica de saída (coluna única, será broadcast)
    exits = closes >= bb_upper_exit

    # Shift para evitar look-ahead bias
    entries = entries.shift(1).fillna(False)
    exits = exits.shift(1).fillna(False)

    if not entries.any().any():
        return None

    # 4. Execução do Backtest Massivo
    portfolio = vbt.Portfolio.from_signals(
        close=closes,
        entries=entries,
        exits=exits,
        sl_stop=STOP_LOSS_PCT,
        init_cash=INITIAL_CAPITAL,
        fees=FEES_PCT,
        slippage=SLIPPAGE_PCT,
        freq='1D'
    )
    
    return portfolio

def process_single_ticker_stability(ticker: str):
    """
    Função wrapper para executar a análise de estabilidade, capturar exceções
    e retornar um dicionário com métricas de robustez e o melhor parâmetro.
    """
    try:
        pf = run_stability_analysis(ticker)
        if pf:
            sharpe_ratios = pf.sharpe_ratio()
            
            # Filtra parâmetros que não geraram trades ou tiveram poucos trades
            sharpe_ratios = sharpe_ratios[pf.trades.count() > 3]

            if len(sharpe_ratios) < 3: # Exige um mínimo de resultados válidos
                return None

            # --- O NOVO "HANDOVER": ENCONTRAR O MELHOR PARÂMETRO ---
            # Encontra o desvio (que está no índice) que corresponde ao maior Sharpe
            best_param_dev = sharpe_ratios.idxmax()

            # --- ANÁLISE DE ROBUSTEZ ---
            sharpe_medio = sharpe_ratios.mean()
            sharpe_std = sharpe_ratios.std()
            pct_sharpe_positivo = (sharpe_ratios > 0).sum() / len(sharpe_ratios) * 100
            stability_factor = sharpe_medio / (sharpe_std + 1e-6)

            return {
                'Ticker': ticker,
                'Best BB Dev': best_param_dev,
                'Sharpe Medio': sharpe_medio,
                'Sharpe Std Dev': sharpe_std,
                'Pct Parametros Positivos (%)': pct_sharpe_positivo,
                'Fator de Estabilidade': stability_factor,
                'Num Parametros Testados': len(sharpe_ratios)
            }
    except Exception as e:
        logger.error(f"Falha na análise de estabilidade de {ticker}: {e}", exc_info=False)
    
    return None

if __name__ == "__main__":
    tickers = get_expanded_universe()
    todos_resultados = []

    logger.info(f"--- INICIANDO ANÁLISE DE ESTABILIDADE E OTIMIZAÇÃO PARA {len(tickers)} ATIVOS ---")
    
    with concurrent.futures.ProcessPoolExecutor(max_workers=os.cpu_count()) as executor:
        future_to_ticker = {executor.submit(process_single_ticker_stability, ticker): ticker for ticker in tickers}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_ticker), total=len(tickers), desc="Gerando Ranking de Estabilidade"):
            resultado = future.result()
            if resultado:
                todos_resultados.append(resultado)

    logger.info(f"Análise concluída. {len(todos_resultados)} ativos tiveram resultados.")

    if todos_resultados:
        df_report = pd.DataFrame(todos_resultados)
        
        print("\n\n" + "="*80)
        print("          🏆 TOP 10 ATIVOS POR ESTABILIDADE (Fator de Estabilidade)")
        print("="*80)
        df_top_estaveis = df_report.sort_values(by='Fator de Estabilidade', ascending=False).head(10)
        print(df_top_estaveis.to_string(index=False))
        
        print("\n\n" + "="*80)
        print("          👍 TOP 10 ATIVOS POR PARÂMETRO ÓTIMO (Melhor Sharpe)")
        print("="*80)
        df_top_sharpe = df_report.sort_values(by='Sharpe Medio', ascending=False).head(10)
        print(df_top_sharpe.to_string(index=False))
        print("="*80)

        # --- EXPORTAÇÃO DO RELATÓRIO DE HANDOVER ---
        try:
            report_dir = 'data/reports'
            os.makedirs(report_dir, exist_ok=True)
            report_path = os.path.join(report_dir, 'professional_stability_ranking.csv')
            
            df_report_sorted = df_report.sort_values(by='Fator de Estabilidade', ascending=False)
            # Aumentar precisão para garantir que o robô leia o valor exato do desvio
            df_report_sorted.to_csv(report_path, index=False, float_format='%.4f') 
            
            logger.info(f"Relatório de handover com {len(df_report)} ativos salvo em: {report_path}")
        except Exception as e:
            logger.error(f"Falha ao salvar o relatório de handover: {e}")

    else:
        logger.warning("Nenhuma análise produziu resultados para gerar um relatório.")
