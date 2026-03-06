
import subprocess
import sys
import os


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SRC_PATH = os.path.join(PROJECT_ROOT, 'co-piloto-quant', 'src')
PYTHON = sys.executable

def run_step(script_name, step_desc):
    print(f"\n=== {step_desc} ({script_name}) ===")
    env = os.environ.copy()
    # Inclui src no PYTHONPATH explicitamente
    env['PYTHONPATH'] = SRC_PATH + os.pathsep + PROJECT_ROOT + os.pathsep + env.get('PYTHONPATH', '')
    result = subprocess.run([PYTHON, script_name], cwd=PROJECT_ROOT, env=env)
    if result.returncode != 0:
        print(f"[ERRO] Falha ao rodar {script_name}")
        return False
    return True

if __name__ == "__main__":
    etapas = [
        ('co-piloto-quant/scripts/update_market_data.py', 'Atualizando dados de mercado'),
        ('co-piloto-quant/scripts/data_pipeline.py', 'Executando pipeline institucional'),
        ('co-piloto-quant/scripts/features_pipeline.py', 'Executando feature pipeline')
    ]
    falhas = 0
    for script, desc in etapas:
        ok = run_step(script, desc)
        if not ok:
            falhas += 1
    if falhas == 0:
        print("\n✅ Pipeline completo finalizado com sucesso!")
    else:
        print(f"\n⚠️ Pipeline finalizado com {falhas} etapa(s) com erro. Veja os logs para detalhes.")
        sys.exit(1)
