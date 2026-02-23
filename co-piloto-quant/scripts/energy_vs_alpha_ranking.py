import pandas as pd
import os

RESULTS_PATH = os.path.join(os.path.dirname(__file__), '../src/co_piloto_quant/data/results/energy_vs_alpha_report.csv')

def main():
    df = pd.read_csv(RESULTS_PATH)
    # Remove linhas sem alpha_top20 ou alpha_geral
    df = df.dropna(subset=["alpha_top20", "alpha_geral"])
    # Calcula o diferencial preditivo
    df["diff_pred"] = df["alpha_top20"] - df["alpha_geral"]
    # Para cada versão, pega o top 10 ativos com maior diff_pred
    ranking = {}
    for versao in sorted(df["versao"].unique()):
        df_v = df[df["versao"] == versao].copy()
        df_v = df_v.sort_values("diff_pred", ascending=False)
        ranking[versao] = df_v[["ativo", "alpha_top20", "alpha_geral", "diff_pred"]].head(10)

    # Exibe ranking de forma legível
    print("\nRANKING DOS ATIVOS COM MAIOR PODER PREDITIVO DE ALPHA POR VERSÃO:\n")
    for versao, df_rank in ranking.items():
        print(f"Versão {versao} (Top 10):")
        print(df_rank.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
        print("\n" + "-"*60 + "\n")

    # Salva ranking em CSVs separados por versão
    for versao, df_rank in ranking.items():
        out_path = os.path.join(os.path.dirname(RESULTS_PATH), f"energy_vs_alpha_ranking_{versao}.csv")
        df_rank.to_csv(out_path, index=False)
    print("Rankings salvos em arquivos CSV por versão.")

if __name__ == "__main__":
    main()