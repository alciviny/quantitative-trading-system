"""
Stress Test de Robustez com Simulação de Monte Carlo.

Este script carrega os resultados de um backtest (uma lista de retornos de trades)
e aplica as análises de Monte Carlo (Bootstrap Simples e Block Bootstrap) para
avaliar a robustez da estratégia.

Ele gera um relatório detalhado no console e salva as principais métricas de
risco em um arquivo CSV.

Exemplo de uso:
    python scripts/stress_test_monte_carlo.py --input-file some_results.csv
"""

import argparse
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Adiciona o diretório 'src' ao path para permitir importações locais
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from src.co_piloto_quant.analysis.monte_carlo import (
        full_monte_carlo_analysis,
        strategy_is_robust
    )
except ImportError as e:
    print(f"Erro ao importar o módulo de análise: {e}")
    print("Verifique se o arquivo 'src/co_piloto_quant/analysis/monte_carlo.py' existe.")
    sys.exit(1)


def setup_logging():
    """Configura o logging básico para o script."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )


def main():
    """Função principal que orquestra a execução do script."""
    parser = argparse.ArgumentParser(
        description="Executa análise de robustez de Monte Carlo em resultados de backtest.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("src/co_piloto_quant/data/momentum_all_regimes_results.csv"),
        help="Caminho para o arquivo CSV com os resultados do backtest. Deve conter uma coluna 'return'."
    )
    parser.add_argument(
        "--simulations",
        type=int,
        default=5000,
        help="Número de simulações de Monte Carlo a serem executadas."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("src/co_piloto_quant/data/reports"),
        help="Diretório onde o relatório de resultados será salvo."
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=5,
        help="Tamanho do bloco para o Block Bootstrap."
    )
    parser.add_argument(
        "--ruin-level",
        type=float,
        default=0.5,
        help="Nível de drawdown (perda percentual) considerado como 'ruína'."
    )

    args = parser.parse_args()
    setup_logging()
    
    # --- Validação dos caminhos ---
    # O script está em co-piloto-quant/scripts, então o input file default está um nível acima
    input_file_path = args.input_file
    if not input_file_path.is_absolute():
        # Assumindo que o arquivo de input está em src/co_piloto_quant/data/
        input_file_path = Path(__file__).resolve().parents[1] / "src/co_piloto_quant/data" / args.input_file.name

    if not input_file_path.exists():
        logging.error(f"Arquivo de entrada não encontrado: {input_file_path}")
        sys.exit(1)
        
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = Path(__file__).resolve().parents[1] / "src/co_piloto_quant/data/reports" / "monte_carlo_results.csv"

    # --- Carregamento e Preparação dos Dados ---
    logging.info(f"Carregando resultados do backtest de: {input_file_path}")
    try:
        backtest_df = pd.read_csv(input_file_path)
    except Exception as e:
        logging.error(f"Falha ao ler o arquivo CSV: {e}")
        sys.exit(1)

    if "return" not in backtest_df.columns:
        logging.error("A coluna 'return' não foi encontrada no arquivo de entrada.")
        logging.error("Colunas disponíveis: %s", backtest_df.columns.tolist())
        sys.exit(1)
        
    trade_returns = backtest_df["return"].dropna().to_numpy()

    if trade_returns.size == 0:
        logging.error("Não há dados de retorno válidos para analisar.")
        sys.exit(1)

    # --- Diagnóstico dos Dados de Entrada ---
    logging.info("Executando diagnóstico sobre os dados de retorno carregados...")
    returns_series = pd.Series(trade_returns)
    print("\n" + "-"*80)
    print("🔬 ANÁLISE ESTATÍSTICA DOS DADOS DE ENTRADA".center(80))
    print(returns_series.describe())
    catastrophic_losses = (returns_series <= -0.99).sum()
    heavy_losses = (returns_series < -0.50).sum()
    print("\n--- Análise de Perdas Extremas ---")
    print(f"Número de trades com perda >= 99%: {catastrophic_losses}")
    print(f"Número de trades com perda > 50%:  {heavy_losses}")
    print("-" * 80 + "\n")
    # --- Fim do Diagnóstico ---

    logging.info(f"Analisando {len(trade_returns)} trades com {args.simulations} simulações.")

    # --- Execução da Análise ---
    analysis_results = full_monte_carlo_analysis(
        trade_returns=trade_returns,
        num_simulations=args.simulations,
        block_size=args.block_size,
        ruin_level=args.ruin_level
    )

    report_simple = analysis_results["report_simple"]
    report_block = analysis_results["report_block"]

    # --- Exibição dos Relatórios ---
    print("\n" + "="*80)
    print("🔬 RELATÓRIO DE ROBUSTEZ - MONTE CARLO".center(80))
    print("="*80)

    print("\n--- [ Análise com Bootstrap Simples ] ---")
    print(report_simple.round(4))

    print("\n--- [ Análise com Block Bootstrap (Mais Conservadora) ] ---")
    print(report_block.round(4))
    
    # --- Veredito Final e Salvamento ---
    is_robust = strategy_is_robust(report_block)
    verdict = "ROBUSTA" if is_robust else "FRÁGIL"
    
    print("\n" + "-"*80)
    logging.info(f"VEREDITO (baseado em Block Bootstrap): A estratégia é considerada {verdict}.")
    print("-"*80 + "\n")

    # Salva as métricas solicitadas do relatório de Block Bootstrap
    try:
        metrics_to_save = report_block[["return_P5", "return_P10", "prob_ruin"]].copy()
        metrics_to_save.to_csv(output_file)
        logging.info(f"Relatório de métricas salvo em: {output_file}")
    except Exception as e:
        logging.error(f"Falha ao salvar o arquivo de resultados: {e}")

if __name__ == "__main__":
    main()
