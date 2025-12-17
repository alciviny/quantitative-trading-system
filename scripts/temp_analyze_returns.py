import pandas as pd
from pathlib import Path

# Define o caminho do arquivo de forma robusta
file_path = Path(__file__).resolve().parents[1] / 'co-piloto-quant' / 'momentum_all_regimes_results.csv'

print(f"Analisando o arquivo: {file_path}\n")

try:
    df = pd.read_csv(file_path)

    if 'return' in df.columns:
        returns = df['return'].dropna()
        
        print("--- Análise Estatística da Coluna 'return' ---")
        print(returns.describe())
        
        catastrophic_losses = (returns <= -0.99).sum()
        heavy_losses = (returns < -0.50).sum()
        
        print("\n--- Análise de Perdas Extremas ---")
        print(f"Número de trades com perda >= 99%: {catastrophic_losses}")
        print(f"Número de trades com perda > 50%:  {heavy_losses}")

        if catastrophic_losses > 0:
            print("\n[!] Conclusão: Foram encontrados trades com perdas catastróficas (>=99%).")
            print("    Isso explica por que a simulação de Monte Carlo resulta em 100% de ruína.")
            print("    Um único trade com retorno de -1.0 zera o capital em uma simulação.")

    else:
        print("Erro: A coluna 'return' não foi encontrada no arquivo.")

except FileNotFoundError:
    print(f"Erro: O arquivo não foi encontrado em '{file_path}'")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")
