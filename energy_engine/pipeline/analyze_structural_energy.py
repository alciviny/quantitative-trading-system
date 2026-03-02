


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from energy_engine.features.energy import calcular_energia_estrutural, calcular_entropia_centroides
from energy_engine.features.metrics import preditive_metrics

def main(
	factors_path=None,
	results_path=None,
	ticker="PETR4.SA",
	plot=True
):
	"""
	Executa o cálculo de energia estrutural para um arquivo de fatores estruturais.
	"""
	# Caminhos flexíveis
	if factors_path is None:
		factors_path = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results/structural_factors_{}.csv'.format(ticker))
	if results_path is None:
		results_path = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results/structural_energy_{}.csv'.format(ticker))

	fatores = pd.read_csv(factors_path, index_col=0)
	fatores = calcular_energia_estrutural(fatores)
	fatores = calcular_entropia_centroides(fatores)

	if plot:
		plt.figure(figsize=(12,6))
		fatores['energia_estrutural'].plot(label='Energia Estrutural')
		plt.title(f'Energia Estrutural v0.1 — {ticker}')
		plt.legend()
		plt.grid(True)
		plt.show()

	fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
	N = 5
	energias_antes = []
	for idx in fatores.index[N:]:
		if fatores.loc[idx, 'transicao'] == 1:
			energias_antes.append(fatores.loc[idx-N:idx-1, 'energia_estrutural'].mean())
	print(f'Energia média nos {N} dias antes das transições:', np.nanmean(energias_antes))
	print('Energia média geral:', fatores['energia_estrutural'].mean())
	regimes = fatores['regime_rolling'].fillna(method='ffill')
	centroides = fatores_v.groupby(regimes).transform('mean')
	fatores_v = fatores_v.loc[centroides.index]
	fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
	window_v2 = 21
	fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()

	window_v3 = 21
	fatores['energia_v3'] = (
		fatores['energia_estrutural'] +
		fatores['energia_v2'] +
		fatores['fatores_entropy']
	)
	fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()

	if plot:
		plt.figure(figsize=(12,6))
		fatores['energia_estrutural'].plot(label='Energia v0.1')
		fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
		fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
		plt.title('Comparativo Energia Estrutural v0.1 vs v0.2 vs v0.3')
		plt.legend()
		plt.grid(True)
		plt.show()

	fatores[['compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll','fatores_entropy','energia_v3','energia_v3_roll']].to_csv(results_path)
	print(f'Arquivo de energia estrutural salvo em {results_path}')

	preditive_metrics('energia_estrutural', fatores)
	preditive_metrics('energia_v2_roll', fatores)
	preditive_metrics('energia_v3_roll', fatores)

