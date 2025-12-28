import sys
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing
import logging

# =========================================================
# SETUP DE IMPORTAÇÃO
# =========================================================
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.append(str(project_root / "src"))

# Importação dos módulos do sistema
from co_piloto_quant.data.data_manager import data_manager 
from co_piloto_quant.indicators.vwap_annual import AnnualVWAPAnalyst
from co_piloto_quant.indicators.special.hurst_exponent import calculate_rolling_hurst
from co_piloto_quant.indicators.special.market_entropy import calculate_rolling_entropy
from co_piloto_quant.indicators.special.half_life import calculate_rolling_ou_params

# =========================================================
# CONFIGURAÇÃO DO LAB
# =========================================================
DATA_ROOT = project_root / "src" / "co_piloto_quant" / "data"
OUTPUT_DIR = DATA_ROOT / "lab_outputs" / "regime_context"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

Z_BINS = [-np.inf, -2.0, -1.0, -0.5, 0.5, 1.0, 2.0, np.inf]
Z_LABELS = [
    "Extreme Cheap (<-2.0)",
    "Cheap (-2.0 a -1.0)",
    "Value Area Low (-1.0 a -0.5)",
    "Fair Value (-0.5 a 0.5)",
    "Value Area High (0.5 a 1.0)",
    "Expensive (1.0 a 2.0)",
    "Extreme Expensive (>2.0)"
]

HURST_WINDOW = 126
ENTROPY_WINDOW = 20
HALFLIFE_WINDOW = 60

# =========================================================
# LOGGING
# =========================================================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# =========================================================
# FUNÇÕES DE CÁLCULO
# =========================================================
def calculate_regimes(df: pd.DataFrame) -> pd.DataFrame:
    df['hurst'] = calculate_rolling_hurst(df['Close'], window=HURST_WINDOW, kind='returns')
    df['entropy'] = calculate_rolling_entropy(df['Close'], window=ENTROPY_WINDOW)
    ou_df = calculate_rolling_ou_params(df['Close'], window=HALFLIFE_WINDOW, strict_mode=False)
    hl_col = f'half_life_{HALFLIFE_WINDOW}'
    df['half_life'] = ou_df[hl_col] if hl_col in ou_df.columns else np.nan
    return df

def process_asset(ticker: str):
    ticker_yf = ticker.replace('_SA', '.SA')
    try:
        logging.info(f"Iniciando {ticker_yf} (original: {ticker})...")
        df = data_manager.get_data(ticker_yf)
        if df is None or df.empty:
            logging.warning(f"{ticker_yf}: Dataframe vazio.")
            return None

        logging.info(f"[{ticker_yf}] Tipo das colunas: {type(df.columns)}")
        logging.info(f"[{ticker_yf}] Conteúdo das colunas: {df.columns}")

        # --- Tratamento reforçado de colunas ---
        # 1. Achata tuplas
        new_cols = [col[0] if isinstance(col, tuple) else col for col in df.columns]
        df.columns = new_cols

        # 2. Padroniza nomes
        df.columns = [str(c).capitalize() for c in df.columns]

        # --- Garantir coluna Date ---
        if isinstance(df.index, pd.DatetimeIndex):
            df = df.reset_index().rename(columns={'index': 'Date'})
        else:
            df.reset_index(drop=True, inplace=True)
            if 'Date' not in df.columns:
                # Tenta identificar coluna de data pelo nome
                date_cols = [c for c in df.columns if 'date' in c.lower()]
                if date_cols:
                    df.rename(columns={date_cols[0]: 'Date'}, inplace=True)
                else:
                    logging.warning(f"{ticker_yf}: Coluna obrigatória Date não encontrada.")
                    return None

        # --- Manter apenas colunas essenciais, evitando múltiplas colunas ---
        essential_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        df_clean_cols = {}
        for col in essential_cols:
            if col in df.columns:
                # Se for DataFrame (múltiplas colunas com mesmo nome), pega apenas a primeira
                if isinstance(df[col], pd.DataFrame):
                    df_clean_cols[col] = df[col].iloc[:, 0]
                else:
                    df_clean_cols[col] = df[col]
        df = pd.DataFrame(df_clean_cols)

        # Verifica se todas as colunas essenciais existem
        for col in essential_cols:
            if col not in df.columns:
                logging.warning(f"{ticker_yf}: Coluna obrigatória {col} não encontrada.")
                return None

        if len(df) < (HURST_WINDOW + 50):
            logging.warning(f"{ticker_yf}: Dados insuficientes para cálculo.")
            return None

        # --- VWAP Annual ---
        try:
            analyst = AnnualVWAPAnalyst(price_col="Close")
            df = analyst.calculate(df)
        except Exception as e:
            logging.warning(f"{ticker_yf}: Falha no cálculo do VWAP. Erro: {e}")
            return None

        # --- Física de mercado ---
        df = calculate_regimes(df)

        # --- Categorização VWAP ---
        df["vwap_zone"] = pd.cut(df["vwap_z_score"], bins=Z_BINS, labels=Z_LABELS)

        # --- Limpeza e agregação ---
        cols_check = ['hurst', 'entropy', 'half_life', 'vwap_zone']
        df_clean = df.dropna(subset=cols_check)
        if df_clean.empty:
            return None

        stats = df_clean.groupby("vwap_zone", observed=False).agg(
            hurst_mean=('hurst', 'mean'),
            hurst_median=('hurst', 'median'),
            hurst_std=('hurst', 'std'),
            entropy_mean=('entropy', 'mean'),
            entropy_median=('entropy', 'median'),
            half_life_median=('half_life', 'median'),
            Close_count=('Close', 'count')
        )
        stats['ticker'] = ticker
        return stats.reset_index()

    except Exception as e:
        logging.error(f"Erro crítico em {ticker_yf}: {e}")
        return None

