

import os
import glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import datetime
from energy_engine.utils.rolling import rolling_zscore, robust_zscore
from energy_engine.utils.log import log
from energy_engine.features.metrics import preditive_metrics

def log(msg):
	print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

def rolling_zscore(series, window):
def preditive_metrics(energy_col, fatores, n=5):


def main(factors_dir=None, results_dir=None, plot=True):
	if factors_dir is None:
		factors_dir = os.path.join(os.path.dirname(__file__), '../../co-piloto-quant/src/co_piloto_quant/data/results')
	if results_dir is None:
		results_dir = factors_dir
	files = glob.glob(os.path.join(factors_dir, 'structural_factors_*.csv'))
	ativos = [os.path.basename(f).replace('structural_factors_','').replace('.csv','') for f in files]
	log(f'Encontrados {len(files)} arquivos de fatores estruturais.')
	resultados = []
	for ativo, path in zip(ativos, files):
		try:
			log(f'Processando ativo: {ativo}')
			fatores = pd.read_csv(path, index_col=0)
			log('Arquivo de fatores lido com sucesso.')
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
			log('Energia v0.1 calculada.')
			fatores['fatores_entropy'] = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].rolling(window_entropy).std().mean(axis=1)
			fatores_v = fatores[['fator_persistencia','fator_estrutura','fator_expansao','fator_liquidez']].copy()
			regimes = fatores['regime_rolling'].fillna(method='ffill')
			centroides = fatores_v.groupby(regimes).transform('mean')
			fatores_v = fatores_v.loc[centroides.index]
			fatores['energia_v2'] = np.sqrt(((fatores_v - centroides)**2).sum(axis=1))
			fatores['energia_v2_roll'] = fatores['energia_v2'].rolling(window_v2).mean()
			log('Energia v0.2 calculada.')
			fatores['energia_v3'] = (
				fatores['energia_estrutural'] +
				fatores['energia_v2'] +
				fatores['fatores_entropy']
			)
			fatores['energia_v3_roll'] = fatores['energia_v3'].rolling(window_v3).mean()
			fatores['energia_v4'] = (
				robust_zscore(fatores['energia_estrutural'], window_zscore_robusto) *
				robust_zscore(fatores['energia_v2'], window_zscore_robusto) +
				robust_zscore(fatores['fatores_entropy'], window_zscore_robusto)
			)
			fatores['energia_v4_roll'] = fatores['energia_v4'].rolling(window_v3).mean()
			log('Energia v0.4 calculada.')
			log('Energia v0.3 calculada.')
			met_v1 = preditive_metrics('energia_estrutural', fatores)
			met_v2 = preditive_metrics('energia_v2_roll', fatores)
			met_v3 = preditive_metrics('energia_v3_roll', fatores)
			resultados.append({
				'ativo': ativo,
				'v0.1': met_v1,
				'v0.2': met_v2,
				'v0.3': met_v3
			})
			energy_cols = [
				'date' if 'date' in fatores.columns else None,
				'compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll','fatores_entropy','energia_v3','energia_v3_roll','energia_v4','energia_v4_roll','regime_rolling','ret_futuro_10','close'
			]
			energy_cols = [col for col in energy_cols if col and col in fatores.columns]
			fatores[energy_cols].to_csv(os.path.join(results_dir, f'structural_energy_{ativo}.csv'), index=False)
			log(f'Arquivo de energia salvo para {ativo}.')
			if plot:
				plt.figure(figsize=(12,6))
				fatores['energia_estrutural'].plot(label='Energia v0.1')
				fatores['energia_v2_roll'].plot(label='Energia v0.2 (rolling)')
				fatores['energia_v3_roll'].plot(label='Energia v0.3 (combinada rolling)')
				fatores['energia_v4_roll'].plot(label='Energia v0.4 (robusta, não-linear)', linestyle='--')
				plt.title(f'Comparativo Energias — {ativo}')
				plt.legend()
				plt.grid(True)
				plt.savefig(os.path.join(results_dir, f'energy_comparative_{ativo}.png'))
				plt.close()
				log(f'Gráfico comparativo salvo para {ativo}.')
		except Exception as e:
			log(f'Erro ao processar {ativo}: {e}')
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
	log('Relatório comparativo salvo em energy_comparative_report.csv')
	log(df_report)

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description="Batch de cálculo de energia estrutural para múltiplos ativos.")
	parser.add_argument('--factors_dir', type=str, default=None, help='Diretório dos CSVs de fatores estruturais')
	parser.add_argument('--results_dir', type=str, default=None, help='Diretório para salvar os resultados')
	parser.add_argument('--no-plot', action='store_true', help='Não salvar gráficos')
	args = parser.parse_args()
	main(factors_dir=args.factors_dir, results_dir=args.results_dir, plot=not args.no_plot)
