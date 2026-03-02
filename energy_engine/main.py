import argparse
import os
import pandas as pd
from energy_engine.features.energy import calcular_energia_estrutural, calcular_entropia_centroides, calcular_energia_v4
from energy_engine.features.grid_search import run_grid_search
from energy_engine.features.batch import processar_batch
from energy_engine.features.report import gerar_relatorio_comparativo
from energy_engine.features.metrics import preditive_metrics
from energy_engine.features.diagnostics import diagnostico_regimes

def etapa_leitura_fatores(ativos, factors_dir):
    fatores_dict = {}
    for ativo in ativos:
        path = os.path.join(factors_dir, f'structural_factors_{ativo}.csv')
        fatores_dict[ativo] = pd.read_csv(path, index_col=0)
    return fatores_dict

def etapa_calculo_energia(fatores_dict):
    resultados = {}
    for ativo, fatores in fatores_dict.items():
        fatores = calcular_energia_estrutural(fatores)
        fatores = calcular_entropia_centroides(fatores)
        fatores = calcular_energia_v4(fatores)
        resultados[ativo] = fatores
    return resultados

def etapa_validacao(resultados):
    for ativo, fatores in resultados.items():
        print(f'\nMétricas preditivas para {ativo}:')
        preditive_metrics('energia_estrutural', fatores)
        preditive_metrics('energia_v2_roll', fatores)
        preditive_metrics('energia_v3_roll', fatores)
        if 'energia_v4_roll' in fatores.columns:
            preditive_metrics('energia_v4_roll', fatores)

def etapa_diagnostico(resultados):
    for ativo, fatores in resultados.items():
        print(f'\nDiagnóstico de regimes para {ativo}:')
        diagnostico_regimes(fatores, fatores, ticker=ativo, plot=False)

def etapa_exportacao(resultados, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    for ativo, fatores in resultados.items():
        out_path = os.path.join(output_dir, f'structural_energy_{ativo}.csv')
        cols = [
            'compressao','instabilidade','energia_estrutural','energia_v2','energia_v2_roll',
            'fatores_entropy','energia_v3','energia_v3_roll','energia_v4','energia_v4_roll'
        ]
        export_cols = [col for col in cols if col in fatores.columns]
        fatores[export_cols].to_csv(out_path)
        print(f'Resultado salvo em {out_path}')

def main():
    parser = argparse.ArgumentParser(description='Orquestrador universal energy_engine')
    parser.add_argument('--step', type=str, default='all', choices=['all','leitura','calculo','validacao','diagnostico','exportacao','gridsearch','batch','relatorio'], help='Etapa do pipeline')
    parser.add_argument('--ativos', nargs='+', help='Lista de ativos')
    parser.add_argument('--factors_dir', type=str, help='Diretório dos fatores estruturais')
    parser.add_argument('--output_dir', type=str, default='./energy_results', help='Diretório de saída dos resultados')
    parser.add_argument('--quantis', nargs='+', type=float, default=[0.7,0.8,0.9], help='Quantis para grid search')
    parser.add_argument('--horizontes', nargs='+', type=int, default=[1,5,10,20], help='Horizontes para grid search')
    parser.add_argument('--versoes', nargs='+', default=['v0.1','v0.2','v0.3','v0.4'], help='Versões de energia para grid search')
    parser.add_argument('--validation_script', type=str, default='energy_engine/pipeline/energy_validation_metrics.py', help='Script de validação para grid search')
    parser.add_argument('--no-plot', action='store_true', help='Não exibir gráficos')
    args = parser.parse_args()

    # Etapas tradicionais
    if args.step in ['all','leitura','calculo','validacao','diagnostico','exportacao']:
        if not args.ativos or not args.factors_dir:
            raise ValueError('ativos e factors_dir são obrigatórios para esta etapa.')
        fatores_dict = etapa_leitura_fatores(args.ativos, args.factors_dir)
        resultados = etapa_calculo_energia(fatores_dict)
        if args.step in ['all','validacao']:
            etapa_validacao(resultados)
        if args.step in ['all','diagnostico']:
            etapa_diagnostico(resultados)
        if args.step in ['all','exportacao']:
            etapa_exportacao(resultados, args.output_dir)

    # Grid search
    if args.step == 'gridsearch':
        if not args.ativos or not args.factors_dir:
            raise ValueError('ativos e factors_dir são obrigatórios para gridsearch.')
        run_grid_search(
            quantis=args.quantis,
            horizontes=args.horizontes,
            ativos=args.ativos,
            versoes=args.versoes,
            output_dir=args.output_dir,
            validation_script=args.validation_script
        )

    # Batch
    if args.step == 'batch':
        if not args.factors_dir or not args.output_dir:
            raise ValueError('factors_dir e output_dir são obrigatórios para batch.')
        processar_batch(args.factors_dir, args.output_dir, plot=not args.no_plot)

    # Relatório comparativo
    if args.step == 'relatorio':
        if not args.ativos or not args.factors_dir or not args.output_dir:
            raise ValueError('ativos, factors_dir e output_dir são obrigatórios para relatório.')
        gerar_relatorio_comparativo(args.ativos, args.factors_dir, args.output_dir, plot=not args.no_plot)

if __name__ == '__main__':
    main()
