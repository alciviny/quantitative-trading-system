import os
import pandas as pd
import itertools
import subprocess
from energy_engine.utils.log import log

def run_grid_search(quantis, horizontes, ativos, versoes, output_dir, validation_script, extra_args=None):
    """Executa grid search para validação de métricas de energia."""
    os.makedirs(output_dir, exist_ok=True)
    resultados = []
    for quantil, horizonte in itertools.product(quantis, horizontes):
        output_csv = os.path.join(output_dir, f'metricas_q{int(quantil*100)}_h{horizonte}.csv')
        cmd = [
            'python', validation_script,
            '--ativos', *ativos,
            '--versoes', *versoes,
            '--quantil', str(quantil),
            '--horizonte', str(horizonte),
            '--output', output_csv,
            '--plots', output_dir
        ]
        if extra_args:
            cmd += extra_args
        log(f'Rodando: quantil={quantil}, horizonte={horizonte}')
        try:
            subprocess.run(cmd, check=True)
        except Exception as e:
            log(f"Falha em quantil={quantil}, horizonte={horizonte}: {e}")
            continue
        if os.path.exists(output_csv):
            try:
                df = pd.read_csv(output_csv)
                if not df.empty:
                    df['quantil'] = quantil
                    df['horizonte'] = horizonte
                    resultados.append(df)
                else:
                    log(f"Arquivo {output_csv} está vazio, ignorando.")
            except Exception as e:
                log(f"Erro ao ler {output_csv}: {e}")
    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        df_final.to_csv(os.path.join(output_dir, 'metricas_gridsearch_consolidado.csv'), index=False)
        log('Grid search finalizado! Resultados em metricas_gridsearch_consolidado.csv')
        return df_final
    else:
        log('Nenhum resultado válido encontrado.')
        return None