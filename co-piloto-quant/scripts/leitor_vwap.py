import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Adiciona o diretório raiz do projeto ao sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from co_piloto_quant.config import RESULTS_DIR

# =========================================================
# CONFIGURAÇÃO DE PASTAS
# =========================================================
# O caminho agora usa a constante do arquivo de configuração
LAB_OUTPUT_DIR = RESULTS_DIR
SAVE_OUTPUTS = True         # Se True, salva CSVs consolidados
PLOT_OUTPUTS = True         # Se True, plota gráficos


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

def compute_global_stats(df: pd.DataFrame) -> dict:
    """Computa estatísticas globais agrupadas por horizonte."""
    all_stats = {}
    horizons = sorted(df["Horizon_Days"].unique())
    for h in horizons:
        df_h = df[df["Horizon_Days"] == h]
        stats = df_h[["z_bucket", "Count", "Avg_Return", "Median_Return", "Volatility", "Win_Rate"]].copy()
        all_stats[f"fwd_ret_{h}d"] = stats
    return all_stats

def compute_per_ticker_stats(df: pd.DataFrame) -> dict:
    """Computa estatísticas separadas por ativo."""
    per_ticker = {}
    tickers = df["Ticker"].unique()
    for ticker in tickers:
        df_t = df[df["Ticker"] == ticker]
        ticker_stats = {}
        horizons = sorted(df_t["Horizon_Days"].unique())
        for h in horizons:
            df_h = df_t[df_t["Horizon_Days"] == h]
            stats = df_h[["z_bucket", "Count", "Avg_Return", "Median_Return", "Volatility", "Win_Rate"]].copy()
            ticker_stats[f"fwd_ret_{h}d"] = stats
        per_ticker[ticker] = ticker_stats
    return per_ticker

def plot_stats(stats: pd.DataFrame, title: str):
    """Plota o retorno médio por z_bucket."""
    if not PLOT_OUTPUTS:
        return
    if stats["Count"].sum() < 10:
        return  # evita plots com poucos dados

    plt.figure(figsize=(12, 6))
    colors = ["red" if x < 0 else "green" for x in stats["Avg_Return"]]
    sns.barplot(
        x=stats["z_bucket"],
        y=stats["Avg_Return"],
        hue=stats["z_bucket"],
        palette=colors,
        dodge=False,
        legend=False
    )
    plt.axhline(0, color="black", linewidth=1)
    plt.ylabel("Retorno Médio (%)")
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

def save_stats_to_csv(stats_dict: dict, prefix: str):
    """Salva estatísticas em CSVs separados por horizonte."""
    if not SAVE_OUTPUTS:
        return
    output_dir = LAB_OUTPUT_DIR / "consolidated_outputs"
    output_dir.mkdir(exist_ok=True, parents=True)
    for horizon, stats in stats_dict.items():
        file_path = output_dir / f"{prefix}_{horizon}.csv"
        stats.to_csv(file_path, index=False)
    print(f"CSV(s) salvos em {output_dir}")

# =========================================================
# EXECUÇÃO PRINCIPAL
# =========================================================
if __name__ == "__main__":
    try:
        print(f"Carregando CSVs de: {LAB_OUTPUT_DIR}")
        df_all = load_all_csvs(LAB_OUTPUT_DIR)
    except Exception as e:
        print(f"Erro ao carregar CSVs: {e}")
        sys.exit(1)

    # Estatísticas globais
    print("\n=== Estatísticas Globais ===")
    global_stats = compute_global_stats(df_all)
    save_stats_to_csv(global_stats, "global_stats")
    for col, stats in global_stats.items():
        print(f"\nHorizonte: {col}")
        print(stats.set_index("z_bucket"))
        plot_stats(stats, f"Global | Retorno Médio {col} vs Stress VWAP")

    # Estatísticas por ativo
    print("\n=== Estatísticas por Ativo ===")
    per_ticker_stats = compute_per_ticker_stats(df_all)
    for ticker, stats_dict in per_ticker_stats.items():
        print(f"\n--- {ticker} ---")
        save_stats_to_csv(stats_dict, ticker)
        for col, stats in stats_dict.items():
            print(f"\n{col}")
            print(stats.set_index("z_bucket"))
            plot_stats(stats, f"{ticker} | Retorno Médio {col} vs Stress VWAP")
