#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_swing_bear_calm.py
Validação da estratégia operando APENAS em BEAR_CALM
(melhores resultados observados no teste anterior)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Tuple

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

from co_piloto_quant.strategies.mean_reversion_swing import MeanReversionSwingStrategy

ML_READY_PATH = "src/co_piloto_quant/data/ml_ready"
CUSTO_TOTAL_TRADE = 0.0006
DEFAULT_WORKERS = 4
MIN_DATE = "2022-01-01"
TARGET_REGIME = "BEAR_CALM"

logger = logging.getLogger("validate_swing_bear")
_contaminated_lock = threading.Lock()
_contaminated: List[Dict[str, int]] = []


def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(level)


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
        df['close'] = df['close'].interpolate(method='linear').ffill().bfill()

        with _contaminated_lock:
            _contaminated.append({'ticker': ticker or 'unknown', 'suspects': n_suspects})

    return df, n_suspects


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


def run_strategy_simulation(df: pd.DataFrame, strategy, ticker: str, close_open_trades: bool = True, target_regime: str = None) -> pd.DataFrame:
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
    highs = df_eval['high'].values if 'high' in df_eval.columns else closes

    trades = []
    in_trade = False
    
    entry_price = 0.0
    entry_date = None
    entry_idx = 0
    entry_regime = ''
    days_in_trade = 0
    stop_loss = 0.0
    profit_target = 0.0

    MAX_HARD_STOP = 0.10
    MAX_DAYS = 10

    for i in range(1, len(df_eval)):
        sig = signals[i]
        today_regime = regimes[i]

        if not in_trade and sig == 'BUY':
            if target_regime and today_regime != target_regime:
                continue
            
            in_trade = True
            entry_price = float(closes[i])
            entry_date = dates[i]
            entry_idx = i
            entry_regime = today_regime
            days_in_trade = 0
            
            if 'STOP_LOSS' in df_eval.columns and pd.notna(df_eval['STOP_LOSS'].iloc[i]):
                stop_loss = float(df_eval['STOP_LOSS'].iloc[i])
            else:
                stop_loss = entry_price * 0.95
            
            if 'PROFIT_TARGET' in df_eval.columns and pd.notna(df_eval['PROFIT_TARGET'].iloc[i]):
                profit_target = float(df_eval['PROFIT_TARGET'].iloc[i])
            else:
                profit_target = entry_price * 1.03

        elif in_trade:
            current_close = float(closes[i])
            current_low = float(lows[i])
            current_high = float(highs[i])
            days_in_trade += 1
            
            triggered = False
            exit_price = 0.0
            reason = ''
            
            if current_high >= profit_target:
                exit_price = profit_target
                reason = 'PROFIT_TARGET'
                triggered = True
            
            elif current_low <= stop_loss:
                exit_price = stop_loss
                reason = 'STOP_LOSS'
                triggered = True
            
            elif days_in_trade >= MAX_DAYS:
                exit_price = current_close
                reason = 'MAX_DAYS'
                triggered = True
            
            elif current_low <= entry_price * (1 - MAX_HARD_STOP):
                exit_price = entry_price * (1 - MAX_HARD_STOP)
                reason = 'HARD_STOP'
                triggered = True
            
            elif sig == 'SELL':
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
                    'days_held': days_in_trade,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'stop_loss': stop_loss,
                    'sinal_tipo': 'PRICE'
                })
                
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
            'days_held': days_in_trade,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'stop_loss': stop_loss,
            'sinal_tipo': 'PRICE'
        })

    return pd.DataFrame(trades)


