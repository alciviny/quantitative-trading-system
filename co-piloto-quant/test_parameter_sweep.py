# -*- coding: utf-8 -*-
"""
test_parameter_sweep.py
Testa combinações de parâmetros para encontrar melhor performance em walk-forward
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import subprocess
import json
import pandas as pd
from itertools import product

def create_test_script(bb_std: float, rsi_period: int, max_hl: int, 
                       use_regime: bool, only_bull: bool, output_file: str):
    """Cria script temporário com parâmetros específicos"""
    
    script = f"""# -*- coding: utf-8 -*-
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

logger = logging.getLogger("test_sweep")
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
            _contaminated.append({{'ticker': ticker or 'unknown', 'suspects': n_suspects}})
    
    return df, n_suspects

def _calculate_rolling_vol_of_vol(price_series: pd.Series, window: int = 20) -> pd.Series:
    if median_abs_deviation is None:
        return pd.Series(0.0, index=price_series.index)
    returns = price_series.pct_change()
    rolling_vol = returns.rolling(window).std()
    vol_of_vol = rolling_vol.rolling(window).apply(median_abs_deviation, raw=False)
    return vol_of_vol

def classify_regime(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if 'Entropy_20' not in df.columns or 'VolVol_Z' not in df.columns:
        df['REGIME'] = 'UNKNOWN'
        return df
    
    entropy = df['Entropy_20']
    vol_vol = df['VolVol_Z']
    mm200 = df['close'].rolling(200, min_periods=1).mean()
    price_above_ma = df['close'] > mm200
    
    regime = []
    for idx in df.index:
        ent = entropy.iloc[idx] if pd.notna(entropy.iloc[idx]) else 2.0
        vv = vol_vol.iloc[idx] if pd.notna(vol_vol.iloc[idx]) else 0.0
        above_ma = price_above_ma.iloc[idx] if pd.notna(price_above_ma.iloc[idx]) else False
        
        if above_ma:
            if ent < 2.5 and vv < 1.0:
                regime.append('BULL_CALM')
            elif ent < 2.5 and vv >= 1.0:
                regime.append('BULL_VOLATILE')
            else:
                regime.append('BULL_CALM')
        else:
            if ent < 2.5 and vv < 1.0:
                regime.append('BEAR_CALM')
            elif ent < 2.5 and vv >= 1.0:
                regime.append('BEAR_VOLATILE')
            else:
                regime.append('BEAR_CALM')
    
    df['REGIME'] = regime
    return df

def process_one_asset(ticker: str, train_df: pd.DataFrame, test_df: pd.DataFrame) -> List[Dict]:
    results = []
    
    train_df, _ = apply_sanity_check(train_df, ticker)
    test_df, _ = apply_sanity_check(test_df, ticker)
    
    for df_phase, phase_name in [(train_df, 'TRAIN'), (test_df, 'TEST')]:
        if df_phase.empty or len(df_phase) < 50:
            continue
        
        strategy = MeanReversionStrategy(
            bb_std_dev={bb_std},
            rsi_period={rsi_period},
            max_half_life={max_hl},
            use_regime_filter={use_regime},
            only_bull_market={only_bull},
            adaptive_rsi=True,
            adaptive_bb=True
        )
        
        try:
            trades_list = strategy.backtest(df_phase)
            
            for trade in trades_list:
                ret = trade.get('return', 0)
                regime = trade.get('regime', 'UNKNOWN')
                
                results.append({{
                    'ticker': ticker,
                    'regime': regime,
                    'return': ret,
                    'win': 1 if ret > 0 else 0,
                    'phase': phase_name,
                    'days_held': trade.get('days_held', 0),
                    'hurst': trade.get('hurst_entrada', 0.5),
                    'entropy': trade.get('entropy_entrada', 0.0),
                }})
        except Exception as e:
            pass
    
    return results

def main():
    setup_logging()
    files = get_parquet_files()
    if not files:
        logger.error("Nenhum arquivo encontrado")
        return
    
    logger.info(f"Testando com parâmetros: BB={{bb_std}}, RSI={{rsi_period}}, HL={{max_hl}}, Regime={{use_regime}}, OnlyBull={{only_bull}}")
    
    all_results = []
    
    for fpath in files:
        ticker = fpath.stem.replace("_SA", "")
        try:
            df = pd.read_parquet(fpath)
            if df.empty or 'close' not in df.columns:
                continue
            
            # Períodos: 12 meses treino + 3 meses teste
            mid_date = pd.Timestamp('2023-12-31')
            train_df = df[df.index < mid_date].tail(252)
            test_df = df[(df.index >= mid_date) & (df.index < mid_date + pd.Timedelta(days=90))]
            
            results = process_one_asset(ticker, train_df, test_df)
            all_results.extend(results)
        except Exception as e:
            logger.warning(f"Erro processando {{ticker}}: {{e}}")
    
    if all_results:
        df_results = pd.DataFrame(all_results)
        df_results.to_csv('{output_file}', index=False)
        
        train = df_results[df_results['phase'] == 'TRAIN']
        test = df_results[df_results['phase'] == 'TEST']
        
        print(f"  {{len(train)} trades TRAIN | Ret: {{train['return'].mean():.4f}} | WR: {{(train['win'].mean()):.1%}}")
        print(f"  {{len(test)} trades TEST   | Ret: {{test['return'].mean():.4f}} | WR: {{(test['win'].mean()):.1%}}")

if __name__ == "__main__":
    main()
"""
    
    return script

# Definir grid de parâmetros
param_grid = {{
    'bb_std': [1.0, 1.5, 2.0],
    'rsi_period': [60, 120, 180],
    'max_hl': [15, 25, 35],
    'use_regime': [False, True],
    'only_bull': [False, True],
}}

combinations = list(product(
    param_grid['bb_std'],
    param_grid['rsi_period'],
    param_grid['max_hl'],
    param_grid['use_regime'],
    param_grid['only_bull']
))

print(f"\n🔧 TESTANDO {len(combinations)} COMBINAÇÕES DE PARÂMETROS")
print("="*80)

results_summary = []

for idx, (bb_std, rsi_period, max_hl, use_regime, only_bull) in enumerate(combinations, 1):
    output_file = f"sweep_results_{idx:03d}.csv"
    test_script = create_test_script(bb_std, rsi_period, max_hl, use_regime, only_bull, output_file)
    
    # Salvar e executar script
    temp_file = f"_temp_sweep_{idx}.py"
    with open(temp_file, 'w') as f:
        f.write(test_script)
    
    print(f"\n[{idx}/{len(combinations)}] BB={bb_std:.1f} | RSI={rsi_period} | HL={max_hl} | Regime={use_regime} | OnlyBull={only_bull}")
    print("  ", end="", flush=True)
    
    try:
        result = subprocess.run([sys.executable, temp_file], capture_output=True, text=True, timeout=60)
        
        # Ler resultados
        if Path(output_file).exists():
            df = pd.read_csv(output_file)
            train = df[df['phase'] == 'TRAIN']
            test = df[df['phase'] == 'TEST']
            
            if len(train) > 0 and len(test) > 0:
                train_ret = train['return'].mean()
                test_ret = test['return'].mean()
                train_wr = train['win'].mean()
                test_wr = test['win'].mean()
                
                deg = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
                
                print(f"Train: {train_ret:+.4f} ({train_wr:.0%}) | Test: {test_ret:+.4f} ({test_wr:.0%}) | Deg: {deg:+.0f}%")
                
                results_summary.append({
                    'bb_std': bb_std,
                    'rsi_period': rsi_period,
                    'max_hl': max_hl,
                    'use_regime': use_regime,
                    'only_bull': only_bull,
                    'train_trades': len(train),
                    'test_trades': len(test),
                    'train_ret': train_ret,
                    'test_ret': test_ret,
                    'train_wr': train_wr,
                    'test_wr': test_wr,
                    'degradation': deg,
                })
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        Path(temp_file).unlink(missing_ok=True)
        Path(output_file).unlink(missing_ok=True)

# Salvar resumo
df_summary = pd.DataFrame(results_summary)
df_summary.to_csv('parameter_sweep_summary.csv', index=False)

print("\n" + "="*80)
print("📊 TOP 5 MELHORES PARÂMETROS (por Test Return):")
print("="*80)
top_5 = df_summary.nlargest(5, 'test_ret')[['bb_std', 'rsi_period', 'max_hl', 'use_regime', 'only_bull', 'test_ret', 'test_wr', 'degradation']]
print(top_5.to_string(index=False))
