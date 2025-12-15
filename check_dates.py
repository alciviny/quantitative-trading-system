import pandas as pd
from pathlib import Path

ml_ready = Path('co-piloto-quant/src/co_piloto_quant/data/ml_ready')
files = sorted(ml_ready.glob('*_SA.parquet'))

if files:
    dates_min = []
    dates_max = []
    
    for f in files[:5]:
        try:
            df = pd.read_parquet(f)
            if 'data_pregao' in df.columns:
                dates = pd.to_datetime(df['data_pregao'])
            else:
                dates = pd.to_datetime(df.index, errors='coerce')
            dates_min.append(dates.min())
            dates_max.append(dates.max())
            print(f'{f.stem}: {dates.min().date()} a {dates.max().date()} ({len(df)} dias)')
        except Exception as e:
            print(f'{f.stem}: erro - {str(e)[:50]}')
    
    if dates_min and dates_max:
        print(f'\nRange geral: {min(dates_min).date()} a {max(dates_max).date()}')
        print(f'Total de {len(files)} arquivos')
else:
    print('Nenhum arquivo encontrado')
