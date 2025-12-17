#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
walk_forward_from_stress.py
Replica o lab_universal_stress.py mas com walk-forward
Mesmos parâmetros, mesmas regras, mesmos regimes - apenas dividido em janelas
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

from co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy

ML_READY_PATH = "src/co_piloto_quant/data/ml_ready"
CUSTO_TOTAL_TRADE = 0.0006
DEFAULT_WORKERS = 4

logger = logging.getLogger("walk_forward_stress")
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
    close_s = df['close'].ffill().bfill()

    try:
        hurst_series = calculate_rolling_hurst(close_s, window=72, kind='returns')
        hurst_series = hurst_series.replace([np.inf, -np.inf], np.nan)
        rolling_mean_h = hurst_series.rolling(252, min_periods=1).mean()
        rolling_std_h = hurst_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['hurst_z_72_c'] = ((hurst_series - rolling_mean_h) / rolling_std_h).fillna(0.5)
    except Exception:
        df['hurst_z_72_c'] = 0.5

    try:
        entropy_series = calculate_rolling_entropy(close_s, window=20)
        entropy_series = entropy_series.replace([np.inf, -np.inf], np.nan)
        df['Entropy_20'] = entropy_series 
        
        rolling_mean_e = entropy_series.rolling(252, min_periods=1).mean()
        rolling_std_e = entropy_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['Entropy_Z'] = ((entropy_series - rolling_mean_e) / rolling_std_e).fillna(0.5)
    except Exception:
        df['Entropy_20'] = 0.0
        df['Entropy_Z'] = 0.5
        
    try:
        vol_vol_series = _calculate_rolling_vol_of_vol(close_s, window=20)
        vol_vol_series = vol_vol_series.replace([np.inf, -np.inf], np.nan)
        rolling_mean_v = vol_vol_series.rolling(252, min_periods=1).mean()
        rolling_std_v = vol_vol_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['VolVol_Z'] = ((vol_vol_series - rolling_mean_v) / rolling_std_v).fillna(0.0)
    except Exception:
        df['VolVol_Z'] = 0.0

    if 'entropy_z_20' in df.columns:
        df.rename(columns={'entropy_z_20': 'Entropy_Z'}, inplace=True)

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

    for upper, orig in upper_cols.items():
        if 'BB_' in upper:
            rename_map[orig] = orig.lower()

    known = {'IFR_120': 'rsi_120', 'WWMA_200': 'wwma_200', 'STOCH_K_20_3': 'stoch_k_20_3'}
    for k, v in known.items():
        if k in upper_cols:
            rename_map[upper_cols[k]] = v

    return rename_map


def run_strategy_simulation(df: pd.DataFrame, strategy, ticker: str, close_open_trades: bool = True) -> pd.DataFrame:
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
            'hurst_entrada': float(hurst_vals[entry_idx]),
            'entropy_entrada': float(entropy_vals[entry_idx]),
            'halflife_entrada': float(half_life_vals[entry_idx]),
            'sinal_tipo': 'PRICE'
        })

    return pd.DataFrame(trades)


