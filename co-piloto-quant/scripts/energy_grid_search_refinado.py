import os
import pandas as pd
import numpy as np
import itertools
import subprocess

# Parâmetros do grid
quantis = [0.7, 0.8, 0.9]
horizontes = [1, 5, 10, 20]
janelas = [10, 21, 42, 63]  # Exemplo: 10, 21, 42, 63 dias
ativos = ['BPAC11.SA', 'ELET6.SA', 'AXIA6.SA']
versoes = ['v0.1', 'v0.2', 'v0.3']

# Caminhos
output_dir = 'co-piloto-quant/docs/validacao_energy/gridsearch_refinado/'
os.makedirs(output_dir, exist_ok=True)

resultados = []

for quantil, horizonte, janela in itertools.product(quantis, horizontes, janelas):
    output_csv = os.path.join(output_dir, f'metricas_q{int(quantil*100)}_h{horizonte}_w{janela}.csv')
    cmd = [
        'python', 'co-piloto-quant/scripts/energy_validation_metrics.py',
        '--ativos', *ativos,
        '--versoes', *versoes,
        '--quantil', str(quantil),
        '--horizonte', str(horizonte),
        '--output', output_csv,
        '--plots', output_dir,
        '--janela', str(janela)  # Suporte para janela de cálculo
    ]
    print(f'Rodando: quantil={quantil}, horizonte={horizonte}, janela={janela}')
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Falha em quantil={quantil}, horizonte={horizonte}, janela={janela}: {e}")
        continue
    if os.path.exists(output_csv):
        try:
            df = pd.read_csv(output_csv)
            if not df.empty:
                df['quantil'] = quantil
                df['horizonte'] = horizonte
                df['janela'] = janela
                resultados.append(df)
            else:
                print(f"Arquivo {output_csv} está vazio, ignorando.")
        except Exception as e:
            print(f"Erro ao ler {output_csv}: {e}")

# Consolida tudo em um único CSV
df_final = pd.concat(resultados, ignore_index=True)
df_final.to_csv(os.path.join(output_dir, 'metricas_gridsearch_refinado_consolidado.csv'), index=False)
print('Grid search refinado finalizado! Resultados em metricas_gridsearch_refinado_consolidado.csv')
