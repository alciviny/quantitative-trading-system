#!/usr/bin/env python3
import pandas as pd
from pathlib import Path

p = Path('src/co_piloto_quant/data/ml_ready')
files = sorted(list(p.glob('*_SA.parquet')))[:3]

for f in files:
    df = pd.read_parquet(f)
    if 'data_pregao' in df.columns:
        dates = pd.to_datetime(df['data_pregao'])
    else:
        dates = pd.to_datetime(df.index, errors='coerce')
    
    print(f'{f.stem}: {dates.min().date()} to {dates.max().date()}, {len(df)} candles')
