


import pandas as pd
import os
from energy_engine.features.diagnostics import diagnostico_regimes


def main(energy_path=None, factors_path=None, ticker="PETR4.SA", plot=True):
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
	parser.add_argument('--ticker', type=str, default="PETR4.SA", help='Ticker do ativo')
	parser.add_argument('--no-plot', action='store_true', help='Não exibir gráficos')
	args = parser.parse_args()
	main(energy_path=args.energy_path, factors_path=args.factors_path, ticker=args.ticker, plot=not args.no_plot)
