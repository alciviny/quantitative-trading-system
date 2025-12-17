"""Módulo para análise de robustez de estratégias de trading usando Monte Carlo.

Este módulo fornece ferramentas para realizar simulações de Monte Carlo,
incluindo Bootstrap simples e Block Bootstrap, para avaliar a robustez dos
retornos de uma estratégia de trading. Ele calcula métricas de risco importantes,
como percentis de retorno, drawdown máximo e probabilidade de ruína.
"""

import logging
from typing import Dict, List, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def run_monte_carlo(
    trade_returns: np.ndarray,
    num_simulations: int = 1000,
    initial_capital: float = 10000.0,
    min_return: float = -0.99
) -> pd.DataFrame:
    """Executa uma simulação de Monte Carlo usando amostragem de bootstrap simples.

    Args:
        trade_returns (np.ndarray): Um array de retornos percentuais de trades.
        num_simulations (int, optional): O número de simulações a serem executadas.
            Defaults to 1000.
        initial_capital (float, optional): O capital inicial para cada simulação.
            Defaults to 10000.0.

    Returns:
        pd.DataFrame: Um DataFrame contendo o retorno final e o drawdown máximo
            para cada simulação.
    """
    results: List[Dict[str, float]] = []
    if trade_returns.size == 0:
        logger.warning("Monte Carlo recebeu um array de retornos vazio. Retornando DataFrame vazio.")
        return pd.DataFrame()

    trade_returns = np.clip(trade_returns, min_return, None)

    for _ in range(num_simulations):
        # Amostragem com reposição (Bootstrap)
        simulated_trades = np.random.choice(
            trade_returns,
            size=len(trade_returns),
            replace=True
        )

        log_returns = np.log1p(simulated_trades)
        cumulative_log_return = np.cumsum(log_returns)
        equity_curve = initial_capital * np.exp(cumulative_log_return)

        final_return = (equity_curve[-1] / initial_capital) - 1
        
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / np.maximum(peak, 1e-10)
        max_dd = np.nanmax(drawdown)

        results.append({
            "return": final_return,
            "max_dd": max_dd
        })

    return pd.DataFrame(results)


