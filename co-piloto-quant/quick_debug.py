import sys
import os

try:
    os.chdir(r"c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant")
    import pandas as pd
    
    df = pd.read_csv("momentum_all_regimes_results.csv")
    
    print("=== ANÁLISE DO ARQUIVO ===")
    print(f"Total de trades: {len(df)}")
    print(f"\nColunas: {list(df.columns)}")
    print(f"\n=== REGIMES ===")
    print(df['regime'].value_counts())
    
    print(f"\n=== BULL_VOLATILE ANÁLISE ===")
    bull_vol = df[df['regime'] == 'BULL_VOLATILE']
    print(f"Trades: {len(bull_vol)}")
    print(f"Win rate: {bull_vol['win'].mean()*100:.1f}%")
    print(f"Retorno médio: {bull_vol['return'].mean()*100:.2f}%")
    
except Exception as e:
    print(f"ERRO: {e}")
    import traceback
    traceback.print_exc()
