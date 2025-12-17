# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import argparse
import logging
import pandas as pd
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from co_piloto_quant.strategies.adaptive_regime_momentum import AdaptiveRegimeMomentumStrategy

ML_READY_PATH = "src/co_piloto_quant/data/ml_ready"
CUSTO_TOTAL_TRADE = 0.0006
DEFAULT_WORKERS = 4
MIN_DATE = "2022-01-01"

logger = logging.getLogger("validate_momentum")

def setup_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler()
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(level)

def get_parquet_files(path: str = ML_READY_PATH):
    p = Path(path)
    if not p.exists():
        alt = Path("co_piloto_quant") / path
        if alt.exists():
            p = alt
        else:
            logger.error("Nao foi possivel encontrar: %s", path)
            return []
    files = sorted(p.glob("*_SA.parquet"))
    return files

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

def run_strategy_simulation(df: pd.DataFrame, strategy, ticker: str) -> pd.DataFrame:
    try:
        df_eval = strategy.evaluate(df.copy(), ticker)
    except Exception as e:
        logger.warning('Erro ao avaliar %s: %s', ticker, e)
        return pd.DataFrame()
    
    if 'SIGNAL' not in df_eval.columns:
        return pd.DataFrame()
    
    df_eval['SIGNAL'] = df_eval['SIGNAL'].astype(str)
    
    closes = df_eval['close'].values
    dates = df_eval.index
    signals = df_eval['SIGNAL'].values
    
    lows = df_eval['low'].values if 'low' in df_eval.columns else closes
    highs = df_eval['high'].values if 'high' in df_eval.columns else closes
    
    trades = []
    in_trade = False
    entry_price = 0.0
    entry_date = None
    stop_loss = 0.0
    profit_target = 0.0
    days_held = 0
    
    MAX_HARD_STOP = 0.10
    MAX_DAYS = 15
    
    for i in range(1, len(df_eval)):
        sig = signals[i]
        
        if not in_trade and sig in ['BUY', 'SELL']:
            in_trade = True
            entry_price = float(closes[i])
            entry_date = dates[i]
            days_held = 0
            
            if 'STOP_LOSS' in df_eval.columns and pd.notna(df_eval['STOP_LOSS'].iloc[i]):
                stop_loss = float(df_eval['STOP_LOSS'].iloc[i])
            else:
                stop_loss = entry_price * (0.95 if sig == 'BUY' else 1.05)
            
            if 'PROFIT_TARGET' in df_eval.columns and pd.notna(df_eval['PROFIT_TARGET'].iloc[i]):
                profit_target = float(df_eval['PROFIT_TARGET'].iloc[i])
            else:
                profit_target = entry_price * (1.03 if sig == 'BUY' else 0.97)
            
            signal_type = sig
        
        elif in_trade:
            current_close = float(closes[i])
            current_low = float(lows[i])
            current_high = float(highs[i])
            days_held += 1
            
            exit_triggered = False
            exit_price = 0.0
            exit_reason = ''
            
            if signal_type == 'BUY':
                if current_low <= stop_loss:
                    exit_triggered = True
                    exit_price = stop_loss
                    exit_reason = 'STOP_LOSS' if abs(exit_price - stop_loss) < 0.01 else 'HARD_STOP'
                elif current_high >= profit_target:
                    exit_triggered = True
                    exit_price = profit_target
                    exit_reason = 'PROFIT_TARGET'
            else:
                if current_high >= stop_loss:
                    exit_triggered = True
                    exit_price = stop_loss
                    exit_reason = 'STOP_LOSS' if abs(exit_price - stop_loss) < 0.01 else 'HARD_STOP'
                elif current_low <= profit_target:
                    exit_triggered = True
                    exit_price = profit_target
                    exit_reason = 'PROFIT_TARGET'
            
            if not exit_triggered and days_held >= MAX_DAYS:
                exit_triggered = True
                exit_price = current_close
                exit_reason = 'MAX_DAYS'
            
            if exit_triggered:
                ret = (exit_price - entry_price) / entry_price if signal_type == 'BUY' else (entry_price - exit_price) / entry_price
                ret -= CUSTO_TOTAL_TRADE
                
                trades.append({
                    'ticker': ticker,
                    'regime': df_eval['REGIME'].iloc[i] if 'REGIME' in df_eval.columns else 'UNKNOWN',
                    'return': ret,
                    'win': 1 if ret > 0 else 0,
                    'reason': exit_reason,
                    'days': days_held,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'atr': df_eval['ATR'].iloc[i] if 'ATR' in df_eval.columns else 0,
                })
                
                in_trade = False
    
    if trades:
        return pd.DataFrame(trades)
    return pd.DataFrame()

def process_file_in_window(file_path, strategy, train_start, train_end, test_start, test_end):
    try:
        df = pd.read_parquet(file_path)
        if 'data_pregao' in df.columns:
            df['data_pregao'] = pd.to_datetime(df['data_pregao'])
            df = df.set_index('data_pregao')
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        
        df = classify_regimes(df)
        ticker = file_path.stem.replace('_SA', '')
        
        df_train = df[(df.index >= train_start) & (df.index <= train_end)].copy()
        df_test = df[(df.index >= test_start) & (df.index <= test_end)].copy()
        
        trades_train = pd.DataFrame()
        trades_test = pd.DataFrame()
        
        if not df_train.empty:
            trades_train = run_strategy_simulation(df_train, strategy, ticker)
            if not trades_train.empty:
                trades_train['phase'] = 'TRAIN'
        
        if not df_test.empty:
            trades_test = run_strategy_simulation(df_test, strategy, ticker)
            if not trades_test.empty:
                trades_test['phase'] = 'TEST'
        
        return trades_train, trades_test
    
    except Exception as e:
        logger.exception('Erro em %s: %s', file_path.name, e)
        return pd.DataFrame(), pd.DataFrame()

