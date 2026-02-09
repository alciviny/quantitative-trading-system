import pandas as pd
from pathlib import Path

data_dir = Path(__file__).parent / "data" / "processed"
petr4_file = data_dir / "PETR4_SA.parquet"

if petr4_file.exists():
    df = pd.read_parquet(petr4_file)
    print(f"✓ Arquivo existe: {petr4_file}")
    print(f"Shape: {df.shape}")
    print(f"Colunas: {list(df.columns)[:15]}")
    print(f"\nClose existe: {'close' in df.columns}")
    if 'close' in df.columns:
        print(f"Close últimas 5 linhas:\n{df['close'].tail()}")
        print(f"Close min/max: {df['close'].min():.2f} / {df['close'].max():.2f}")
    
    print(f"\nEntropy_20 existe: {'entropy_20' in df.columns}")
    if 'entropy_20' in df.columns:
        print(f"Entropy últimas 5 linhas:\n{df['entropy_20'].tail()}")
        print(f"Entropy min/max/mean: {df['entropy_20'].min():.6f} / {df['entropy_20'].max():.6f} / {df['entropy_20'].mean():.6f}")
else:
    print(f"❌ Arquivo não encontrado: {petr4_file}")
    print(f"Arquivos disponíveis: {list(data_dir.glob('*.parquet'))[:5]}")
