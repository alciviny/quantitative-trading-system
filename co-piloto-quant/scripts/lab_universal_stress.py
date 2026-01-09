#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lab_universal_stress.py (Versão Multi-Regime)
Agora permite testar a estratégia em QUALQUER regime de mercado ou em TODOS simultaneamente.
Use: python lab_universal_stress.py --regime ALL
"""

from __future__ import annotations

import argparse
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
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

# Estratégias / indicadores
from co_piloto_quant.strategies.base import AdaptiveSniperStrategy
from co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy
from co_piloto_quant.strategies.volatile_momentum_professional import VolatileMomentumProfessional
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy

from co_piloto_quant.config import PROCESSED_DATA_PATH

# --------------------------- CONFIG ---------------------------
ML_READY_PATH = PROCESSED_DATA_PATH
START_DATE = "2021-12-08"
CUSTO_TOTAL_TRADE = 0.0006  # 0.06% round-trip
DEFAULT_WORKERS = 4

# --------------------------- LOG ---------------------------
logger = logging.getLogger("lab_stress")

# Contaminated tickers report (thread-safe)
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


# --------------------------- SANITY CHECK (ADAPTATIVE) ---------------------------
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
        logger.warning("Sanity Check [%s]: %d dias suspeitos (limiar=%.3f).",
                       ticker or "unknown", n_suspects, limiar)
        df.loc[suspect_mask, 'close'] = np.nan
        # CRITICAL: Only ffill used to prevent lookahead bias
        df['close'] = df['close'].ffill()
        df.dropna(subset=['close'], inplace=True)

        with _contaminated_lock:
            _contaminated.append({ 'ticker': ticker or 'unknown', 'suspects': n_suspects })

    return df, n_suspects


# --------------------------- INDICADORES (FORÇADO) ---------------------------
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

    # --- HURST ---
    try:
        hurst_series = calculate_rolling_hurst(close_s, window=72, kind='returns')
        hurst_series = hurst_series.replace([np.inf, -np.inf], np.nan)
        rolling_mean_h = hurst_series.rolling(252, min_periods=1).mean()
        rolling_std_h = hurst_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['hurst_z_72_c'] = ((hurst_series - rolling_mean_h) / rolling_std_h).fillna(0.5)
    except Exception as e:
        df['hurst_z_72_c'] = 0.5

    # --- ENTROPY ---
    try:
        entropy_series = calculate_rolling_entropy(close_s, window=20)
        entropy_series = entropy_series.replace([np.inf, -np.inf], np.nan)
        df['Entropy_20'] = entropy_series 
        
        rolling_mean_e = entropy_series.rolling(252, min_periods=1).mean()
        rolling_std_e = entropy_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['Entropy_Z'] = ((entropy_series - rolling_mean_e) / rolling_std_e).fillna(0.5)
    except Exception as e:
        df['Entropy_20'] = 0.0
        df['Entropy_Z'] = 0.5
        
    # --- VOL_OF_VOL ---
    try:
        vol_vol_series = _calculate_rolling_vol_of_vol(close_s, window=20)
        vol_vol_series = vol_vol_series.replace([np.inf, -np.inf], np.nan)
        rolling_mean_v = vol_vol_series.rolling(252, min_periods=1).mean()
        rolling_std_v = vol_vol_series.rolling(252, min_periods=1).std().replace(0, np.nan)
        df['VolVol_Z'] = ((vol_vol_series - rolling_mean_v) / rolling_std_v).fillna(0.0)
    except Exception as e:
        df['VolVol_Z'] = 0.0

    if 'entropy_z_20' in df.columns:
        df.rename(columns={'entropy_z_20': 'Entropy_Z'}, inplace=True)

    return df


def classify_regimes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df['mm200_lab'] = df['close'].rolling(200, min_periods=1).mean()
    df['trend_signal'] = np.where(df['close'] > df['mm200_lab'], 'BULL', 'BEAR')

    distancia_mm = (df['close'] - df['mm200_lab']).abs() / df['mm200_lab']
    df.loc[distancia_mm < 0.03, 'trend_signal'] = 'SIDEWAYS' # Zona neutra de 3%

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


# --------------------------- SIMULAÇÃO & SANITY-TRADE ---------------------------
def run_strategy_simulation(df: pd.DataFrame, strategy, ticker: str, target_regime: str = 'ALL', close_open_trades: bool = True) -> pd.DataFrame:
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

    # Extração segura de indicadores para análise
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
    
    # Tenta pegar half-life (pode vir com varios nomes)
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
            
            # --- FILTRO DE REGIME DO LAB (AGORA FLEXÍVEL) ---
            if target_regime != 'ALL' and today_regime != target_regime:
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
            
            # Trailing Stop Lógico
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
                 # Saída mais agressiva em regimes de baixa
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
                    'halflife_entrada': float(half_life_vals[entry_idx]), # Nova métrica
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


def process_file(file_path: Path, strategy, start_date: str, target_regime: str, close_open_trades: bool) -> pd.DataFrame:
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
        df = df[df.index >= pd.to_datetime(start_date)].copy()

        if df.empty: return pd.DataFrame()

        df = classify_regimes(df)
        df['REGIME'] = df['REGIME'].astype(str)

        # Passa o regime alvo para a simulação
        df_trades = run_strategy_simulation(df, strategy, ticker, target_regime=target_regime, close_open_trades=close_open_trades)

        if not df_trades.empty:
            logger.info('%s: %d trades (suspects=%d)', ticker, len(df_trades), n_suspects)

        return df_trades

    except Exception as e:
        logger.exception('Erro processando %s: %s', file_path.name, e)
        return pd.DataFrame()


def analise_tecnica_detalhada(final_df: pd.DataFrame) -> None:
    print('\n' + '═' * 60)
    print('🔬 ANÁLISE TÉCNICA DETALHADA - LABORATÓRIO (Definitivo)')
    print('═' * 60)

    wins = final_df[final_df['win'] == 1]
    losses = final_df[final_df['win'] == 0]

    print('\n  HURST ANALYSIS:')
    print(f"  Hurst (Wins):   Média={wins['hurst_entrada'].mean():.3f}, Std={wins['hurst_entrada'].std():.3f}")
    if not losses.empty:
        print(f"  Hurst (Losses): Média={losses['hurst_entrada'].mean():.3f}, Std={losses['hurst_entrada'].std():.3f}")

    print('\n  ENTROPY ANALYSIS:')
    if not wins.empty:
        print(f"  Entropy (Wins):   Média={wins['entropy_entrada'].mean():.3f}, Std={wins['entropy_entrada'].std():.3f}")
    if not losses.empty:
        print(f"  Entropy (Losses): Média={losses['entropy_entrada'].mean():.3f}, Std={losses['entropy_entrada'].std():.3f}")

    print('\n  HALF-LIFE ANALYSIS:')
    if 'halflife_entrada' in wins.columns and not wins.empty:
        print(f"  Half-Life (Wins):   Média={wins['halflife_entrada'].mean():.2f}, Std={wins['halflife_entrada'].std():.2f}")
    if 'halflife_entrada' in losses.columns and not losses.empty:
        print(f"  Half-Life (Losses): Média={losses['halflife_entrada'].mean():.2f}, Std={losses['halflife_entrada'].std():.2f}")

    print('\n  PROFITABILITY METRICS:')
    ganhos = final_df[final_df['return'] > 0]['return'].sum()
    perdas = abs(final_df[final_df['return'] < 0]['return'].sum())
    profit_factor = ganhos / perdas if perdas > 0 else float('inf') if ganhos > 0 else 0.0
    print(f"  Total Ganhos:    {ganhos:>8.4f} ({ganhos*100:.2f}%)")
    print(f"  Total Perdas:    {perdas:>8.4f} ({perdas*100:.2f}%)")
    print(f"  Profit Factor:   {profit_factor:.2f}x")

    print('\n  ANÁLISE DE DRAWDOWN:')
    final_df_sorted = final_df.sort_index() if isinstance(final_df.index, pd.DatetimeIndex) else final_df
    retorno_cumulativo = (1 + final_df_sorted['return']).cumprod()
    drawdown = (retorno_cumulativo.cummax() - retorno_cumulativo) / retorno_cumulativo.cummax()
    print(f"  Max Drawdown:    {drawdown.max()*100:>6.2f}%")

    print('\n  PERFORMANCE POR REGIME (DETALHADO):')
    regime_detalhado = final_df.groupby('regime').agg({
        'return': ['count', 'mean', 'sum'],
        'win': 'mean',
        'halflife_entrada': 'mean',
        'days_held': 'mean'
    }).round(4)
    regime_detalhado.columns = ['Trades', 'Avg_Return', 'Total_Return', 'WinRate', 'HalfLife', 'Days']
    # Ordena por Retorno Total para ver onde está o dinheiro
    print(regime_detalhado.sort_values('Total_Return', ascending=False))


def save_sanity_report(path: Path) -> None:
    if not _contaminated:
        logger.info('Nenhum ticker contaminado detectado.')
        return
    df = pd.DataFrame(_contaminated)
    df_agg = df.groupby('ticker')['suspects'].sum().reset_index()
    df_agg.to_csv(path, index=False)
    logger.info('Sanity report salvo em %s', path)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='Stress Test - Lab Multi-Regime')
    
    # --- NOVO ARGUMENTO DE REGIME ---
    parser.add_argument('--regime', type=str, default='ALL', 
                        help='Regime alvo para teste (ex: BULL_CALM, SIDEWAYS_CALM, BEAR_VOLATILE, ALL)')
    
    parser.add_argument('--strategy', choices=['mean-reversion', 'adaptive-sniper', 'volatile-momentum'], default='mean-reversion')
    parser.add_argument('--start-date', type=str, default=START_DATE)

    # Parametros Mean Reversion
    mean_rev_group = parser.add_argument_group('Mean Reversion')
    mean_rev_group.add_argument('--bb-std', type=float, default=1.5)
    mean_rev_group.add_argument('--rsi-period', type=int, default=120)
    
    # Parametros Adaptativos
    adaptive_group = parser.add_argument_group('Adaptive Mean Reversion')
    adaptive_group.add_argument('--disable-adaptive-rsi', action='store_true')
    adaptive_group.add_argument('--disable-adaptive-bb', action='store_true')
    adaptive_group.add_argument('--disable-regime-filter', action='store_true')
    adaptive_group.add_argument('--bb-std-volatile', type=float, default=2.5)
    
    # Novo parâmetro Half-Life exposto
    adaptive_group.add_argument('--max-half-life', type=int, default=25, help='Filtro de elasticidade (Half-Life máximo)')

    vm_group = parser.add_argument_group('Volatile Momentum')
    vm_group.add_argument('--atr-stop', type=float, default=2.5, help='ATR multiplier for stop loss')
    
    exec_group = parser.add_argument_group('Execution')
    exec_group.add_argument('--out', type=str, default=None)
    exec_group.add_argument('--workers', type=int, default=DEFAULT_WORKERS)
    exec_group.add_argument('--close-open-trades', action='store_true')

    args = parser.parse_args()
    files = get_parquet_files()

    if args.strategy == 'mean-reversion':
        strategy = MeanReversionStrategy(
            bb_std_dev=args.bb_std, 
            rsi_period=args.rsi_period,
            bb_std_dev_volatile=args.bb_std_volatile,
            adaptive_rsi=not args.disable_adaptive_rsi,
            adaptive_bb=not args.disable_adaptive_bb,
            use_regime_filter=not args.disable_regime_filter,
            max_half_life=args.max_half_life # Passando o novo parametro
        )
    elif args.strategy == 'volatile-momentum':
        strategy = VolatileMomentumProfessional(
            ema_fast=12,
            ema_slow=26,
            atr_stop_multiplier=args.atr_stop,
            atr_profit_multiplier=3.0,
            target_regimes=['BULL_VOLATILE', 'BEAR_VOLATILE'] if args.regime == 'ALL' else [args.regime]
        )
    else:
        strategy = AdaptiveSniperStrategy()

    logger.info('Estratégia: %s', strategy.get_name())
    logger.info('Testando Regime: %s', args.regime)

    all_trades = []
    
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(process_file, fp, strategy, args.start_date, args.regime, args.close_open_trades): fp for fp in files}
        for f in tqdm(as_completed(futures), total=len(futures), desc='Arquivos'):
            res = f.result()
            if isinstance(res, pd.DataFrame) and not res.empty:
                all_trades.append(res)

    if all_trades:
        final_df = pd.concat(all_trades, ignore_index=True)

        print('\n' + '=' * 60)
        print('🏁 RESULTADOS GERAIS DO STRESS TEST - LABORATÓRIO (Definitivo)')
        print('=' * 60)

        # Resumo Simples
        regime_stats = final_df.groupby('regime')['return'].agg(['count', 'mean'])
        regime_stats['win_rate'] = final_df.groupby('regime')['return'].apply(lambda x: (x > 0).mean())
        print(regime_stats.sort_values('mean', ascending=False))

        analise_tecnica_detalhada(final_df)
        save_sanity_report(Path('sanity_report.csv'))
    else:
        logger.warning('Nenhum trade gerado para o regime %s.', args.regime)

if __name__ == '__main__':
    main()