def _block_bootstrap(returns: np.ndarray, block_size: int) -> np.ndarray:
    """Gera uma amostra usando a técnica de Block Bootstrap.

    Essa técnica ajuda a preservar a autocorrelação nos dados, como
    clusters de perdas ou ganhos.

    Args:
        returns (np.ndarray): O array de retornos original.
        block_size (int): O tamanho de cada bloco.

    Returns:
        np.ndarray: Um novo array de retornos amostrado por blocos.
    """
    # Cria uma lista de blocos sobrepostos
    blocks = [
        returns[i : i + block_size]
        for i in range(len(returns) - block_size + 1)
    ]

    sampled_indices = np.random.randint(0, len(blocks), size=len(returns) // block_size + 1)
    
    # Concatena os blocos amostrados
    sampled_returns = np.concatenate([blocks[i] for i in sampled_indices])

    return sampled_returns[:len(returns)]


def run_monte_carlo_block(
    trade_returns: np.ndarray,
    block_size: int = 5,
    num_simulations: int = 1000,
    initial_capital: float = 10000.0,
    min_return: float = -0.99
) -> pd.DataFrame:
    """Executa uma simulação de Monte Carlo usando Block Bootstrap.

    Args:
        trade_returns (np.ndarray): Um array de retornos percentuais de trades.
        block_size (int, optional): O tamanho do bloco para a amostragem.
            Defaults to 5.
        num_simulations (int, optional): O número de simulações a serem executadas.
            Defaults to 1000.
        initial_capital (float, optional): O capital inicial para cada simulação.
            Defaults to 10000.0.

    Returns:
        pd.DataFrame: Um DataFrame contendo o retorno final e o drawdown máximo
            para cada simulação.
    """
    results: List[Dict[str, float]] = []
    if trade_returns.size == 0:
        logger.warning("Block Bootstrap recebeu um array de retornos vazio. Retornando DataFrame vazio.")
        return pd.DataFrame()

    trade_returns = np.clip(trade_returns, min_return, None)

    for _ in range(num_simulations):
        simulated_trades = _block_bootstrap(trade_returns, block_size)
        
        log_returns = np.log1p(simulated_trades)
        cumulative_log_return = np.cumsum(log_returns)
        equity_curve = initial_capital * np.exp(cumulative_log_return)

        final_return = (equity_curve[-1] / initial_capital) - 1
        
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (peak - equity_curve) / np.maximum(peak, 1e-10)
        max_dd = np.nanmax(drawdown)

        results.append({
            "return": final_return,
            "max_dd": max_dd
        })

    return pd.DataFrame(results)


def robustness_report(
    mc_df: pd.DataFrame,
    ruin_level: float = 0.5
) -> pd.DataFrame:
    """Gera um relatório de robustez a partir dos resultados de Monte Carlo.

    Calcula os percentis pessimistas de retorno e drawdown, a probabilidade
    de ruína e uma versão pessimista do Calmar Ratio.

    Args:
        mc_df (pd.DataFrame): DataFrame com os resultados das simulações.
        ruin_level (float, optional): O nível de drawdown considerado como
            "ruína". Defaults to 0.5 (50% de perda).

    Returns:
        pd.DataFrame: Um DataFrame com as métricas de robustez.
    """
    if mc_df.empty:
        logger.warning("robustness_report recebeu um DataFrame vazio.")
        return pd.DataFrame()

    report: Dict[str, float] = {
        "return_P5": mc_df['return'].quantile(0.05),
        "return_P10": mc_df['return'].quantile(0.10),
        "return_median": mc_df['return'].quantile(0.50),
        "maxDD_P90": mc_df['max_dd'].quantile(0.90),
        "maxDD_P95": mc_df['max_dd'].quantile(0.95),
        "prob_ruin": (mc_df['max_dd'] > ruin_level).mean()
    }

    # Calmar pessimista (P10 de retorno / P90 de DD) para evitar divisão por zero
    calmar_pessimista = mc_df['return'].quantile(0.10) / mc_df['max_dd'].quantile(0.90)
    report["calmar_pessimista"] = calmar_pessimista if np.isfinite(calmar_pessimista) else 0.0

    return pd.DataFrame(report, index=["ROBUSTEZ"])


def full_monte_carlo_analysis(
    trade_returns: np.ndarray,
    num_simulations: int = 5000,
    block_size: int = 5,
    ruin_level: float = 0.5
) -> Dict[str, Any]:
    """Executa um pipeline completo de análise de Monte Carlo.

    Realiza simulações de Bootstrap simples e Block Bootstrap e gera
    relatórios de robustez para ambos.

    Args:
        trade_returns (np.ndarray): Array com os retornos dos trades.
        num_simulations (int, optional): Número de simulações. Defaults to 5000.
        block_size (int, optional): Tamanho do bloco para Block Bootstrap. Defaults to 5.
        ruin_level (float, optional): Nível de drawdown para o cálculo da
            probabilidade de ruína. Defaults to 0.5.

    Returns:
        Dict[str, Any]: Um dicionário contendo os DataFrames dos resultados
            das simulações e os relatórios de robustez.
    """
    logger.info("Iniciando análise completa de Monte Carlo com %d simulações.", num_simulations)
    
    mc_simple = run_monte_carlo(
        trade_returns,
        num_simulations=num_simulations
    )

    mc_block = run_monte_carlo_block(
        trade_returns,
        block_size=block_size,
        num_simulations=num_simulations
    )

    logger.info("Gerando relatórios de robustez...")
    report_simple = robustness_report(mc_simple, ruin_level)
    report_block = robustness_report(mc_block, ruin_level)
    
    logger.info("Análise de Monte Carlo concluída.")
    return {
        "mc_simple": mc_simple,
        "mc_block": mc_block,
        "report_simple": report_simple,
        "report_block": report_block
    }


def strategy_is_robust(report: pd.DataFrame) -> bool:
    """Determina se uma estratégia é robusta com base em critérios objetivos.

    Critérios:
    - Retorno no 5º percentil (pior 5% dos casos) deve ser positivo.
    - Probabilidade de ruína (drawdown > 50%) deve ser menor que 5%.
    - Calmar Ratio pessimista (P10) deve ser maior que 1.

    Args:
        report (pd.DataFrame): O relatório de robustez gerado pela função
            `robustness_report`.

    Returns:
        bool: True se a estratégia for considerada robusta, False caso contrário.
    """
    if report.empty:
        return False
        
    crit1 = report.loc['ROBUSTEZ', 'return_P5'] > 0
    crit2 = report.loc['ROBUSTEZ', 'prob_ruin'] < 0.05
    crit3 = report.loc['ROBUSTEZ', 'calmar_pessimista'] > 1.0
    
    return all([crit1, crit2, crit3])
