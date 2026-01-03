#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_volatile_momentum.py
Testa VolatileMomentumProfessional no lab universal
"""

import argparse
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
import numpy as np
from tqdm import tqdm

from co_piloto_quant.strategies.volatile_momentum_professional import VolatileMomentumProfessional

ML_READY_PATH = "src/co_piloto_quant/data/ml_ready"
CUSTO_TOTAL_TRADE = 0.0006

logger = logging.getLogger("test_momentum")

def setup_logging():
    handler = logging.StreamHandler()
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    handler.setFormatter(logging.Formatter(fmt))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

def get_parquet_files(path: str = ML_READY_PATH):
    p = Path(path)
    if not p.exists():
        alt = Path("co_piloto_quant") / path
        if alt.exists():
            p = alt
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

def run_strategy_simulation(df: pd.DataFrame, strategy, ticker: str, target_regime: str = 'ALL') -> pd.DataFrame:
    try:
        df_eval = strategy.evaluate(df.copy(), ticker)
    except Exception as e:
        logger.warning(f'Erro ao avaliar {ticker}: {e}')
        return pd.DataFrame()
    
    if 'SIGNAL' not in df_eval.columns:
        return pd.DataFrame()
    
    df_eval['SIGNAL'] = df_eval['SIGNAL'].astype(str)
    
    closes = df_eval['close'].values
    dates = df_eval.index
    signals = df_eval['SIGNAL'].values
    regimes = df_eval['REGIME'].values if 'REGIME' in df_eval.columns else np.full(len(df_eval), '')
    lows = df_eval['low'].values if 'low' in df_eval.columns else closes
    
    has_stop = 'STOP_LOSS' in df_eval.columns
    has_profit = 'PROFIT_TARGET' in df_eval.columns
    stops_col = df_eval['STOP_LOSS'].values if has_stop else np.full(len(df_eval), np.nan)
    targets_col = df_eval['PROFIT_TARGET'].values if has_profit else np.full(len(df_eval), np.nan)
    
    trades = []
    in_trade = False
    entry_price = 0.0
    entry_date = None
    entry_regime = ''
    current_technical_stop = 0.0
    current_profit_target = 0.0
    
    for i in range(1, len(df_eval)):
        sig = signals[i]
        today_regime = regimes[i]
        
        if not in_trade and sig == 'BUY':
            if target_regime != 'ALL' and today_regime != target_regime:
                continue
            
            in_trade = True
            entry_price = float(closes[i])
            entry_date = dates[i]
            entry_regime = today_regime
            
            if has_stop and not np.isnan(stops_col[i]):
                current_technical_stop = float(stops_col[i])
            else:
                current_technical_stop = entry_price * 0.95
            
            if has_profit and not np.isnan(targets_col[i]):
                current_profit_target = float(targets_col[i])
            else:
                current_profit_target = entry_price * 1.05
        
        elif in_trade:
            current_close = float(closes[i])
            current_low = float(lows[i])
            days_held = (dates[i] - entry_date).days
            
            exit_price = 0.0
            reason = ''
            triggered = False
            
            # Profit Target
            if current_close >= current_profit_target:
                exit_price = current_profit_target
                reason = 'PROFIT_TARGET'
                triggered = True
            
            # Stop Loss
            elif current_low <= current_technical_stop:
                exit_price = min(current_technical_stop, current_close)
                reason = 'STOP_LOSS'
                triggered = True
            
            # Max Days
            elif days_held > 7:
                exit_price = current_close
                reason = 'MAX_DAYS'
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
                    'entry_price': entry_price,
                    'exit_price': exit_price
                })
                
                in_trade = False
    
    return pd.DataFrame(trades)

def process_file(file_path: Path, strategy, start_date: str, target_regime: str) -> pd.DataFrame:
    try:
        ticker = file_path.stem.replace('_', '.')
        df = pd.read_parquet(file_path)
        
        if 'data_pregao' in df.columns:
            df.index = pd.to_datetime(df['data_pregao'])
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        df = df.sort_index()
        
        df = df[df.index >= pd.to_datetime(start_date)].copy()
        if df.empty:
            return pd.DataFrame()
        
        df = classify_regimes(df)
        df['REGIME'] = df['REGIME'].astype(str)
        
        df_trades = run_strategy_simulation(df, strategy, ticker, target_regime=target_regime)
        
        if not df_trades.empty:
            logger.info(f'{ticker}: {len(df_trades)} trades')
        
        return df_trades
    
    except Exception as e:
        logger.exception(f'Erro processando {file_path.name}: {e}')
        return pd.DataFrame()

def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Test VolatileMomentumProfessional')
    parser.add_argument('--regime', type=str, default='BEAR_VOLATILE',
                        help='Regime (BULL_VOLATILE, BEAR_VOLATILE, ALL)')
    parser.add_argument('--start-date', type=str, default='2021-12-08')
    parser.add_argument('--workers', type=int, default=4)
    
    args = parser.parse_args()
    files = get_parquet_files()
    
    if not files:
        logger.error('Nenhum arquivo parquet encontrado!')
        return
    
    strategy = VolatileMomentumProfessional(
        ema_fast=12,
        ema_slow=26,
        atr_stop_multiplier=2.5,
        atr_profit_multiplier=3.0,
        target_regimes=['BULL_VOLATILE', 'BEAR_VOLATILE'] if args.regime == 'ALL' else [args.regime]
    )
    
    logger.info(f'Estratégia: {strategy.get_name()}')
    logger.info(f'Regime alvo: {args.regime}')
    logger.info(f'Arquivos para processar: {len(files)}')
    
    all_trades = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_file, fp, strategy, args.start_date, args.regime): fp for fp in files}
        for f in tqdm(as_completed(futures), total=len(futures), desc='Processando'):
            res = f.result()
            if isinstance(res, pd.DataFrame) and not res.empty:
                all_trades.append(res)
    
    if all_trades:
        final_df = pd.concat(all_trades, ignore_index=True)
        
        print('\n' + '='*70)
        print('RESULTADOS - VOLATILE MOMENTUM PROFESSIONAL')
        print('='*70)
        
        regime_stats = final_df.groupby('regime').agg({
            'return': ['count', 'mean', 'sum'],
            'win': 'mean',
            'days_held': 'mean'
        }).round(4)
        
        print('\nPOR REGIME:')
        print(regime_stats)
        
        # Métricas Globais
        ganhos = final_df[final_df['return'] > 0]['return'].sum()
        perdas = abs(final_df[final_df['return'] < 0]['return'].sum())
        pf = ganhos / perdas if perdas > 0 else 0
        
        print('\nMÉTRICAS GLOBAIS:')
        print(f'  Total Trades: {len(final_df)}')
        print(f'  Win Rate: {(final_df["win"].mean()*100):.1f}%')
        print(f'  Total Ganho: {ganhos*100:+.2f}%')
        print(f'  Total Perda: {perdas*100:+.2f}%')
        print(f'  Profit Factor: {pf:.2f}x')
        print(f'  Retorno Médio: {final_df["return"].mean()*100:+.2f}%')
        print(f'  Dias Médios em Trade: {final_df["days_held"].mean():.1f}')
        
        # Salvar resultados
        output_file = f'momentum_{args.regime}_results.csv'
        final_df.to_csv(output_file, index=False)
        logger.info(f'Resultados salvos em {output_file}')
    else:
        logger.warning(f'Nenhum trade gerado para {args.regime}')

if __name__ == '__main__':
    main()
