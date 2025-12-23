import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# =========================================================
# SETUP DE IMPORTAÇÃO
# =========================================================
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root / "src"))

from co_piloto_quant.indicators.vwap_annual import AnnualVWAPAnalyst

# =========================================================
# CONFIGURAÇÃO DO LAB
# =========================================================
DATA_DIR = project_root / "data" / "ml_ready"
OUTPUT_DIR = project_root / "data" / "lab_outputs"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

ANALYSIS_DAYS_LIST = [5, 10, 20, 40]

Z_BINS = [-np.inf, -2.5, -1.5, -0.5, 0.5, 1.5, 2.5, np.inf]
Z_LABELS = [
    "Muito Barato (<-2.5)",
    "Barato (-2.5 a -1.5)",
    "Leve Desc (-1.5 a -0.5)",
    "Neutro",
    "Leve Premio (0.5 a 1.5)",
    "Caro (1.5 a 2.5)",
    "Muito Caro (>2.5)"
]

# =========================================================
# FUNÇÕES AUXILIARES
# =========================================================
def load_local_data(ticker: str) -> pd.DataFrame | None:
    file_path = DATA_DIR / f"{ticker}.parquet"
    if not file_path.exists():
        print(f"Erro: Arquivo {file_path} não encontrado.")
        return None
    df = pd.read_parquet(file_path)
    return df


def create_forward_returns(df: pd.DataFrame) -> pd.DataFrame:
    for d in ANALYSIS_DAYS_LIST:
        df[f"fwd_ret_{d}d"] = df["Close"].shift(-d) / df["Close"] - 1
    return df


def compute_stats(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    stats = (
        df.groupby("z_bucket", observed=False)[target_col]
        .agg(
            Count="count",
            Avg_Return="mean",
            Median_Return="median",
            Volatility="std",
            Win_Rate=lambda x: (x > 0).mean()
        )
        .reset_index()
    )
    stats["Avg_Return"] *= 100
    stats["Median_Return"] *= 100
    stats["Win_Rate"] *= 100
    return stats


def plot_avg_return(stats: pd.DataFrame, title: str):
    if stats["Count"].sum() < 50:
        return
    plt.figure(figsize=(12, 6))
    colors = ["red" if x < 0 else "green" for x in stats["Avg_Return"]]
    sns.barplot(x=stats["z_bucket"], y=stats["Avg_Return"], hue=stats["z_bucket"], palette=colors, legend=False)
    plt.axhline(0, color="black", linewidth=1)
    plt.ylabel("Retorno Médio (%)")
    plt.title(title)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()


# =========================================================
# FUNÇÃO PRINCIPAL PARA CADA ATIVO
# =========================================================
def run_stress_lab(ticker: str, save_to_csv: bool = True, update_ml_ready: bool = False):
    df = load_local_data(ticker)
    if df is None or len(df) < 300:
        print(f"{ticker}: dados insuficientes.")
        return

    analyst = AnnualVWAPAnalyst(price_col="Close")
    df = analyst.calculate(df)

    if "Date" not in df.columns:
        raise RuntimeError(f"{ticker}: coluna 'Date' não encontrada após normalização.")

    df["Year"] = pd.to_datetime(df["Date"]).dt.year
    df = create_forward_returns(df)
    df["z_bucket"] = pd.cut(df["vwap_z_score"], bins=Z_BINS, labels=Z_LABELS)

    all_stats = []

    for d in ANALYSIS_DAYS_LIST:
        target = f"fwd_ret_{d}d"
        stats = compute_stats(df, target)
        stats["Horizon_Days"] = d
        all_stats.append(stats)

    if save_to_csv:
        global_csv = OUTPUT_DIR / f"{ticker}_vwap_lab_global.csv"
        pd.concat(all_stats, ignore_index=True).to_csv(global_csv, index=False)
    
        yearly_stats = (
            df.groupby(["Year", "z_bucket"])["fwd_ret_20d"]
            .mean()
            .unstack()
            * 100
        )
        yearly_csv = OUTPUT_DIR / f"{ticker}_vwap_lab_yearly.csv"
        yearly_stats.to_csv(yearly_csv)

    if update_ml_ready:
        df_ml_ready = load_local_data(ticker)
        if df_ml_ready is not None:
            for col in ["vwap_z_score", "vwap_dist_pct"]:
                df_ml_ready[col] = df[col]
            df_ml_ready.to_parquet(DATA_DIR / f"{ticker}.parquet", index=False)

    print(f"{ticker} processado. CSVs salvos em {OUTPUT_DIR}")


# =========================================================
# EXECUÇÃO EM PARALELO
# =========================================================
if __name__ == "__main__":
    arquivos = sorted(DATA_DIR.glob("*.parquet"))
    if not arquivos:
        print("Nenhum arquivo .parquet encontrado.")
        sys.exit(0)

    tickers = [f.stem for f in arquivos]
    print(f"Total de ativos encontrados: {len(tickers)}")

    max_workers = min(8, multiprocessing.cpu_count())  # Ajuste aqui conforme CPU

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_stress_lab, ticker): ticker for ticker in tickers}
        for future in as_completed(futures):
            ticker = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"Erro ao processar {ticker}: {e}")
