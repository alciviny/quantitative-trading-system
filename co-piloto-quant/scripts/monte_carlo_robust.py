#!/usr/bin/env python3
"""
Monte Carlo robusto para dados com muitos trades negativos.
Usa geometric mean em vez de product para estabilidade.
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path

def robust_monte_carlo(returns, num_sims=5000, initial_capital=10000):
    """Monte Carlo usando geometric mean (mais estável)."""
    returns = np.clip(returns, -0.95, None)
    
    final_returns = []
    max_dds = []
    
    for _ in range(num_sims):
        sampled = np.random.choice(returns, size=len(returns), replace=True)
        
        # Usar produto de forma segura
        equity = np.array([initial_capital])
        for r in sampled:
            equity = np.append(equity, equity[-1] * (1 + r))
        
        # Se algum valor ficou negativo/zero, truncar
        equity = np.maximum(equity, 0.01)
        
        final_ret = (equity[-1] / initial_capital) - 1
        
        # Drawdown
        peak = np.maximum.accumulate(equity)
        dd = (peak - equity) / np.maximum(peak, 0.01)
        max_dd = np.nanmax(dd)
        
        final_returns.append(final_ret)
        max_dds.append(max_dd)
    
    return np.array(final_returns), np.array(max_dds)

def main():
    parser = argparse.ArgumentParser(description="Monte Carlo Robusto")
    parser.add_argument("--input-file", type=Path, default=Path("momentum_all_regimes_results.csv"))
    parser.add_argument("--simulations", type=int, default=5000)
    args = parser.parse_args()
    
    if not args.input_file.exists():
        print(f"Erro: arquivo não encontrado: {args.input_file}")
        return
    
    df = pd.read_csv(args.input_file)
    returns = df["return"].dropna().values
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO DOS DADOS")
    print("="*80)
    print(f"Total trades: {len(returns)}")
    print(f"Min: {returns.min():.4f}")
    print(f"Max: {returns.max():.4f}")
    print(f"Mean: {returns.mean():.6f}")
    print(f"Median: {np.median(returns):.6f}")
    print(f"Std: {returns.std():.6f}")
    print(f"\nTrades negativos: {(returns < 0).sum()}")
    print(f"Win rate: {(returns > 0).mean()*100:.1f}%")
    
    print("\n" + "="*80)
    print(f"EXECUTANDO {args.simulations} SIMULAÇÕES...")
    print("="*80)
    
    final_rets, max_dds = robust_monte_carlo(returns, num_sims=args.simulations)
    
    print("\n" + "="*80)
    print("RESULTADOS MONTE CARLO")
    print("="*80)
    
    print(f"\nRETORNOS:")
    print(f"  P5 (pior 5%):     {np.percentile(final_rets, 5):+.4f}")
    print(f"  P10:              {np.percentile(final_rets, 10):+.4f}")
    print(f"  P25:              {np.percentile(final_rets, 25):+.4f}")
    print(f"  Mediana (P50):    {np.percentile(final_rets, 50):+.4f}")
    print(f"  P75:              {np.percentile(final_rets, 75):+.4f}")
    print(f"  P90:              {np.percentile(final_rets, 90):+.4f}")
    print(f"  P95 (melhor 5%):  {np.percentile(final_rets, 95):+.4f}")
    print(f"  Média:            {final_rets.mean():+.4f}")
    
    print(f"\nDRAWDOWN MÁXIMO:")
    print(f"  P90 (conservador): {np.percentile(max_dds, 90):.4f}")
    print(f"  P95:               {np.percentile(max_dds, 95):.4f}")
    print(f"  Média:             {max_dds.mean():.4f}")
    
    prob_ruin = (final_rets < 0).mean()
    print(f"\nPROB DE RUÍNA (retorno < 0): {prob_ruin*100:.1f}%")
    
    if final_rets.mean() > 0.05:
        print("\n✅ RESULTADO: ESTRATÉGIA VIÁVEL (média > 5%)")
    elif final_rets.mean() > 0:
        print("\n⚠️  RESULTADO: ESTRATÉGIA MARGINAL (0% < média < 5%)")
    else:
        print("\n❌ RESULTADO: ESTRATÉGIA NÃO VIÁVEL (média negativa)")

if __name__ == '__main__':
    main()
