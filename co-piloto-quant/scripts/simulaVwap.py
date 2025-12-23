import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# =========================================================
# CONFIGURAÇÃO DE PASTAS
# =========================================================
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
LAB_OUTPUT_DIR = project_root / "src" / "co_piloto_quant" / "data" / "lab_outputs"
REPORT_DIR = project_root / "src" / "co_piloto_quant" / "data" / "lab_reports"
REPORT_DIR.mkdir(exist_ok=True, parents=True)

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def load_all_csvs(path: Path) -> pd.DataFrame:
    """Carrega todos os CSVs globais de uma pasta em um único DataFrame."""
    files = sorted(path.glob("*_vwap_lab_global.csv"))
    if not files:
        raise RuntimeError(f"Nenhum CSV encontrado em {path}")

    df_list = []
    for f in files:
        df = pd.read_csv(f)
        ticker = f.stem.replace("_vwap_lab_global", "")
        df["Ticker"] = ticker
        df_list.append(df)
    df_all = pd.concat(df_list, ignore_index=True)
    print(f"{len(files)} CSVs carregados, total de linhas: {len(df_all)}")
    return df_all


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona métricas extras: Sharpe simplificado e drawdown."""
    df = df.copy()
    df["Sharpe"] = df["Avg_Return"] / (df["Volatility"] + 1e-9)  # evita divisão por zero
    # Drawdown simulado aproximado
    df["Drawdown"] = df["Avg_Return"] - df["Volatility"]
    return df


def plot_bucket_bar(stats: pd.DataFrame, title: str):
    """Plota retorno médio por bucket em barras."""
    if stats["Count"].sum() < 10:
        return
    plt.figure(figsize=(12, 6))
    colors = ["red" if x < 0 else "green" for x in stats["Avg_Return"]]
    sns.barplot(
        x="z_bucket",
        y="Avg_Return",
        data=stats,
        palette=colors,
        dodge=False
    )
    plt.axhline(0, color="black", linewidth=1)
    plt.ylabel("Retorno Médio (%)")
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


def plot_heatmap(df: pd.DataFrame, value_col: str, title: str):
    """Plota heatmap de valor por ativo x bucket."""
    pivot = df.pivot(index="Ticker", columns="z_bucket", values=value_col)
    plt.figure(figsize=(14, max(5, len(pivot)/2)))
    sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn", center=0)
    plt.title(title)
    plt.ylabel("Ativo")
    plt.xlabel("Bucket VWAP")
    plt.tight_layout()
    plt.show()


# =========================================================
# EXECUÇÃO PRINCIPAL
# =========================================================
if __name__ == "__main__":
    print(f"Carregando CSVs de: {LAB_OUTPUT_DIR}")
    df_all = load_all_csvs(LAB_OUTPUT_DIR)
    df_all = compute_metrics(df_all)

    # Estatísticas globais por horizonte
    horizons = sorted(df_all["Horizon_Days"].unique())
    for h in horizons:
        df_h = df_all[df_all["Horizon_Days"] == h]
        print(f"\n=== Métricas Globais para Horizonte {h} dias ===")
        display_cols = ["z_bucket", "Count", "Avg_Return", "Median_Return", "Volatility", "Win_Rate", "Sharpe", "Drawdown"]
        print(df_h[display_cols].set_index("z_bucket"))
        df_h[display_cols].to_csv(REPORT_DIR / f"global_metrics_{h}d.csv", index=False)
        plot_bucket_bar(df_h, f"Global | Retorno Médio {h}D vs Stress VWAP")
        plot_heatmap(df_h, "Avg_Return", f"Heatmap Avg_Return | Horizonte {h}D")

    # Estatísticas por ativo
    tickers = df_all["Ticker"].unique()
    for ticker in tickers:
        df_t = df_all[df_all["Ticker"] == ticker]
        print(f"\n--- Métricas para {ticker} ---")
        for h in horizons:
            df_th = df_t[df_t["Horizon_Days"] == h]
            print(f"\nHorizonte {h}D")
            print(df_th[display_cols].set_index("z_bucket"))
            df_th[display_cols].to_csv(REPORT_DIR / f"{ticker}_metrics_{h}d.csv", index=False)
            plot_bucket_bar(df_th, f"{ticker} | Retorno Médio {h}D vs Stress VWAP")