def main():
    setup_logging()
    
    parser = argparse.ArgumentParser(description='Validacao AdaptiveRegimeMomentumStrategy')
    parser.add_argument('--ema-fast', type=int, default=12)
    parser.add_argument('--ema-slow', type=int, default=26)
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    parser.add_argument('--out', type=str, default='momentum_all_regimes_results.csv')
    args = parser.parse_args()
    
    strategy = AdaptiveRegimeMomentumStrategy(
        ema_fast=args.ema_fast,
        ema_slow=args.ema_slow,
        atr_period=14,
        atr_stop_multiplier=2.0,
        max_hold_calm=15,
        max_hold_volatile=7
    )
    
    logger.info('Estrategia: %s', strategy.get_name())
    logger.info('Validacao: Walk-forward 12m treino + 3m teste (2022-2025, TODOS REGIMES)')
    
    files = get_parquet_files()
    if not files:
        logger.error("Nenhum arquivo encontrado")
        return
    
    logger.info('Determinando periodos disponiveis...')
    df_sample = pd.read_parquet(files[0])
    if 'data_pregao' in df_sample.columns:
        all_dates = pd.to_datetime(df_sample['data_pregao'])
    else:
        all_dates = pd.to_datetime(df_sample.index, errors='coerce')
    
    min_date = max(pd.Timestamp(all_dates.min()), pd.Timestamp(MIN_DATE))
    max_date = pd.Timestamp(all_dates.max())
    logger.info('Periodo: %s a %s', min_date.date(), max_date.date())
    
    windows = []
    current = min_date
    
    while True:
        train_end = current + pd.DateOffset(months=12)
        test_end = train_end + pd.DateOffset(months=3)
        test_start = train_end + pd.Timedelta(days=1)
        
        if test_end > max_date:
            break
        
        windows.append({
            'name': f"{current.strftime('%Y-%m')}",
            'train_start': pd.Timestamp(current),
            'train_end': pd.Timestamp(train_end),
            'test_start': pd.Timestamp(test_start),
            'test_end': pd.Timestamp(test_end)
        })
        
        current = current + pd.DateOffset(months=3)
    
    logger.info('Geradas %d janelas (12m treino + 3m teste)', len(windows))
    
    all_trades = []
    
    for w_idx, window in enumerate(windows, 1):
        logger.info(f'\n[{w_idx}/{len(windows)}] Janela: {window["name"]}')
        logger.info(f'  Treino (12m): {window["train_start"].date()} a {window["train_end"].date()}')
        logger.info(f'  Teste (3m):   {window["test_start"].date()} a {window["test_end"].date()}')
        
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(process_file_in_window, fp, strategy, 
                                window['train_start'], window['train_end'], 
                                window['test_start'], window['test_end']): fp for fp in files}
            
            for f in tqdm(as_completed(futures), total=len(futures), desc=f'Janela {window["name"]}'):
                trades_train, trades_test = f.result()
                if isinstance(trades_train, pd.DataFrame) and not trades_train.empty:
                    trades_train['window'] = window['name']
                    all_trades.append(trades_train)
                if isinstance(trades_test, pd.DataFrame) and not trades_test.empty:
                    trades_test['window'] = window['name']
                    all_trades.append(trades_test)
    
    if all_trades:
        final_df = pd.concat(all_trades, ignore_index=True)
        
        print('\n' + '=' * 80)
        print('VALIDACAO: ADAPTIVE REGIME MOMENTUM (2022-2025, TODOS REGIMES)')
        print('=' * 80)
        
        print('\n[RESUMO GERAL]:')
        for phase in ['TRAIN', 'TEST']:
            phase_df = final_df[final_df['phase'] == phase]
            if not phase_df.empty:
                avg = phase_df['return'].mean()
                wr = (phase_df['return'] > 0).mean()
                cnt = len(phase_df)
                
                gains = phase_df[phase_df['return'] > 0]['return'].sum()
                losses = abs(phase_df[phase_df['return'] < 0]['return'].sum())
                pf = gains / losses if losses > 0 else 0
                
                print(f'  {phase:6} | {cnt:4} trades | {avg:8.4f} ret | {wr:6.1%} WR | PF: {pf:.2f}x')
        
        print('\n[PERFORMANCE POR REGIME]:')
        for regime in sorted(final_df['regime'].unique()):
            if pd.isna(regime):
                continue
            regime_df = final_df[final_df['regime'] == regime]
            train_df = regime_df[regime_df['phase'] == 'TRAIN']
            test_df = regime_df[regime_df['phase'] == 'TEST']
            
            if not train_df.empty and not test_df.empty:
                train_ret = train_df['return'].mean()
                test_ret = test_df['return'].mean()
                train_wr = (train_df['return'] > 0).mean()
                test_wr = (test_df['return'] > 0).mean()
                
                deg = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
                
                print(f'  {regime:15} | Train: {train_ret:+.4f} ({train_wr:.0%}) | Test: {test_ret:+.4f} ({test_wr:.0%}) | Deg: {deg:+.0f}%')
        
        final_df.to_csv(args.out, index=False)
        logger.info('Resultados salvos em %s', args.out)
    else:
        logger.warning('Nenhum trade gerado')

if __name__ == '__main__':
    main()
