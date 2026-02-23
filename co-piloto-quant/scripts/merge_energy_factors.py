import pandas as pd
import os

ATIVO = 'PETR4.SA'
ENERGY_PATH = os.path.join(os.path.dirname(__file__), f'../src/co_piloto_quant/data/results/structural_energy_{ATIVO}.csv')
FACTORS_PATH = os.path.join(os.path.dirname(__file__), f'../src/co_piloto_quant/data/results/structural_factors_{ATIVO}.csv')
OUT_PATH = os.path.join(os.path.dirname(__file__), f'../src/co_piloto_quant/data/results/energy_factors_merged_{ATIVO}.csv')

def main():
    df_energy = pd.read_csv(ENERGY_PATH)
    df_factors = pd.read_csv(FACTORS_PATH)
    # Tenta usar coluna de data, se existir, senão usa o índice
    if 'date' in df_energy.columns and 'date' in df_factors.columns:
        merged = pd.merge(df_energy, df_factors[['date', 'ret_futuro_10']], on='date', how='left')
    else:
        # Merge por índice
        merged = pd.concat([df_energy.reset_index(drop=True), df_factors['ret_futuro_10'].reset_index(drop=True)], axis=1)
    merged.to_csv(OUT_PATH, index=False)
    print(f"Arquivo de merge salvo em: {OUT_PATH}")
    print(f"Colunas disponíveis: {merged.columns.tolist()}")

if __name__ == "__main__":
    main()