def process_file_in_window(file_path: Path, strategy, train_start, train_end, test_start, test_end) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Processa um arquivo para treino E teste"""
    try:
        ticker = file_path.stem.replace('_', '.')
        df = pd.read_parquet(file_path)

        if 'data_pregao' in df.columns:
            df.index = pd.to_datetime(df['data_pregao'])
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        df = df.sort_index()

        df, n_suspects = apply_sanity_check(df, ticker=ticker)

        rename_map = _build_rename_map(list(df.columns))
        if rename_map:
            df.rename(columns=rename_map, inplace=True)

        df = calculate_missing_indicators(df)
        df = classify_regimes(df)
        df['REGIME'] = df['REGIME'].astype(str)

        # Converte para Timestamp se necessário
        train_start = pd.Timestamp(train_start)
        train_end = pd.Timestamp(train_end)
        test_start = pd.Timestamp(test_start)
        test_end = pd.Timestamp(test_end)
        
        # Filtra dados do período de treino
        df_train_ticker = df[(df.index >= train_start) & (df.index <= train_end)].copy()
        
        # Filtra dados do período de teste
        df_test_ticker = df[(df.index >= test_start) & (df.index <= test_end)].copy()

        trades_train = pd.DataFrame()
        trades_test = pd.DataFrame()

        if not df_train_ticker.empty:
            trades_train = run_strategy_simulation(df_train_ticker, strategy, ticker, close_open_trades=True)
            if not trades_train.empty:
                trades_train['phase'] = 'TRAIN'

        if not df_test_ticker.empty:
            trades_test = run_strategy_simulation(df_test_ticker, strategy, ticker, close_open_trades=True)
            if not trades_test.empty:
                trades_test['phase'] = 'TEST'

        return trades_train, trades_test

    except Exception as e:
        logger.exception('Erro processando %s: %s', file_path.name, e)
        return pd.DataFrame(), pd.DataFrame()


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Walk-Forward com mesmos parâmetros do stress test')
    
    parser.add_argument('--bb-std', type=float, default=1.5)
    parser.add_argument('--rsi-period', type=int, default=120)
    parser.add_argument('--bb-std-volatile', type=float, default=2.5)
    parser.add_argument('--max-half-life', type=int, default=25)
    parser.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    parser.add_argument('--out', type=str, default='walk_forward_results.csv')

    args = parser.parse_args()
    
    strategy = MeanReversionStrategy(
        bb_std_dev=args.bb_std, 
        rsi_period=args.rsi_period,
        bb_std_dev_volatile=args.bb_std_volatile,
        adaptive_rsi=True,
        adaptive_bb=True,
        use_regime_filter=True,
        max_half_life=args.max_half_life
    )

    logger.info('Estratégia: %s', strategy.get_name())

    files = get_parquet_files()
    if not files:
        logger.error("Nenhum arquivo encontrado")
        return

    # Determina períodos
    logger.info('Determinando períodos disponíveis...')
    df_sample = pd.read_parquet(files[0])
    if 'data_pregao' in df_sample.columns:
        all_dates = pd.to_datetime(df_sample['data_pregao'])
    else:
        all_dates = pd.to_datetime(df_sample.index, errors='coerce')
    
    min_date = pd.Timestamp(all_dates.min())
    max_date = pd.Timestamp(all_dates.max())
    logger.info('Período: %s a %s', min_date.date(), max_date.date())
    
    # Gera janelas
    windows = []
    current = pd.Timestamp(min_date)
    
    while True:
        # Adiciona 6 meses para treino
        year, month = current.year, current.month
        train_month = month + 6
        train_year = year + (train_month - 1) // 12
        train_month = (train_month - 1) % 12 + 1
        train_end = pd.Timestamp(year=train_year, month=train_month, day=1) - pd.Timedelta(days=1)
        
        # Calcula fim do teste (3 meses depois do treino)
        test_month = train_month + 3
        test_year = train_year + (test_month - 1) // 12
        test_month = (test_month - 1) % 12 + 1
        test_end = pd.Timestamp(year=test_year, month=test_month, day=1) - pd.Timedelta(days=1)
        
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
        
        # Avança 1 mês
        next_month = current.month + 1
        next_year = current.year + (next_month - 1) // 12
        next_month = (next_month - 1) % 12 + 1
        current = pd.Timestamp(year=next_year, month=next_month, day=current.day if current.day <= 28 else 28)
    
    logger.info('Geradas %d janelas', len(windows))

    all_trades = []
    
    for w_idx, window in enumerate(windows, 1):
        logger.info(f'\n[{w_idx}/{len(windows)}] Janela: {window["name"]}')
        logger.info(f'  Treino: {window["train_start"].date()} a {window["train_end"].date()}')
        logger.info(f'  Teste:  {window["test_start"].date()} a {window["test_end"].date()}')
        
        window_trades = []
        
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futures = {ex.submit(process_file_in_window, fp, strategy, window['train_start'], window['train_end'], window['test_start'], window['test_end']): fp for fp in files}
            
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
        print('🔄 WALK-FORWARD VALIDATION RESULTS')
        print('=' * 70)

        # Por fase
        print('\n📈 PERFORMANCE POR FASE:')
        for phase in ['TRAIN', 'TEST']:
            phase_df = final_df[final_df['phase'] == phase]
            if not phase_df.empty:
                avg = phase_df['return'].mean()
                wr = (phase_df['return'] > 0).mean()
                cnt = len(phase_df)
                print(f'  {phase:6} | {cnt:4} trades | {avg:8.4f} retorno | {wr:6.1%} win_rate')

        # Degradação
        train_avg = final_df[final_df['phase'] == 'TRAIN']['return'].mean()
        test_avg = final_df[final_df['phase'] == 'TEST']['return'].mean()
        
        if train_avg != 0:
            deg = ((test_avg - train_avg) / abs(train_avg)) * 100
        else:
            deg = 0

        print(f'\n⚠️  DEGRADAÇÃO GERAL: {deg:.2f}%')
        
        if abs(deg) < 20:
            print('  ✅ Sistema CONSISTENTE')
        elif abs(deg) < 50:
            print('  ⚠️  Degradação MODERADA')
        else:
            print('  ❌ Sistema OVERFITTED')

        # Salva
        final_df.to_csv(args.out, index=False)
        logger.info('Resultados salvos em %s', args.out)
    else:
        logger.warning('Nenhum trade gerado')


if __name__ == '__main__':
    main()
