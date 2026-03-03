

import os
import pandas as pd
import numpy as np
import itertools
import subprocess
from energy_engine.utils.log import log

def main(
	quantis=None,
	horizontes=None,
	ativos=None,
	versoes=None,
	output_dir=None,
	validation_script=None
):
	if quantis is None:
		quantis = [0.7, 0.8, 0.9]
	if horizontes is None:
		horizontes = [1, 5, 10, 20]
	if ativos is None:
		# Busca todos os arquivos de fatores estruturais no diretório padrão
		factors_dir = 'co-piloto-quant/src/co_piloto_quant/data/results'
		ativos = []
		for fname in os.listdir(factors_dir):
			if fname.startswith('structural_factors_') and fname.endswith('.csv'):
				ticker = fname.replace('structural_factors_','').replace('.csv','')
				ativos.append(ticker)
		if not ativos:
			ativos = ['BPAC11.SA', 'ELET6.SA', 'AXIA6.SA']  # fallback
	if versoes is None:
		versoes = ['v0.1', 'v0.2', 'v0.3']
	if output_dir is None:
		output_dir = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/docs/validacao_energy/gridsearch/')
	if validation_script is None:
		validation_script = os.path.join(os.path.dirname(__file__), 'energy_validation_metrics.py')
	os.makedirs(output_dir, exist_ok=True)
	resultados = []
	for quantil, horizonte in itertools.product(quantis, horizontes):
		output_csv = os.path.join(output_dir, f'metricas_q{int(quantil*100)}_h{horizonte}.csv')
		cmd = [
			'python', validation_script,
			'--versoes', *versoes,
			'--quantil', str(quantil),
			'--horizonte', str(horizonte),
			'--output', output_csv,
			'--plots', output_dir
		]
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
		print('Grid search finalizado! Resultados em metricas_gridsearch_consolidado.csv')
	else:
		print('Nenhum resultado válido encontrado.')

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Grid search para validação de métricas de energia.")
	parser.add_argument('--quantis', type=float, nargs='+', default=None, help='Lista de quantis')
	parser.add_argument('--horizontes', type=int, nargs='+', default=None, help='Lista de horizontes')
	parser.add_argument('--ativos', type=str, nargs='+', default=None, help='Lista de ativos')
	parser.add_argument('--versoes', type=str, nargs='+', default=None, help='Lista de versões')
	parser.add_argument('--output_dir', type=str, default=None, help='Diretório de saída dos resultados')
	parser.add_argument('--validation_script', type=str, default=None, help='Caminho para o script de validação')
	args = parser.parse_args()
	main(
		quantis=args.quantis,
		horizontes=args.horizontes,
		ativos=args.ativos,
		versoes=args.versoes,
		output_dir=args.output_dir,
		validation_script=args.validation_script
	)
