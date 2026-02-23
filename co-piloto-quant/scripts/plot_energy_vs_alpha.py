import pandas as pd
import matplotlib.pyplot as plt
import os


# Parâmetros
ATIVO = 'PETR4.SA'
VERSAO = 'v0.3'
DATA_PATH = os.path.join(os.path.dirname(__file__), f'../src/co_piloto_quant/data/results/structural_energy_{ATIVO}.csv')

def main():
    # Carrega dados de energia estrutural e alpha futuro
    df = pd.read_csv(DATA_PATH)
    # Checa se as colunas existem
    if f'energy_{VERSAO}' not in df.columns or 'ret_futuro_10' not in df.columns:
        print(f"Colunas necessárias não encontradas em {DATA_PATH}.")
        print(f"Colunas disponíveis: {df.columns.tolist()}")
        return
    # Plot scatter energia x alpha futuro
    plt.figure(figsize=(10,6))
    plt.scatter(df[f'energy_{VERSAO}'], df['ret_futuro_10'], alpha=0.5, s=10)
    plt.xlabel(f'Energia Estrutural {VERSAO}')
    plt.ylabel('Alpha Futuro (ret_futuro_10)')
    plt.title(f'{ATIVO} - Energia Estrutural {VERSAO} x Alpha Futuro')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    main()