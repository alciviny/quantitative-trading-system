


import pandas as pd
import os
from energy_engine.features.diagnostics import diagnostico_regimes


def main(energy_path=None, factors_path=None, ticker=None, plot=True, batch=False, data_dir=None):
	import glob
	if batch:
		# Diretório padrão se não informado
		if data_dir is None:
			data_dir = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results/')
		energy_files = glob.glob(os.path.join(data_dir, 'structural_energy_*.csv'))
		ativos = [os.path.basename(f).replace('structural_energy_','').replace('.csv','') for f in energy_files]
		for ticker in ativos:
			energy_path = os.path.join(data_dir, f'structural_energy_{ticker}.csv')
			factors_path = os.path.join(data_dir, f'structural_factors_{ticker}.csv')
			if not os.path.exists(energy_path) or not os.path.exists(factors_path):
				print(f'[AVISO] Arquivos ausentes para {ticker}, ignorando.')
				continue
			try:
				energy = pd.read_csv(energy_path, index_col=0)
				factors = pd.read_csv(factors_path, index_col=0)
				print(f'Rodando diagnóstico para {ticker}')
				diagnostico_regimes(energy, factors, ticker=ticker, plot=plot)
			except Exception as e:
				print(f'[ERRO] Falha ao rodar {ticker}: {e}')
	else:
		if ticker is None:
			ticker = "PETR4.SA"
		if energy_path is None:
			energy_path = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_{}.csv'.format(ticker))
		if factors_path is None:
			factors_path = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_{}.csv'.format(ticker))
		energy = pd.read_csv(energy_path, index_col=0)
		factors = pd.read_csv(factors_path, index_col=0)
		print(f'Rodando diagnóstico para {ticker}')
		diagnostico_regimes(energy, factors, ticker=ticker, plot=plot)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Diagnóstico de regimes estruturais.")
	parser.add_argument('--energy_path', type=str, default=None, help='Caminho para o CSV de energia')
	parser.add_argument('--factors_path', type=str, default=None, help='Caminho para o CSV de fatores estruturais')
	parser.add_argument('--ticker', type=str, default=None, help='Ticker do ativo')
	parser.add_argument('--no-plot', action='store_true', help='Não exibir gráficos')
	parser.add_argument('--batch', action='store_true', help='Rodar diagnóstico para todos os ativos disponíveis')
	parser.add_argument('--data_dir', type=str, default=None, help='Diretório dos arquivos de dados')
	args = parser.parse_args()
	main(energy_path=args.energy_path, factors_path=args.factors_path, ticker=args.ticker, plot=not args.no_plot, batch=args.batch, data_dir=args.data_dir)
