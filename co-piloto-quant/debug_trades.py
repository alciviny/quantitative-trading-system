import pandas as pd
import os

os.chdir(r"c:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-quant")

csv_path = "momentum_all_regimes_results.csv"
df = pd.read_csv(csv_path)

with open("debug_output.txt", "w") as f:
    f.write(f"Total de linhas: {len(df)}\n")
    f.write(f"\nColunas: {df.columns.tolist()}\n")
    f.write(f"\nRegimes disponíveis:\n")
    f.write(str(df['regime'].value_counts()) + "\n")
    f.write(f"\n--- BULL_VOLATILE trades: {len(df[df['regime'] == 'BULL_VOLATILE'])}\n")
    f.write(f"Win rate BULL_VOLATILE: {df[df['regime'] == 'BULL_VOLATILE']['win'].mean()*100:.1f}%\n")

print("Done")
