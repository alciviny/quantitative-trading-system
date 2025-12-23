#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward_validation.py
Walk-Forward Testing: Valida consistência da estratégia
Treino: 6 meses | Teste: 3 meses (sem retreinar parâmetros)
Desliza mensalmente para frente
"""

from __future__ import annotations

import argparse
import logging
import threading
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    from scipy.stats import median_abs_deviation
except ImportError:
    try:
        from scipy.stats import median_absolute_deviation as median_abs_deviation
    except ImportError:
        median_abs_deviation = None

from co_piloto_quant.strategies.signal_engine import SignalEngine
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.data.data_manager import data_manager

ML_READY_PATH = "src/co_piloto_quant/data/ml_ready"
CUSTO_TOTAL_TRADE = 0.0006
DEFAULT_WORKERS = 4

logger = logging.getLogger("walk_forward")

_contaminated_lock = threading.Lock()
_contaminated: List[Dict[str, int]] = []


def get_parquet_files(path: str = ML_READY_PATH) -> List[Path]:
    p = Path(path)
    if not p.exists():
        alt = Path("co_piloto_quant") / path
        if alt.exists():
            p = alt
        else:
            logger.error("Não foi possível encontrar o diretório: %s", path)
            return []

    files = sorted(p.glob("*_SA.parquet"))
    return files


def apply_sanity_check(df: pd.DataFrame, ticker: Optional[str] = None) -> Tuple[pd.DataFrame, int]:
    df = df.copy()

    if df.empty or 'close' not in df.columns:
        return df, 0

    rets = df['close'].pct_change()
    q99 = rets.abs().quantile(0.999)
    limiar = max(0.20, float(q99))

    try:
        atr_like = df['close'].pct_change().rolling(14, min_periods=1).std() * np.sqrt(14)
        atr_thresh = (atr_like.mean() * 5).fillna(limiar)
    except Exception:
        atr_thresh = pd.Series(limiar, index=df.index)

    suspect_mask = (rets.abs() > limiar) | (rets.abs() > atr_thresh)

    n_suspects = int(suspect_mask.sum())
    if n_suspects > 0:
        logger.warning("Sanity Check [%s]: %d dias suspeitos", ticker or "unknown", n_suspects)
        df.loc[suspect_mask, 'close'] = np.nan
        # CRITICAL: Only ffill used to prevent lookahead bias
        df['close'] = df['close'].ffill()
        df.dropna(subset=['close'], inplace=True)

        with _contaminated_lock:
            _contaminated.append({'ticker': ticker or 'unknown', 'suspects': n_suspects})

    return df, n_suspects


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(level)


def _calculate_rolling_vol_of_vol(price_series: pd.Series, window: int = 20) -> pd.Series:
    if median_abs_deviation is None:
        return pd.Series(0.0, index=price_series.index)
        
    returns = price_series.pct_change()
    vol = returns.rolling(window).std()
    vol_diff = vol.diff()
    vol_vol = vol_diff.rolling(window).apply(lambda x: median_abs_deviation(x[~np.isnan(x)], scale='normal'), raw=False)
    return vol_vol


def calculate_missing_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    close_s = df['close'].ffill()

    # --- Hurst ---
    try:
        hurst_window = 72
        hurst_col_name = IndicatorNames.hurst_z(hurst_window)
        hurst_series = calculate_rolling_hurst(close_s, window=hurst_window, kind='returns')
        hurst_series = hurst_series.replace([np.inf, -np.inf], np.nan)
        rolling_mean_h = hurst_series.rolling(252, min_periods=1).mean()
        rolling_std_h = hurst_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df[hurst_col_name] = ((hurst_series - rolling_mean_h) / rolling_std_h).fillna(0.5)
    except Exception:
        df[IndicatorNames.hurst_z(72)] = 0.5

    # --- Entropy ---
    try:
        entropy_window = 20
        entropy_col_name = IndicatorNames.entropy_z(entropy_window)
        entropy_series = calculate_rolling_entropy(close_s, window=entropy_window)
        entropy_series = entropy_series.replace([np.inf, -np.inf], np.nan)
        
        rolling_mean_e = entropy_series.rolling(252, min_periods=1).mean()
        rolling_std_e = entropy_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df[entropy_col_name] = ((entropy_series - rolling_mean_e) / rolling_std_e).fillna(0.5)
    except Exception:
        df[IndicatorNames.entropy_z(20)] = 0.5
        
    # --- Volatility of Volatility ---
    # COMENTADO PARA ACELERAR: Cálculo lento e não usado pela estratégia DynamicMR.
    # try:
    #     vol_vol_series = _calculate_rolling_vol_of_vol(close_s, window=20)
    #     vol_vol_series = vol_vol_series.replace([np.inf, -np.inf], np.nan)
    #     rolling_mean_v = vol_vol_series.rolling(252, min_periods=1).mean()
    #     rolling_std_v = vol_vol_series.rolling(252, min_periods=1).std().replace(0, np.nan)
    #     df['VolVol_Z'] = ((vol_vol_series - rolling_mean_v) / rolling_std_v).fillna(0.0)
    # except Exception:
    df['VolVol_Z'] = 0.0  # Deixado para não quebrar dependências futuras


    return df


def classify_regimes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df['mm200_lab'] = df['close'].rolling(200, min_periods=1).mean()
    df['trend_signal'] = np.where(df['close'] > df['mm200_lab'], 'BULL', 'BEAR')

    distancia_mm = (df['close'] - df['mm200_lab']).abs() / df['mm200_lab']
    df.loc[distancia_mm < 0.03, 'trend_signal'] = 'SIDEWAYS'

    df['vol_20_lab'] = df['close'].rolling(20, min_periods=1).std() / df['close']
    vol_threshold = df['vol_20_lab'].rolling(252, min_periods=1).quantile(0.70)
    df['vol_signal'] = np.where(df['vol_20_lab'] > vol_threshold, 'VOLATILE', 'CALM')

    df['REGIME'] = df['trend_signal'] + '_' + df['vol_signal']
    return df


def _build_rename_map(columns: List[str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    upper_cols = {c.upper(): c for c in columns}

    # Explicitly find and rename Bollinger Bands to match IndicatorNames convention
    for upper, orig in upper_cols.items():
        if 'BB_LOWER' in upper:
            # This assumes the strategy is using the default parameters (20, 2.0)
            rename_map[orig] = IndicatorNames.bollinger_lower(20, 2.0)
        elif 'BB_MID' in upper:  # Catches BB_MID and BB_MIDDLE
            rename_map[orig] = IndicatorNames.bollinger_middle(20)

    # Handle other known indicators
    known = {'IFR_120': 'rsi_120', 'WWMA_200': 'wwma_200', 'STOCH_K_20_3': 'stoch_k_20_3'}
    for k, v in known.items():
        if k in upper_cols:
            rename_map[upper_cols[k]] = v

    return rename_map


def run_strategy_simulation(df: pd.DataFrame, bb_dev: float, vol_max: float, bb_exit_std_dev: float, ticker: str, close_open_trades: bool = True) -> pd.DataFrame:
    df = df.copy().sort_index()
    df = df.loc[~df.index.duplicated(keep='last')]
    try:
        df_eval = strategy.evaluate(df.copy(), ticker)
    except Exception as e:
        logger.warning('Erro ao avaliar estratégia %s: %s', ticker, e)
        return pd.DataFrame()

    if 'SIGNAL' not in df_eval.columns:
        return pd.DataFrame()

    df_eval['SIGNAL'] = df_eval['SIGNAL'].astype(str)

    closes = df_eval['close'].values
    dates = df_eval.index
    signals = df_eval['SIGNAL'].values
    regimes = df_eval['REGIME'].values if 'REGIME' in df_eval.columns else np.full(len(df_eval), '')
    
    lows = df_eval['low'].values if 'low' in df_eval.columns else closes

    rsi_vals = np.full(len(df_eval), 50.0)
    bb_mid_vals = np.full(len(df_eval), 0.0)
    hurst_vals = np.full(len(df_eval), 0.5)
    entropy_vals = np.full(len(df_eval), 0.0)
    half_life_vals = np.full(len(df_eval), 0.0)

    for c in df_eval.columns:
        if 'rsi' in c.lower(): rsi_vals = df_eval[c].fillna(50).values; break
    for c in df_eval.columns:
        if 'bb_middle' in c.lower(): bb_mid_vals = df_eval[c].fillna(0).values; break
    for c in df_eval.columns:
        if 'hurst' in c.lower() and 'z' in c.lower(): hurst_vals = df_eval[c].fillna(0.5).values; break
    for c in df_eval.columns:
        if 'entropy' in c.lower() and 'z' in c.lower(): entropy_vals = df_eval[c].fillna(0.0).values; break
    
    for c in ['half_life', 'half_life_60', 'HalfLife_60']:
        if c in df_eval.columns:
            half_life_vals = df_eval[c].fillna(0).values
            break

    has_stop = 'STOP_LOSS' in df_eval.columns
    stops_col = df_eval['STOP_LOSS'].values if has_stop else np.full(len(df_eval), np.nan)

    trades = []
    in_trade = False
    
    entry_price = 0.0
    entry_date = None
    entry_idx = 0
    entry_regime = ''
    current_technical_stop = 0.0
    cooldown_until = None
    highest_price = 0.0

    MAX_HARD_STOP = 0.05
    MAX_DAYS_IN_LOSS = 10

    for i in range(1, len(df_eval)):
        sig = signals[i]
        today_regime = regimes[i]

        if not in_trade and sig == 'BUY':
            
            if cooldown_until and dates[i] < cooldown_until:
                continue
            
            in_trade = True
            entry_price = float(closes[i])
            entry_date = dates[i]
            entry_idx = i
            entry_regime = today_regime
            highest_price = entry_price
            
            if has_stop and not np.isnan(stops_col[i]):
                current_technical_stop = float(stops_col[i])
            else:
                current_technical_stop = 0.0

        elif in_trade:
            exit_price = 0.0
            reason = ''
            triggered = False
            
            current_close = float(closes[i])
            current_low = float(lows[i])
            days_held = (dates[i] - entry_date).days
            
            highest_price = max(highest_price, current_close)
            
            if highest_price >= entry_price * 1.08:
                current_technical_stop = max(current_technical_stop, entry_price * 1.01)
            
            hard_stop_price = entry_price * (1 - MAX_HARD_STOP)
            
            if not triggered and current_low <= hard_stop_price:
                exit_price = min(hard_stop_price, current_close)
                reason = 'HARD_STOP'
                triggered = True

            elif not triggered and current_technical_stop > 0 and current_low <= current_technical_stop:
                exit_price = min(current_technical_stop, current_close)
                reason = 'STOP_TECNICO'
                triggered = True

            elif not triggered and days_held > MAX_DAYS_IN_LOSS and current_close < entry_price:
                exit_price = current_close
                reason = 'TIME_STOP'
                triggered = True

            elif not triggered and 'BEAR' in entry_regime:
                if (rsi_vals[i] > 50) or (bb_mid_vals[i] > 0 and current_close >= bb_mid_vals[i]):
                    exit_price = current_close
                    reason = 'BEAR_OPTIMIZED'
                    triggered = True

            elif not triggered and sig == 'SELL':
                exit_price = current_close
                reason = 'SIGNAL'
                triggered = True

            if triggered:
                raw_ret = (exit_price / entry_price) - 1
                net_ret = raw_ret - (CUSTO_TOTAL_TRADE * 2)

                trades.append({
                    'ticker': ticker,
                    'regime': entry_regime,
                    'return': net_ret,
                    'win': 1 if net_ret > 0 else 0,
                    'reason': reason,
                    'days_held': days_held,
                    'date_entry': entry_date,
                    'date_exit': dates[i],
                    'hurst_entrada': float(hurst_vals[entry_idx]),
                    'entropy_entrada': float(entropy_vals[entry_idx]),
                    'halflife_entrada': float(half_life_vals[entry_idx]),
                    'sinal_tipo': 'PRICE'
                })
                
                if net_ret < 0:
                    cooldown_until = dates[i] + pd.Timedelta(days=5)
                
                in_trade = False

    if in_trade and close_open_trades:
        exit_price = float(closes[-1])
        raw_ret = (exit_price / entry_price) - 1
        net_ret = raw_ret - (CUSTO_TOTAL_TRADE * 2)
        trades.append({
            'ticker': ticker,
            'regime': entry_regime,
            'return': net_ret,
            'win': 1 if net_ret > 0 else 0,
            'reason': 'END_CLOSED',
            'days_held': (dates[-1] - entry_date).days,
            'date_entry': entry_date,
            'date_exit': dates[-1],
            'hurst_entrada': float(hurst_vals[entry_idx]),
            'entropy_entrada': float(entropy_vals[entry_idx]),
            'halflife_entrada': float(half_life_vals[entry_idx]),
            'sinal_tipo': 'PRICE'
        })

    return pd.DataFrame(trades)


def process_file_window(file_path: Path, bb_dev: float, vol_max: float, bb_exit_std_dev: float, df_train: pd.DataFrame, df_test: pd.DataFrame, 
                       window_name: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Processa um arquivo para treino E teste em uma janela específica"""
    try:
        ticker = file_path.stem.replace('_', '.')
        full_df = pd.read_parquet(file_path)

        if 'data_pregao' in full_df.columns:
            full_df.index = pd.to_datetime(full_df['data_pregao'])
        else:
            full_df.index = pd.to_datetime(full_df.index, errors='coerce')
        full_df = full_df.sort_index()

        # Sanity check
        full_df, n_suspects = apply_sanity_check(full_df, ticker=ticker)

        rename_map = _build_rename_map(list(full_df.columns))
        if rename_map:
            full_df.rename(columns=rename_map, inplace=True)

        # Remove colunas duplicadas geradas pela renomeação imprecisa
        full_df = full_df.loc[:, ~full_df.columns.duplicated()]

        full_df = calculate_missing_indicators(full_df)
        full_df = classify_regimes(full_df)
        full_df['REGIME'] = full_df['REGIME'].astype(str)

        # Explicitly align all columns to the main index to prevent alignment errors.
        # This can happen if indicators loaded from files have slightly different date ranges.
        main_index = full_df.index
        for col in full_df.columns:
            if not full_df[col].index.equals(main_index):
                full_df[col] = full_df[col].reindex(main_index)

        # ===============================
        # FINAL ALIGNMENT + SANITIZATION
        # ===============================
        full_df = full_df.sort_index()

        # Mantém apenas linhas completas para colunas críticas
        critical_cols = ['close']
        critical_cols += [c for c in full_df.columns if 'bb_' in c.lower()]
        critical_cols += [c for c in full_df.columns if 'hurst' in c.lower()]
        critical_cols += [c for c in full_df.columns if 'entropy' in c.lower()]

        critical_cols = list(set(critical_cols))

        full_df = full_df.dropna(subset=critical_cols)


        # Filtra apenas os dados da janela de treino
        df_train_ticker = full_df[full_df.index >= df_train[0]]
        df_train_ticker = df_train_ticker[df_train_ticker.index <= df_train[-1]].copy()

        # Filtra apenas os dados da janela de treino
        df_train_ticker = full_df[full_df.index >= df_train[0]]
        df_train_ticker = df_train_ticker[df_train_ticker.index <= df_train[-1]].copy()

        trades_train = pd.DataFrame()
        trades_test = pd.DataFrame()

        if not df_train_ticker.empty:
            trades_train = run_strategy_simulation(df_train_ticker, strategy, ticker, close_open_trades=True)
            if not trades_train.empty:
                trades_train['phase'] = 'TRAIN'
                trades_train['window'] = window_name

        # --- Lógica de Teste com Período de Warm-up ---
        # Garante que a estratégia tenha dados suficientes (ex: 252 dias de lookback)
        # antes do início real do período de teste.
        warmup_days = 300  # Buffer de segurança para lookbacks (ex: 252 dias)
        start_date_with_warmup = df_test[0] - pd.Timedelta(days=warmup_days)

        # Filtra o dataframe para incluir o período de warm-up + teste
        df_test_ticker_raw = full_df[full_df.index >= start_date_with_warmup]
        df_test_ticker_raw = df_test_ticker_raw[df_test_ticker_raw.index <= df_test[-1]].copy()

        if not df_test_ticker_raw.empty:
            # Roda a simulação no dataframe estendido (com warm-up)
            trades_test_raw = run_strategy_simulation(df_test_ticker_raw, strategy, ticker, close_open_trades=True)
            
            # Filtra APENAS os trades que ocorreram dentro da janela de teste oficial
            if not trades_test_raw.empty:
                trades_test = trades_test_raw[trades_test_raw['date_entry'] >= df_test[0]].copy()
                if not trades_test.empty:
                    trades_test['phase'] = 'TEST'
                    trades_test['window'] = window_name

        return trades_train, trades_test

    except Exception as e:
        logger.exception('Erro processando %s na janela %s: %s', file_path.name, window_name, e)
        return pd.DataFrame(), pd.DataFrame()


