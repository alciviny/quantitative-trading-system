import os
import pandas as pd
import numpy as np
import itertools
import subprocess

# Parâmetros do grid
quantis = [0.7, 0.8, 0.9]
horizontes = [1, 5, 10, 20]
ativos = ['BPAC11.SA', 'ELET6.SA', 'AXIA6.SA']
versoes = ['v0.1', 'v0.2', 'v0.3']

# Caminhos
output_dir = 'co-piloto-quant/docs/validacao_energy/gridsearch/'
os.makedirs(output_dir, exist_ok=True)

resultados = []

for quantil, horizonte in itertools.product(quantis, horizontes):
    output_csv = os.path.join(output_dir, f'metricas_q{int(quantil*100)}_h{horizonte}.csv')
    cmd = [
        'python', 'co-piloto-quant/scripts/energy_validation_metrics.py',
        '--ativos', *ativos,  # Corrigido nome da variável
        '--versoes', *versoes,
        '--quantil', str(quantil),
        '--horizonte', str(horizonte),
        '--output', output_csv,
        '--plots', output_dir
    ]
    print(f'Rodando: quantil={quantil}, horizonte={horizonte}')
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Falha em quantil={quantil}, horizonte={horizonte}: {e}")
        continue
    # Lê o resultado e adiciona info de quantil/horizonte se houver dados válidos
    if os.path.exists(output_csv):
        try:
            df = pd.read_csv(output_csv)
            if not df.empty:
                df['quantil'] = quantil
                df['horizonte'] = horizonte
                resultados.append(df)
            else:
                print(f"Arquivo {output_csv} está vazio, ignorando.")
        except Exception as e:
            print(f"Erro ao ler {output_csv}: {e}")

# Consolida tudo em um único CSV
df_final = pd.concat(resultados, ignore_index=True)
df_final.to_csv(os.path.join(output_dir, 'metricas_gridsearch_consolidado.csv'), index=False)
print('Grid search finalizado! Resultados em metricas_gridsearch_consolidado.csv')
