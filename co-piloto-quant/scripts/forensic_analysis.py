"""
forensic_analysis_enhanced.py

Versão profissional e quantitativa do seu script de análise forense
Winners vs Losers — comparações robustas e significância estatística

Melhorias principais:
- Medianas + médias
- Teste estatístico não-paramétrico (Mann-Whitney U)
- Tamanho de efeito (Cohen's d) e diferença padronizada
- Intervalos de confiança por bootstrap (median diff)
- Proteções contra amostras pequenas / NaNs
- Logging, outputs CSV/Markdown com recomendações automáticas
- CLI simples (caminhos customizáveis) e modularidade para testes

Dependências extras:
    pip install scipy

"""

from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu
from scipy import stats

# Optional plotting (matplotlib apenas para debug/inspeção)
import matplotlib.pyplot as plt

# --------------------------- Configuração --------------------------- 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("forensic")

# Defaults - podem ser sobrescritos por CLI
BACKTEST_REPORT = Path("data/reports/ranking_backtest.csv")
MARKET_DNA = Path("data/reports/b3_market_dna.csv")
OUT_DIR = Path("data/reports/forensic")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Parâmetros estatísticos
MIN_SAMPLE = 8  # mínimo para executar testes confiáveis
BOOTSTRAP_ITERS = 2000  # iterações para intervalo bootstrap (median diff)
ALPHA = 0.05

# --------------------------- Utilitários --------------------------- 

def safe_replace_sa(s: pd.Series) -> pd.Series:
    return s.astype(str).str.replace('.SA', '', regex=False)