def get_date_windows(all_dates: pd.DatetimeIndex, train_months: int = 6, test_months: int = 3) -> List[Tuple[str, pd.DatetimeIndex, pd.DatetimeIndex]]:
    """Gera janelas de walk-forward (treino + teste)"""
    windows = []
    
    start_date = all_dates.min()
    end_date = all_dates.max()
    
    current_train_start = start_date
    
    while True:
        # Calcula fim do treino (6 meses depois)
        train_end = current_train_start + pd.DateOffset(months=train_months)
        
        # Calcula fim do teste (3 meses depois)
        test_end = train_end + pd.DateOffset(months=test_months)
        
        if test_end > end_date:
            break
        
        # Filtra datas da janela
        train_idx = all_dates[(all_dates >= current_train_start) & (all_dates <= train_end)]
        test_idx = all_dates[(all_dates > train_end) & (all_dates <= test_end)]
        
        if len(train_idx) > 0 and len(test_idx) > 0:
            window_name = f"{current_train_start.strftime('%Y-%m-%d')}_{train_end.strftime('%Y-%m-%d')}"
            windows.append((window_name, train_idx, test_idx))
        
        # Avança 1 mês
        current_train_start = current_train_start + pd.DateOffset(months=1)
    
    return windows


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Walk-Forward Validation')
    
    parser.add_argument('--bb-dev', type=float, default=0.5,
                        help='Standard deviation multiplier for Kalman Bands (entry).')
    parser.add_argument('--vol-max', type=float, default=1.5,
                        help='Maximum volatility ratio for entry.')
    parser.add_argument('--bb-exit-std-dev', type=float, default=2.0,
                        help='Standard deviation multiplier for Kalman Bands (exit).')
    parser.add_argument('--out', type=str, default=None)
    parser.add_argument('--workers', type=int, default=8)

    args = parser.parse_args()
    files = get_parquet_files()

    bb_dev = args.bb_dev
    vol_max = args.vol_max
    bb_exit_std_dev = args.bb_exit_std_dev

    # Ajuste de custos para "Realidade Institucional"
    global CUSTO_TOTAL_TRADE
    CUSTO_TOTAL_TRADE = 0.0012  # 0.12% total (Slippage + Taxas)

    logger.info(f'Estratégia: SignalEngine (BB_Dev={bb_dev}, Vol_Max={vol_max}, BB_Exit_Std_Dev={bb_exit_std_dev})')

    # Lê todos os dados para determinar as janelas
    logger.info('Lendo dados para determinar períodos disponíveis...')
    all_dates_list = []
    
    for file_path in files[:1]:  # Usa primeiro arquivo para determinar range
        try:
            df = pd.read_parquet(file_path)
            if 'data_pregao' in df.columns:
                dates = pd.to_datetime(df['data_pregao'])
            else:
                dates = pd.to_datetime(df.index, errors='coerce')
            all_dates_list.extend(dates.tolist())
        except:
            pass
    
    if not all_dates_list:
        logger.error('Não foi possível ler datas dos arquivos')
        return
    
    all_dates = pd.DatetimeIndex(sorted(set(all_dates_list)))
    logger.info('Período de dados: %s a %s (%d dias)', all_dates.min().date(), all_dates.max().date(), len(all_dates))
    
    # Gera janelas
    windows = get_date_windows(all_dates, train_months=6, test_months=3)
    logger.info('Geradas %d janelas de walk-forward', len(windows))

    all_trades = []
    
    for window_name, train_dates, test_dates in windows:
        logger.info(f'\n📊 Processando janela: {window_name}')
        logger.info(f'   Treino: {train_dates.min().date()} a {train_dates.max().date()} ({len(train_dates)} dias)')
        logger.info(f'   Teste:  {test_dates.min().date()} a {test_dates.max().date()} ({len(test_dates)} dias)')
        
        window_train_trades = []
        window_test_trades = []
        
        with ProcessPoolExecutor(max_workers=args.workers) as ex:
            futures = {}
            for fp in files:
                future = ex.submit(process_file_window, fp, bb_dev, vol_max, bb_exit_std_dev, train_dates, test_dates, window_name)
                futures[future] = fp
            
            for f in tqdm(as_completed(futures), total=len(futures), desc=f'Janela {window_name}'):
                train_trades, test_trades = f.result()
                if isinstance(train_trades, pd.DataFrame) and not train_trades.empty:
                    window_train_trades.append(train_trades)
                if isinstance(test_trades, pd.DataFrame) and not test_trades.empty:
                    window_test_trades.append(test_trades)
        
        if window_train_trades:
            all_trades.extend(window_train_trades)
        if window_test_trades:
            all_trades.extend(window_test_trades)

    if all_trades:
        final_df = pd.concat(all_trades, ignore_index=True)
        
        print('\n' + '=' * 70)
        print('🔄 WALK-FORWARD VALIDATION RESULTS')
        print('=' * 70)
        
        # Resumo por fase (TRAIN vs TEST)
        print('\n📈 PERFORMANCE POR FASE:')
        phase_stats = final_df.groupby('phase').agg({
            'return': ['count', 'mean', 'sum', 'std'],
            'win': 'mean'
        }).round(4)
        phase_stats.columns = ['Trades', 'Avg_Return', 'Total_Return', 'Std_Dev', 'Win_Rate']
        print(phase_stats)
        
        # Análise por janela
        print('\n🪟 PERFORMANCE POR JANELA (TREINO vs TESTE):')
        for window_name in final_df['window'].unique():
            window_data = final_df[final_df['window'] == window_name]
            
            train_data = window_data[window_data['phase'] == 'TRAIN']
            test_data = window_data[window_data['phase'] == 'TEST']
            
            print(f'\n  {window_name}:')
            if not train_data.empty:
                train_ret = train_data['return'].mean()
                train_wr = (train_data['return'] > 0).mean()
                train_trades = len(train_data)
                print(f'    Treino: {train_trades:>3} trades, {train_ret:>8.4f} avg_ret, {train_wr:>6.2%} win_rate')
            else:
                print(f'    Treino: sem trades')
            
            if not test_data.empty:
                test_ret = test_data['return'].mean()
                test_wr = (test_data['return'] > 0).mean()
                test_trades = len(test_data)
                degradation = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
                print(f'    Teste:  {test_trades:>3} trades, {test_ret:>8.4f} avg_ret, {test_wr:>6.2%} win_rate (degradação: {degradation:>6.1f}%)')
            else:
                print(f'    Teste:  sem trades')
        
        # Resumo de degradação
        print('\n⚠️ ANÁLISE DE CONSISTÊNCIA:')
        train_avg_ret = final_df[final_df['phase'] == 'TRAIN']['return'].mean()
        test_avg_ret = final_df[final_df['phase'] == 'TEST']['return'].mean()
        degradation_overall = ((test_avg_ret - train_avg_ret) / abs(train_avg_ret) * 100) if train_avg_ret != 0 else 0
        
        print(f'  Retorno Médio Treino:  {train_avg_ret:.4f}')
        print(f'  Retorno Médio Teste:   {test_avg_ret:.4f}')
        print(f'  Degradação Geral:      {degradation_overall:.2f}%')
        
        if abs(degradation_overall) < 20:
            print(f'  ✅ Sistema CONSISTENTE (degradação < 20%)')
        elif abs(degradation_overall) < 50:
            print(f'  ⚠️  Sistema com DEGRADAÇÃO MODERADA (20% < degradação < 50%)')
        else:
            print(f'  ❌ Sistema OVERFITTED (degradação > 50%)')
        
        # Salva resultados
        if args.out:
            out_path = Path(args.out)
        else:
            out_path = Path('walk_forward_results.csv')
        
        final_df.to_csv(out_path, index=False)
        logger.info('Resultados salvos em %s', out_path)
    else:
        logger.warning('Nenhum trade gerado.')


if __name__ == '__main__':
    main()