# =========================================================
# EXECUÇÃO
# =========================================================
def main():
    logging.info("=== Laboratório de Regimes Contextualizados ===")
    ml_path = project_root / "src" / "co_piloto_quant" / "data" / "ml_ready"
    arquivos = sorted(ml_path.glob("*.parquet"))
    tickers = [f.stem for f in arquivos]

    if not tickers:
        logging.error(f"Nenhum arquivo encontrado em {ml_path}")
        return

    all_results = []
    max_workers = min(8, multiprocessing.cpu_count())
    logging.info(f"Disparando {len(tickers)} ativos em {max_workers} processos...")

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_asset, t): t for t in tickers}
        for future in as_completed(futures):
            res = future.result()
            if res is not None:
                all_results.append(res)

    if not all_results:
        logging.warning("Nenhum resultado gerado.")
        return

    final_df = pd.concat(all_results, ignore_index=True)
    final_df.to_csv(OUTPUT_DIR / "vwap_regime_full_stats.csv", index=False)

    global_summary = final_df.groupby("vwap_zone", observed=False).agg({
        'hurst_mean': 'mean',
        'entropy_mean': 'mean',
        'half_life_median': 'mean',
        'Close_count': 'sum'
    })
    global_summary = global_summary.reindex(Z_LABELS)
    global_summary.to_csv(OUTPUT_DIR / "vwap_regime_global_summary.csv")

    logging.info("--- Análise Concluída ---")
    logging.info("Resumo das Médias Globais por Zona:")
    logging.info(f"\n{global_summary[['hurst_mean', 'entropy_mean', 'half_life_median']]}")

    try:
        plot_results(global_summary)
        logging.info(f"Gráfico salvo em {OUTPUT_DIR}")
    except Exception as e:
        logging.warning(f"Não foi possível gerar gráfico: {e}")

def plot_results(summary):
    fig, ax1 = plt.subplots(figsize=(12, 6))
    color = 'tab:blue'
    ax1.set_xlabel('Região do VWAP (Z-Score)')
    ax1.set_ylabel('Hurst Exponent (Média)', color=color)
    ax1.plot(summary.index, summary['hurst_mean'], color=color, marker='o', linewidth=2, label='Hurst')
    ax1.tick_params(axis='y', labelcolor=color)
    ax1.axhline(0.5, color='gray', linestyle='--', alpha=0.5, label='Random Walk (0.5)')

    ax2 = ax1.twinx()
    color = 'tab:red'
    ax2.set_ylabel('Market Entropy (Média)', color=color)
    ax2.plot(summary.index, summary['entropy_mean'], color=color, marker='s', linestyle=':', linewidth=2, label='Entropy')
    ax2.tick_params(axis='y', labelcolor=color)

    plt.title("Assinatura do Regime de Mercado vs Localização no VWAP")
    plt.grid(True, alpha=0.3)
    fig.tight_layout()
    plt.savefig(OUTPUT_DIR / "regime_structure_plot.png")

if __name__ == "__main__":
    main()