def read_csv_safe(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {p}")
    return pd.read_csv(p)


# --------------------------- Carregamento e Merge --------------------------- 

def load_and_merge_data(backtest_path: Path = BACKTEST_REPORT, dna_path: Path = MARKET_DNA) -> pd.DataFrame:
    logger.info("Carregando arquivos...")
    df_bt = read_csv_safe(backtest_path)
    df_dna = read_csv_safe(dna_path)

    # Normaliza tickers
    df_bt['Ticker_Key'] = safe_replace_sa(df_bt.get('Ticker', df_bt.columns[0]))
    df_dna['Ticker_Key'] = safe_replace_sa(df_dna.get('Ticker', df_dna.columns[0]))

    # Merge com inner join para manter consistência
    df_merged = pd.merge(df_bt, df_dna, on='Ticker_Key', suffixes=("", "_dna"))

    # Seleciona colunas relevantes (de maneira defensiva)
    candidate_cols = [
        'Ticker', 'Retorno Total (%)', 'Sharpe Ratio', 'Max Drawdown (%)', 'Win Rate (%)',
        'Entropy_Media', 'Entropy_Z', 'Vol_Diaria_Atual', 'Hurst_Z'
    ]

    cols_final = [c for c in candidate_cols if c in df_merged.columns]
    if len(cols_final) < 3:
        logger.warning("Menos de 3 colunas esperadas encontradas após o merge. Conferir os CSVs.")

    df_out = df_merged[cols_final].copy()
    # Remover linhas com Sharpe ausente (não faz sentido classificar)
    df_out = df_out[df_out['Sharpe Ratio'].notna()]

    logger.info(f"Merge final: {len(df_out)} ativos com as colunas: {list(df_out.columns)}")
    return df_out


# --------------------------- Estatísticas Robustas --------------------------- 

def cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """Tamanho de efeito (Cohen's d) com pooled std."""
    a = np.asarray(a)
    b = np.asarray(b)
    na, nb = len(a), len(b)
    if na < 2 or nb < 2:
        return np.nan
    pooled_sd = np.sqrt(((na - 1) * a.std(ddof=1) ** 2 + (nb - 1) * b.std(ddof=1) ** 2) / (na + nb - 2))
    if pooled_sd == 0:
        return np.nan
    return (a.mean() - b.mean()) / pooled_sd


def bootstrap_median_diff(a: np.ndarray, b: np.ndarray, iters: int = BOOTSTRAP_ITERS, alpha: float = ALPHA) -> Tuple[float, float]:
    """Retorna (lower, upper) do intervalo de confiança para a diferença de medianas via bootstrap."""
    a = np.asarray(a)
    b = np.asarray(b)
    diffs = np.empty(iters)
    rng = np.random.default_rng(12345)
    for i in range(iters):
        ma = np.median(rng.choice(a, size=len(a), replace=True))
        mb = np.median(rng.choice(b, size=len(b), replace=True))
        diffs[i] = ma - mb
    lower = np.quantile(diffs, alpha / 2)
    upper = np.quantile(diffs, 1 - alpha / 2)
    return float(lower), float(upper)

def compare_groups(winners: pd.DataFrame, losers: pd.DataFrame, column: str) -> Optional[Dict[str, Any]]:
    w = winners[column].dropna().to_numpy()
    l = losers[column].dropna().to_numpy()

    if len(w) < MIN_SAMPLE or len(l) < MIN_SAMPLE:
        logger.debug(f"Amostra pequena para {column}: winners={len(w)}, losers={len(l)}")
        return None

    # Teste Mann-Whitney (não-paramétrico)
    try:
        stat, p_value = mannwhitneyu(w, l, alternative='two-sided')
    except Exception:
        p_value = np.nan
        stat = np.nan

    effect = float(np.nan if np.isnan(np.mean(w)) or np.isnan(np.mean(l)) else np.mean(w) - np.mean(l))
    median_diff = float(np.median(w) - np.median(l))
    d = cohen_d(w, l)

    # Bootstrap CI para median diff
    try:
        ci_low, ci_up = bootstrap_median_diff(w, l)
    except Exception as exc:
        logger.debug(f"Bootstrap falhou para {column}: {exc}")
        ci_low, ci_up = np.nan, np.nan

    return {
        'stat': stat,
        'p_value': p_value,
        'mean_win': float(np.mean(w)),
        'mean_loss': float(np.mean(l)),
        'median_win': float(np.median(w)),
        'median_loss': float(np.median(l)),
        'mean_diff': effect,
        'median_diff': median_diff,
        'cohen_d': float(d),
        'median_diff_ci_low': ci_low,
        'median_diff_ci_up': ci_up,
        'n_win': len(w),
        'n_loss': len(l)
    }


# --------------------------- Investigação Forense --------------------------- 

def forensic_investigation(df: pd.DataFrame, out_dir: Path = OUT_DIR) -> pd.DataFrame:
    """Executa a análise forense e grava relatórios CSV/markdown com recomendações.

    Retorna um DataFrame com as métricas estatísticas calculadas para cada fator.
    """
    if df.empty:
        raise ValueError("DataFrame vazio")

    # Definição de grupos baseado em Sharpe (Top/Bottom 25%)
    q_high = df['Sharpe Ratio'].quantile(0.75)
    q_low = df['Sharpe Ratio'].quantile(0.25)

    winners = df[df['Sharpe Ratio'] >= q_high]
    losers = df[df['Sharpe Ratio'] <= q_low]

    logger.info(f"Amostra total: {len(df)} | winners: {len(winners)} | losers: {len(losers)}")

    metrics = {
        'Hurst_Z': 'Tendência (Hurst Z)',
        'Entropy_Z': 'Caos/Ruído (Entropy Z)',
        'Entropy_Media': 'Entropia Média',
        'Vol_Diaria_Atual': 'Volatilidade (%)'
    }

    rows = []
    recommendations = []

    for col, label in metrics.items():
        if col not in df.columns:
            logger.debug(f"Coluna {col} não encontrada, pulando.")
            continue

        res = compare_groups(winners, losers, col)
        if res is None:
            rows.append({
                'factor': col,
                'label': label,
                'note': 'insufficient_sample'
            })
            continue

        rows.append({**{'factor': col, 'label': label}, **res})

        # Regras heurísticas para recomendações baseadas em sinais estatísticos
        if col == 'Hurst_Z' and res['mean_diff'] > 0 and res['p_value'] < ALPHA:
            recommendations.append(f"Hurst Z maior nos vencedores (mean_diff={res['mean_diff']:.3f}, p={res['p_value']:.3f}) -> favorece ativos com regime direcional.")
        if col == 'Entropy_Z' and res['mean_diff'] < 0 and res['p_value'] < ALPHA:
            recommendations.append(f"Entropy Z menor nos vencedores (mean_diff={res['mean_diff']:.3f}) -> buscar ativos mais previsíveis.")
        if col == 'Vol_Diaria_Atual' and res['median_diff'] < 0 and res['p_value'] < ALPHA:
            recommendations.append(f"Volatilidade menor nos vencedores (median_diff={res['median_diff']:.3f}) -> aplicar cap de vol ou filter por vol atual.")

        # Efeito notável
        if abs(res.get('cohen_d', 0) or 0) >= 0.8:
            recommendations.append(f"Tamanho de efeito grande para {label} (Cohen's d = {res['cohen_d']:.2f}).")

    df_stats = pd.DataFrame(rows)

    # Salva CSV com estatísticas
    csv_path = out_dir / "forensic_stats.csv"
    df_stats.to_csv(csv_path, index=False)
    logger.info(f"Estatísticas salvas em: {csv_path}")

    # Save simple markdown report
    md_path = out_dir / "forensic_report.md"
    with md_path.open('w', encoding='utf-8') as f:
        f.write("# Forensic Analysis Report\n\n")
        f.write(f"Amostra total: **{len(df)}** — Winners: **{len(winners)}**, Losers: **{len(losers)}**\n\n")
        f.write("## Estatísticas por fator\n\n")
        for _, r in df_stats.iterrows():
            if r.get('note') == 'insufficient_sample':
                f.write(f"- **{r['label']}**: amostra insuficiente para testes estatísticos.\n")
                continue
            f.write(f"- **{r['label']}**:\n")
            f.write(f"  - mean_win: {r['mean_win']:.4f}, mean_loss: {r['mean_loss']:.4f}\n")
            f.write(f"  - median_win: {r['median_win']:.4f}, median_loss: {r['median_loss']:.4f}\n")
            f.write(f"  - median_diff: {r['median_diff']:.4f} (CI {r['median_diff_ci_low']:.4f}, {r['median_diff_ci_up']:.4f})\n")
            f.write(f"  - p-value (Mann-Whitney): {r['p_value']:.4f}\n")
            f.write(f"  - cohen_d: {r['cohen_d']:.3f}\n\n")

        f.write("## Recomendações automáticas\n\n")
        if not recommendations:
            f.write("Nenhuma recomendação estatisticamente robusta encontrada (use os resultados como orientação).\n")
        else:
            for rec in recommendations:
                f.write(f"- {rec}\n")

    logger.info(f"Relatório markdown salvo em: {md_path}")

    # Lista top/bottom tickers (para inspeção manual)
    try:
        top5 = winners.sort_values('Sharpe Ratio', ascending=False)[['Ticker', 'Retorno Total (%)', 'Hurst_Z', 'Entropy_Z']].head(5)
        bot5 = losers.sort_values('Sharpe Ratio', ascending=True)[['Ticker', 'Retorno Total (%)', 'Hurst_Z', 'Entropy_Z']].head(5)
        top5.to_csv(out_dir / 'top5_winners.csv', index=False)
        bot5.to_csv(out_dir / 'bot5_losers.csv', index=False)
        logger.info('Top/bottom examples salvos.')
    except Exception:
        logger.debug('Nao foi possivel extrair top/bottom examples (colunas possivelmente ausentes).')

    return df_stats


# --------------------------- CLI --------------------------- 

def main(argv=None):
    import argparse

    global MIN_SAMPLE, BOOTSTRAP_ITERS, OUT_DIR

    parser = argparse.ArgumentParser(description="Forensic analysis: winners vs losers (robust stats).")
    parser.add_argument('--backtest', type=str, default=str(BACKTEST_REPORT))
    parser.add_argument('--dna', type=str, default=str(MARKET_DNA))
    parser.add_argument('--out', type=str, default=str(OUT_DIR))
    parser.add_argument('--min-sample', type=int, default=MIN_SAMPLE)
    parser.add_argument('--bootstrap-iters', type=int, default=BOOTSTRAP_ITERS)

    args = parser.parse_args(argv)

    MIN_SAMPLE = args.min_sample
    BOOTSTRAP_ITERS = args.bootstrap_iters
    OUT_DIR = Path(args.out)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        df = load_and_merge_data(Path(args.backtest), Path(args.dna))
    except FileNotFoundError as e:
        logger.error(e)
        sys.exit(1)

    stats = forensic_investigation(df, out_dir=OUT_DIR)
    logger.info('Análise concluída com sucesso.')


if __name__ == '__main__':
    main()
