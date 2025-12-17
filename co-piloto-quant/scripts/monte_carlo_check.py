import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def monte_carlo_simulation(
    returns,
    num_simulations=1000,
    seed=42,
    plot_paths=200
):
    """
    Monte Carlo por permutação de retornos (path-dependent).
    Mantém distribuição, destrói sequência.
    """

    np.random.seed(seed)
    returns = returns.dropna().values

    print(f"⚡ Rodando {num_simulations} simulações de Monte Carlo...")

    # Curva real
    original_curve = (1 + returns).cumprod()
    real_final = original_curve[-1]

    final_returns = []
    max_drawdowns = []

    plt.figure(figsize=(12, 6))

    # Curva real em destaque
    plt.plot(
        original_curve,
        color='red',
        linewidth=2.5,
        label='Sua Estratégia'
    )

    for i in range(num_simulations):
        shuffled = np.random.permutation(returns)
        curve = (1 + shuffled).cumprod()

        final_returns.append(curve[-1])

        # Drawdown
        peak = np.maximum.accumulate(curve)
        dd = (curve / peak - 1).min()
        max_drawdowns.append(dd)

        # Evita poluição visual
        if i < plot_paths:
            plt.plot(curve, color='gray', alpha=0.08)

    plt.title('Monte Carlo — Sequência vs Aleatoriedade')
    plt.yscale('log')
    plt.legend()
    plt.show()

    # =====================
    # Estatísticas
    # =====================
    final_returns = np.array(final_returns)
    max_drawdowns = np.array(max_drawdowns)

    prob_ruin = np.mean(final_returns < 1.0)

    p5, p50, p95 = np.percentile(final_returns, [5, 50, 95])

    print("\n📊 RESULTADOS MONTE CARLO")
    print("=" * 40)
    print(f"Chance de Ruína (<1.0x): {prob_ruin*100:.2f}%")
    print(f"Média Final: {final_returns.mean():.2f}x")
    print(f"Mediana: {p50:.2f}x")
    print(f"Pior 5%: {p5:.2f}x")
    print(f"Melhor 5%: {p95:.2f}x")
    print(f"Drawdown Médio: {max_drawdowns.mean()*100:.2f}%")
    print(f"Drawdown Pior Caso: {max_drawdowns.min()*100:.2f}%")
    print(f"\nSua Estratégia Real: {real_final:.2f}x")

    # =====================
    # Conclusão Quant
    # =====================
    if real_final > p95:
        print("✅ CONCLUSÃO: EDGE EXTREMAMENTE FORTE (Top 5%).")
    elif real_final > final_returns.mean():
        print("✅ CONCLUSÃO: EDGE REAL (Acima do aleatório).")
    else:
        print("❌ CONCLUSÃO: RESULTADO FRÁGIL (Possível sorte).")

    # =====================
    # Histograma
    # =====================
    plt.figure(figsize=(10, 4))
    plt.hist(final_returns, bins=50, alpha=0.7)
    plt.axvline(real_final, color='red', linewidth=2, label='Sua Estratégia')
    plt.title('Distribuição do Retorno Final (Monte Carlo)')
    plt.legend()
    plt.show()
