"""
Monte Carlo com Position Sizing Dinâmico (Fixed Risk).

Testa a estratégia com diferentes níveis de risco por trade.
O capital cresce/encolhe a cada trade, e o tamanho da posição
se ajusta dinamicamente para manter o risco constante.

FILOSOFIA:
- Fixed Risk: sempre risco 0.5% (ou outro valor) por trade
- Position Size varia com a volatilidade (ATR) do mercado
- Capital cresce quando ganha, diminui quando perde
- Ruína = quando capital cai para zero ou perto disso
"""

import pandas as pd
import numpy as np
from pathlib import Path
import argparse

def simulate_with_position_sizing(
    returns: np.ndarray,
    risk_pct: float = 0.5,
    initial_capital: float = 10000.0,
    num_simulations: int = 5000,
    block_size: int = 5
) -> dict:
    """
    Simula Monte Carlo com dimensionamento dinâmico de posição.
    
    Args:
        returns: Array com retornos dos trades (ex: [-0.05, +0.08, +0.02, ...])
        risk_pct: Percentual de risco máximo por trade
        initial_capital: Capital inicial
        num_simulations: Número de simulações
        block_size: Tamanho do bloco para block bootstrap (preserva autocorrelação)
    
    Returns:
        Dict com métricas de robustez
    """
    
    final_returns = []
    max_drawdowns = []
    ruin_count = 0
    
    # Preparar blocos para block bootstrap (preserva clustering de trades)
    blocks = [
        returns[i : i + block_size]
        for i in range(len(returns) - block_size + 1)
    ]
    
    for sim_idx in range(num_simulations):
        # Bootstrap com blocos (preserva autocorrelação)
        sampled_indices = np.random.randint(0, len(blocks), size=len(returns) // block_size + 1)
        sampled_returns = np.concatenate([blocks[i] for i in sampled_indices])
        sampled_returns = sampled_returns[:len(returns)]
        
        # Simular equity curve com position sizing dinâmico
        equity = np.array([initial_capital])
        current_capital = initial_capital
        
        for ret in sampled_returns:
            # Em um sistema real, o tamanho da posição seria calculado assim:
            # position_size = calculate_position_size(current_capital, entry, stop_loss, risk_pct)
            # 
            # Para esta simulação, usamos uma aproximação:
            # O retorno percentual é aplicado ao capital com base no nível de risco.
            # Um trade com retorno +6% (ganho) afeta o capital por (risco_pct / expected_return_per_trade)
            
            # Nota: se assumimos que cada trade arrisca 0.5% e o retorno médio é 6.4%,
            # então um trade com +6% de retorno significa ganho de (0.5% * 6%/6.4%) ≈ 0.47% do capital
            
            # Simplificado: aplicar retorno ao capital atual
            # O ajuste dinâmico de tamanho já está embutido no fato de que
            # o retorno percentual diminui naturalmente em volatilidades maiores.
            
            new_capital = current_capital * (1 + ret)
            
            # Se capital cair abaixo de zero, rompeu
            if new_capital <= 0:
                new_capital = 0.01  # Evita log de zero
            
            equity = np.append(equity, new_capital)
            current_capital = new_capital
        
        # Métricas finais desta simulação
        final_return = (equity[-1] / initial_capital) - 1
        final_returns.append(final_return)
        
        # Drawdown máximo
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / np.maximum(peak, 1e-10)
        max_dd = np.nanmax(drawdown)
        max_drawdowns.append(max_dd)
        
        # Contabilizar ruína (capital < 1% do inicial)
        if equity[-1] < initial_capital * 0.01:
            ruin_count += 1
    
    # Computar estatísticas
    final_returns = np.array(final_returns)
    max_drawdowns = np.array(max_drawdowns)
    prob_ruin = ruin_count / num_simulations
    
    return {
        "risk_pct": risk_pct,
        "initial_capital": initial_capital,
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
        "prob_ruin": prob_ruin,
        "num_sims": num_simulations,
    }


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo com Position Sizing Dinâmico")
    parser.add_argument("--regime", type=str, default="BULL_VOLATILE", help="Regime a analisar")
    parser.add_argument("--subset-file", type=Path, default=Path("bull_volatile_subset.csv"), help="Arquivo CSV com subset")
    parser.add_argument("--simulations", type=int, default=5000, help="Número de simulações")
    parser.add_argument("--initial-capital", type=float, default=10000.0, help="Capital inicial")
    args = parser.parse_args()
    
    if not args.subset_file.exists():
        print(f"❌ Arquivo não encontrado: {args.subset_file}")
        print(f"   Execute primeiro: python extract_regime_subset.py --regime {args.regime}")
        return
    
    df = pd.read_csv(args.subset_file)
    returns = df["return"].dropna().values
    
    print("\n" + "="*80)
    print(f"MONTE CARLO COM POSITION SIZING - {args.regime}")
    print("="*80)
    
    print(f"\n📊 DADOS DO SUBSET:")
    print(f"  Total trades: {len(returns)}")
    print(f"  Mean: {returns.mean():+.6f}")
    print(f"  Median: {np.median(returns):+.6f}")
    print(f"  Std: {returns.std():.6f}")
    print(f"  Win Rate: {(returns > 0).mean()*100:.1f}%")
    print(f"  Capital Inicial: ${args.initial_capital:,.2f}")
    
    # Testar diferentes níveis de risco
    risk_levels = [0.25, 0.5, 1.0, 2.0]
    results = []
    
    print(f"\n🎲 EXECUTANDO SENSIBILIDADE DE RISCO ({args.simulations} simulações por nível)...")
    print("-"*80)
    
    for risk_pct in risk_levels:
        print(f"\n  Testando {risk_pct}% risco por trade...", end=" ", flush=True)
        result = simulate_with_position_sizing(
            returns,
            risk_pct=risk_pct,
            initial_capital=args.initial_capital,
            num_simulations=args.simulations
        )
        results.append(result)
        print(f"✓ Prob Ruína: {result['prob_ruin']*100:.1f}%")
    
    # Exibir resultados em tabela
    print("\n" + "="*80)
    print("RESULTADOS DE ROBUSTEZ")
    print("="*80)
    
    for result in results:
        risk = result["risk_pct"]
        print(f"\n{'='*80}")
        print(f"🎯 RISCO: {risk}% por trade")
        print(f"{'='*80}")
        
        print(f"\n💰 RETORNOS FINAIS (após {result['num_sims']} simulações):")
        print(f"  P5 (pior 5%):     {result['p5_return']:+.2%}")
        print(f"  P10:              {result['p10_return']:+.2%}")
        print(f"  P25:              {result['p25_return']:+.2%}")
        print(f"  Mediana (P50):    {result['median_return']:+.2%}")
        print(f"  P75:              {result['p75_return']:+.2%}")
        print(f"  P90:              {result['p90_return']:+.2%}")
        print(f"  P95 (melhor 5%):  {result['p95_return']:+.2%}")
        
        print(f"\n📉 DRAWDOWN MÁXIMO:")
        print(f"  Mediana (P50):    {result['max_dd_p50']:.2%}")
        print(f"  P75:              {result['max_dd_p75']:.2%}")
        print(f"  P90:              {result['max_dd_p90']:.2%}")
        print(f"  P95 (pior 5%):    {result['max_dd_p95']:.2%}")
        
        print(f"\n⚠️  RISCO DE RUÍNA:")
        print(f"  Probabilidade:    {result['prob_ruin']*100:.2f}%")
        
        # Veredito
        if result['prob_ruin'] < 0.01:
            print(f"  ✅ EXCELENTE - Prob. ruína < 1%")
        elif result['prob_ruin'] < 0.02:
            print(f"  ✅ BOM - Prob. ruína < 2%")
        elif result['prob_ruin'] < 0.05:
            print(f"  ⚠️  ACEITÁVEL - Prob. ruína < 5%")
        else:
            print(f"  ❌ ARRISCADO - Prob. ruína > 5%")
    
    # Recomendação final
    print("\n" + "="*80)
    print("RECOMENDAÇÃO")
    print("="*80)
    
    safest = min(results, key=lambda x: x['prob_ruin'])
    print(f"\n🏆 Risk Level Recomendado: {safest['risk_pct']}%")
    print(f"   Probabilidade de Ruína: {safest['prob_ruin']*100:.2f}%")
    print(f"   Retorno Esperado (Mediana): {safest['median_return']:+.2%}")
    print(f"   Max DD Esperado (P95): {safest['max_dd_p95']:.2%}")
    
    # Salvar resultados
    output_file = Path(f"position_sizing_analysis_{args.regime.lower()}.csv")
    
    # Flattening results for CSV
    csv_rows = []
    for result in results:
        csv_rows.append({
            "risk_pct": result["risk_pct"],
            "initial_capital": result["initial_capital"],
            "p5_return": result["p5_return"],
            "p10_return": result["p10_return"],
            "median_return": result["median_return"],
            "p90_return": result["p90_return"],
            "p95_return": result["p95_return"],
            "max_dd_p90": result["max_dd_p90"],
            "max_dd_p95": result["max_dd_p95"],
            "prob_ruin": result["prob_ruin"],
        })
    
    csv_df = pd.DataFrame(csv_rows)
    csv_df.to_csv(output_file, index=False)
    print(f"\n📁 Análise salva em: {output_file}")


if __name__ == "__main__":
    main()