def process_file_in_window(file_path: Path, strategy, train_start, train_end, test_start, test_end, target_regime: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    try:
        ticker = file_path.stem.replace('_', '.')
        df = pd.read_parquet(file_path)

        if 'data_pregao' in df.columns:
            df.index = pd.to_datetime(df['data_pregao'])
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        df = df.sort_index()

        df, _ = apply_sanity_check(df, ticker=ticker)
        df = classify_regimes(df)
        df['REGIME'] = df['REGIME'].astype(str)

        train_start = pd.Timestamp(train_start)
        train_end = pd.Timestamp(train_end)
        test_start = pd.Timestamp(test_start)
        test_end = pd.Timestamp(test_end)
        
        df_train_ticker = df[(df.index >= train_start) & (df.index <= train_end)].copy()
        df_test_ticker = df[(df.index >= test_start) & (df.index <= test_end)].copy()

        trades_train = pd.DataFrame()
        trades_test = pd.DataFrame()

        if not df_train_ticker.empty:
            trades_train = run_strategy_simulation(df_train_ticker, strategy, ticker, close_open_trades=True, target_regime=target_regime)
            if not trades_train.empty:
                trades_train['phase'] = 'TRAIN'

        if not df_test_ticker.empty:
            trades_test = run_strategy_simulation(df_test_ticker, strategy, ticker, close_open_trades=True, target_regime=target_regime)
            if not trades_test.empty:
                trades_test['phase'] = 'TEST'

        return trades_train, trades_test

    except Exception as e:
        logger.exception('Erro processando %s: %s', file_path.name, e)
        return pd.DataFrame(), pd.DataFrame()


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Validação MeanReversionSwing BEAR_CALM only (2022-2025)')
    
    parser.add_argument('--bb-std', type=float, default=1.5)
    parser.add_argument('--rsi-period', type=int, default=40)
    parser.add_argument('--atr-mult', type=float, default=2.0)
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    parser.add_argument('--out', type=str, default='swing_bear_calm_results.csv')

    args = parser.parse_args()
    
    strategy = MeanReversionSwingStrategy(
        bb_std_dev=args.bb_std,
        rsi_period=args.rsi_period,
        atr_multiplier=args.atr_mult,
        max_days_hold=10,
        profit_target_multiple=2.0,
        use_regime_filter=True
    )

    logger.info('Estratégia: %s', strategy.get_name())
    logger.info('CONFIGURAÇÃO: 12 meses TREINO + 3 meses TESTE (2022-2025, BEAR_CALM ONLY)')

    files = get_parquet_files()
    if not files:
        logger.error("Nenhum arquivo encontrado")
        return

    logger.info('Determinando períodos disponíveis...')
    df_sample = pd.read_parquet(files[0])
    if 'data_pregao' in df_sample.columns:
        all_dates = pd.to_datetime(df_sample['data_pregao'])
    else:
        all_dates = pd.to_datetime(df_sample.index, errors='coerce')
    
    min_date = max(pd.Timestamp(all_dates.min()), pd.Timestamp(MIN_DATE))
    max_date = pd.Timestamp(all_dates.max())
    logger.info('Período: %s a %s', min_date.date(), max_date.date())
    
    windows = []
    current = min_date
    
    while True:
        train_end = current + pd.DateOffset(months=12)
        test_end = train_end + pd.DateOffset(months=3)
        test_start = train_end + pd.Timedelta(days=1)
        
        if test_end > max_date:
            break
        
        train_idx = all_dates[(all_dates >= current) & (all_dates <= train_end)]
        test_idx = all_dates[(all_dates > train_end) & (all_dates <= test_end)]
        
        if len(train_idx) > 0 and len(test_idx) > 0:
            windows.append({
                'name': f"{current.strftime('%Y-%m')}",
                'train_start': pd.Timestamp(current),
                'train_end': pd.Timestamp(train_end),
                'test_start': pd.Timestamp(test_start),
                'test_end': pd.Timestamp(test_end)
            })
        
        next_month = current.month + 3
        next_year = current.year + (next_month - 1) // 12
        next_month = (next_month - 1) % 12 + 1
        current = pd.Timestamp(year=next_year, month=next_month, day=current.day if current.day <= 28 else 28)
    
    logger.info('Geradas %d janelas (12m treino + 3m teste)', len(windows))

    all_trades = []
    
    for w_idx, window in enumerate(windows, 1):
        logger.info(f'\n[{w_idx}/{len(windows)}] Janela: {window["name"]}')
        logger.info(f'  Treino (12m): {window["train_start"].date()} a {window["train_end"].date()}')
        logger.info(f'  Teste (3m):   {window["test_start"].date()} a {window["test_end"].date()}')
        
        window_trades = []
        
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(process_file_in_window, fp, strategy, window['train_start'], window['train_end'], window['test_start'], window['test_end'], TARGET_REGIME): fp for fp in files}
            
            for f in tqdm(as_completed(futures), total=len(futures), desc=f'Janela {window["name"]}'):
                trades_train, trades_test = f.result()
                if isinstance(trades_train, pd.DataFrame) and not trades_train.empty:
                    trades_train['window'] = window['name']
                    window_trades.append(trades_train)
                if isinstance(trades_test, pd.DataFrame) and not trades_test.empty:
                    trades_test['window'] = window['name']
                    window_trades.append(trades_test)
        
        all_trades.extend(window_trades)

    if all_trades:
        final_df = pd.concat(all_trades, ignore_index=True)

        print('\n' + '=' * 70)
        print('VALIDACAO: MEAN REVERSION SWING (2022-2025, BEAR_CALM ONLY)')
        print('=' * 70)

        print('\n[PERFORMANCE POR FASE]:')
        for phase in ['TRAIN', 'TEST']:
            phase_df = final_df[final_df['phase'] == phase]
            if not phase_df.empty:
                avg = phase_df['return'].mean()
                wr = (phase_df['return'] > 0).mean()
                cnt = len(phase_df)
                std = phase_df['return'].std()
                
                gains = phase_df[phase_df['return'] > 0]['return'].sum()
                losses = abs(phase_df[phase_df['return'] < 0]['return'].sum())
                pf = gains / losses if losses > 0 else 0
                
                print(f'  {phase:6} | {cnt:4} trades | {avg:8.4f} ret | {wr:6.1%} WR | PF: {pf:.2f}x | std: {std:.4f}')

        train_avg = final_df[final_df['phase'] == 'TRAIN']['return'].mean()
        test_avg = final_df[final_df['phase'] == 'TEST']['return'].mean()
        
        if train_avg != 0:
            deg = ((test_avg - train_avg) / abs(train_avg)) * 100
        else:
            deg = 0

        print(f'\nDEGRADAÇÃO: {deg:.2f}%')
        
        if abs(deg) < 30:
            print('  [OK] CONSISTENTE')
        elif abs(deg) < 100:
            print('  [WARN] MODERADA')
        else:
            print('  [ERROR] OVERFITTED')

        print('\n[EXIT REASONS]:')
        reason_stats = final_df[final_df['phase'] == 'TRAIN'].groupby('reason').agg({
            'return': ['mean', 'count', lambda x: (x > 0).mean()]
        }).round(4)
        reason_stats.columns = ['AvgReturn', 'Count', 'WinRate']
        reason_stats = reason_stats.sort_values('AvgReturn', ascending=False)
        print(reason_stats)

        final_df.to_csv(args.out, index=False)
        logger.info('Resultados salvos em %s', args.out)
    else:
        logger.warning('Nenhum trade gerado')


if __name__ == '__main__':
    main()
