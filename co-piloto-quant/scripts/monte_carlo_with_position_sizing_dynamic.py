import pandas as pd
import numpy as np
from pathlib import Path
import argparse

# ==========================================================
# MONTE CARLO COM POSITION SIZING PROFISSIONAL (SEM ALAVANCAGEM)
# ==========================================================
# Regras:
# - Risco fixo por trade (risk_pct)
# - Exposição máxima realista (cap institucional)
# - Sem alavancagem implícita
# - Payoff proporcional à exposição
# - Block bootstrap para dependência temporal
# ==========================================================


def simulate_with_position_sizing(
    df,
    risk_pct=0.005,
    initial_capital=10000.0,
    num_simulations=5000,
    block_size=5,
    atr_multiple=3.0,
    min_position_pct=0.01,
    max_position_pct=0.08,  # CAP REALISTA (8%)
):
    final_returns = []
    max_drawdowns = []
    ruin_count = 0

    # DEBUG: posições da 1ª simulação
    avg_positions = []

    returns = df["return"].dropna().values

    if len(returns) < block_size:
        block_size = max(1, len(returns) // 2)

    # -------------------------------
    # Block Bootstrap
    # -------------------------------
    blocks = [
        list(range(i, min(i + block_size, len(returns))))
        for i in range(len(returns) - block_size + 1)
    ]

    for sim in range(num_simulations):
        sampled_indices = np.random.randint(
            0, len(blocks), size=len(returns) // block_size + 1
        )

        sampled_trade_indices = []
        for idx in sampled_indices:
            sampled_trade_indices.extend(blocks[idx])

        sampled_trade_indices = sampled_trade_indices[: len(returns)]

        equity = np.array([initial_capital])
        current_capital = initial_capital

        for trade_idx in sampled_trade_indices:
            ret = returns[trade_idx]

            price = float(df.iloc[trade_idx].get("price", 100.0))
            atr = float(df.iloc[trade_idx].get("atr", price * 0.02))

            # ===============================
            # POSITION SIZING BASEADO EM RISCO
            # ===============================
            risk_amount = current_capital * risk_pct
            stop_distance = atr * atr_multiple

            if stop_distance > 0 and price > 0:
                position_value = (risk_amount / stop_distance) * price
                position_size_pct = position_value / current_capital

                # CAP OPERACIONAL REALISTA
                position_size_pct = np.clip(
                    position_size_pct,
                    min_position_pct,
                    max_position_pct,
                )
            else:
                position_size_pct = min_position_pct

            if sim == 0:
                avg_positions.append(position_size_pct)

            # ===============================
            # PAYOFF REALISTA (SEM ALAVANCAGEM)
            # ===============================
            adjusted_return = ret * position_size_pct
            new_capital = current_capital * (1 + adjusted_return)

            if new_capital <= 0:
                new_capital = 0.01

            equity = np.append(equity, new_capital)
            current_capital = new_capital

        final_returns.append((equity[-1] / initial_capital) - 1)

        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / np.maximum(peak, 1e-10)
        max_drawdowns.append(np.nanmax(drawdown))

        if equity[-1] < initial_capital * 0.01:
            ruin_count += 1

    final_returns = np.array(final_returns)
    max_drawdowns = np.array(max_drawdowns)

    # -------------------------------
    # DEBUG POSITION SIZE
    # -------------------------------
    if len(avg_positions) > 0:
        avg_positions = np.array(avg_positions)
        print("\n🔍 DEBUG Position Size (1ª simulação):")
        print(f"  Média:    {avg_positions.mean():.2%}")
        print(f"  Mediana:  {np.median(avg_positions):.2%}")
        print(f"  Máx:      {avg_positions.max():.2%}")

    return {
        "final_returns": final_returns,
        "max_drawdowns": max_drawdowns,
        "p5_return": np.percentile(final_returns, 5),
        "p10_return": np.percentile(final_returns, 10),
        "p25_return": np.percentile(final_returns, 25),
        "median_return": np.percentile(final_returns, 50),
        "p75_return": np.percentile(final_returns, 75),
        "p90_return": np.percentile(final_returns, 90),
        "p95_return": np.percentile(final_returns, 95),
        "max_dd_p50": np.percentile(max_drawdowns, 50),
        "max_dd_p75": np.percentile(max_drawdowns, 75),
        "max_dd_p90": np.percentile(max_drawdowns, 90),
        "max_dd_p95": np.percentile(max_drawdowns, 95),
        "prob_ruin": ruin_count / num_simulations,
        "num_sims": num_simulations,
    }


# ==========================================================
# MAIN
# ==========================================================

def main():
    parser = argparse.ArgumentParser(
        description="Monte Carlo com Position Sizing Profissional (sem alavancagem)"
    )
    parser.add_argument("--regime", type=str, default="BULL_VOLATILE")
    parser.add_argument(
        "--input-file",
        type=Path,
        default=Path("momentum_all_regimes_results.csv"),
    )
    parser.add_argument("--simulations", type=int, default=5000)
    parser.add_argument("--initial-capital", type=float, default=10000.0)
    parser.add_argument("--atr-multiple", type=float, default=3.0)

    args = parser.parse_args()

    if not args.input_file.exists():
        print(f"❌ Arquivo não encontrado: {args.input_file}")
        return

    df = pd.read_csv(args.input_file)

    if "return" not in df.columns:
        print("❌ Coluna 'return' não encontrada")
        return

    # Filtra regime se existir
    for col in df.columns:
        if col.lower() in ["regime", "regime_name", "market_regime", "estrategia"]:
            df = df[df[col].str.upper().str.contains(args.regime.upper(), na=False)]
            break

    if len(df) == 0:
        print(f"❌ Nenhum trade encontrado para {args.regime}")
        return

    if "price" not in df.columns:
        df["price"] = 100.0
    if "atr" not in df.columns:
        df["atr"] = df["price"] * 0.02

    print("\n" + "=" * 80)
    print("MONTE CARLO COM POSITION SIZING PROFISSIONAL")
    print(f"Regime: {args.regime}")
    print("=" * 80)

    returns = df["return"].dropna().values
    print(f"Total trades: {len(returns)}")
    print(f"Win Rate: {(returns > 0).mean() * 100:.1f}%")
    print(f"Capital Inicial: ${args.initial_capital:,.2f}")

    result = simulate_with_position_sizing(
        df=df,
        risk_pct=0.005,
        initial_capital=args.initial_capital,
        num_simulations=args.simulations,
        atr_multiple=args.atr_multiple,
    )

    print("\nRESULTADOS DE ROBUSTEZ")
    print("=" * 80)
    print(f"P5 Retorno:      {result['p5_return']:+.2%}")
    print(f"Mediana Retorno: {result['median_return']:+.2%}")
    print(f"P95 Retorno:     {result['p95_return']:+.2%}")
    print(f"DD P90:          {result['max_dd_p90']:.2%}")
    print(f"Prob. Ruína:     {result['prob_ruin']*100:.2f}%")


if __name__ == "__main__":
    main()
