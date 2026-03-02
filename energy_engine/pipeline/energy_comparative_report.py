

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
from energy_engine.utils.rolling import rolling_zscore
from energy_engine.features.metrics import preditive_metrics

def main(ativos=None, factors_dir=None, results_dir=None, plot=True):
	if ativos is None:
		ativos = ['ITUB4.SA', 'VALE3.SA', 'PETR4.SA']
	if factors_dir is None:
		factors_dir = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results')
	if results_dir is None:
		results_dir = factors_dir
	resultados = []
	for ativo in ativos:
		FACTORS_PATH = os.path.join(factors_dir, f'structural_factors_{ativo}.csv')
		try:
			fatores = pd.read_csv(FACTORS_PATH, index_col=0)
		except Exception as e:
			print(f'Erro ao carregar {ativo}: {e}')
			continue
		window_compressao = 21
		window_instab = 21
		window_zscore_robusto = 60
		window_entropy = 21
		window_v2 = 21
		window_v3 = 21
		fatores['compressao'] = 1 / (fatores['fator_expansao'].rolling(window_compressao).std() + 1e-8)
		regime = fatores['regime_rolling'].fillna(method='ffill')
		fatores['mudanca_regime'] = regime.diff().ne(0).astype(int)
		fatores['instabilidade'] = fatores['mudanca_regime'].rolling(window_instab).mean()
		fatores['compressao_z'] = rolling_zscore(fatores['compressao'], window_zscore_robusto)
		fatores['instabilidade_z'] = rolling_zscore(fatores['instabilidade'], window_zscore_robusto)
		fatores['energia_estrutural'] = fatores['compressao_z'] + fatores['instabilidade_z']
		fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)
		fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
		regimes = fatores['regime_rolling'].fillna(method='ffill')
		centroides = fatores_v.groupby(regimes).transform('mean')
		fatores_v = fatores_v.loc[centroides.index]
		fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
		fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()
		fatores['energia_v3'] = (
			fatores['energia_estrutural'] +
			fatores['energia_v2'] +
			fatores['fatores_entropy']
		)
		fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()
		fatores['transicao'] = fatores['regime_rolling'].diff().ne(0).astype(int)
		met_v1 = preditive_metrics('energia_estrutural', fatores)
		met_v2 = preditive_metrics('energia_v2_roll', fatores)
		met_v3 = preditive_metrics('energia_v3_roll', fatores)
		resultados.append({
			'ativo': ativo,
			'v0.1': met_v1,
			'v0.2': met_v2,
			'v0.3': met_v3
		})
		if plot:
			plt.figure(figsize=(12,6))
			fatores['energia_estrutural'].plot(label='Energia v0.1')
			fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
			fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
			plt.title(f'Comparativo Energias — {ativo}')
			plt.legend()
			plt.grid(True)
			plt.savefig(os.path.join(results_dir, f'energy_comparative_{ativo}.png'))
			plt.close()
	report_rows = []
	for r in resultados:
		for v, met in r.items():
			if v == 'ativo': continue
			report_rows.append({
				'ativo': r['ativo'],
				'versao': v,
				'energia_antes': met['energia_antes'],
				'energia_dia_troca': met['energia_dia_troca'],
				'energia_geral': met['energia_geral'],
				'prob_top20': met['prob_top20'],
				'prob_geral': met['prob_geral']
			})
	df_report = pd.DataFrame(report_rows)
	df_report.to_csv(os.path.join(results_dir, 'energy_comparative_report.csv'), index=False)
	print('Relatório comparativo salvo em energy_comparative_report.csv')
	print(df_report)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Relatório comparativo de energias estruturais.")
	parser.add_argument('--ativos', type=str, nargs='+', default=None, help='Lista de ativos (ex: ITUB4.SA VALE3.SA PETR4.SA)')
	parser.add_argument('--factors_dir', type=str, default=None, help='Diretório dos CSVs de fatores estruturais')
	parser.add_argument('--results_dir', type=str, default=None, help='Diretório para salvar os resultados')
	parser.add_argument('--no-plot', action='store_true', help='Não salvar gráficos')
	args = parser.parse_args()
	main(ativos=args.ativos, factors_dir=args.factors_dir, results_dir=args.results_dir, plot=not args.no_plot)
