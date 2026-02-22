import os
import pandas as pd
from pathlib import Path

# Diretório dos dados processados (ajustar se necessário)
PROCESSED_DIR = Path(__file__).resolve().parent.parent / "src" / "co_piloto_quant" / "data" / "processed"

def convert_all_csv_to_parquet():
    csv_files = list(PROCESSED_DIR.glob("*_processed.csv"))
    if not csv_files:
        print("Nenhum arquivo CSV encontrado para converter.")
        return
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        parquet_file = csv_file.with_suffix('.parquet')
        df.to_parquet(parquet_file, index=False)
        print(f"Convertido: {csv_file.name} -> {parquet_file.name}")

if __name__ == "__main__":
    convert_all_csv_to_parquet()
    print("Conversão concluída!")
