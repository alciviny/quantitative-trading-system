#!/usr/bin/env python3
import pandas as pd
from pathlib import Path
import sys

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from co_piloto_quant.config import PROCESSED_DIR

# O caminho agora usa a constante do arquivo de configuração
p = PROCESSED_DIR
files = sorted(list(p.glob('*_SA.parquet')))[:3]

for f in files:
    df = pd.read_parquet(f)
    if 'data_pregao' in df.columns:
        dates = pd.to_datetime(df['data_pregao'])
    else:
        dates = pd.to_datetime(df.index, errors='coerce')
    
    print(f'{f.stem}: {dates.min().date()} to {dates.max().date()}, {len(df)} candles')

