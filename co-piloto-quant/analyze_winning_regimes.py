#!/usr/bin/env python3
"""
Analisa QUAIS REGIMES estão funcionando vs. quebrando.
Se encontrar um regime com Win Rate > 50%, você tem um ponto de partida.
"""

import pandas as pd
import numpy as np

df = pd.read_csv('momentum_all_regimes_results.csv')

print("\n" + "="*80)
print("ANÁLISE POR REGIME - PROCURANDO EDGE")
print("="*80)

for regime in sorted(df['regime'].unique()):
    regime_df = df[df['regime'] == regime]
    
    returns = regime_df['return'].values
    win_rate = (returns > 0).mean()
    
    if len(returns) < 10:
        continue
    
    mean_ret = returns.mean()
    median_ret = np.median(returns)
    std_ret = returns.std()
    
    # Profit Factor
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    pf = gains / losses if losses > 0 else 0
    
    print(f"\n{regime}")
    print(f"  Trades:       {len(returns)}")
    print(f"  Win Rate:     {win_rate*100:.1f}%")
    print(f"  Mean:         {mean_ret:+.4f}")
    print(f"  Median:       {median_ret:+.4f}")
    print(f"  Std Dev:      {std_ret:.4f}")
    print(f"  Profit Fact:  {pf:.2f}x")
    
    if win_rate > 0.55 and mean_ret > 0.01:
        print(f"  ✅ CANDIDATO FORTE!")
    elif win_rate > 0.50:
        print(f"  ⚠️  CANDIDATO MARGINAL")
    else:
        print(f"  ❌ NÃO VIÁVEL")

print("\n" + "="*80)
print("ANÁLISE GLOBAL")
print("="*80)

all_returns = df['return'].values
print(f"Total Trades: {len(all_returns)}")
print(f"Global Win Rate: {(all_returns > 0).mean()*100:.1f}%")
print(f"Global Mean: {all_returns.mean():+.6f}")
print(f"Global Median: {np.median(all_returns):+.6f}")

gains = all_returns[all_returns > 0].sum()
losses = abs(all_returns[all_returns < 0].sum())
global_pf = gains / losses if losses > 0 else 0
print(f"Global Profit Factor: {global_pf:.2f}x")

print("\n" + "="*80)
print("RECOMENDAÇÕES")
print("="*80)

regimes_good = []
for regime in sorted(df['regime'].unique()):
    regime_df = df[df['regime'] == regime]
    returns = regime_df['return'].values
    if len(returns) >= 10:
        wr = (returns > 0).mean()
        mr = returns.mean()
        if wr > 0.52 and mr > 0.002:
            regimes_good.append(regime)

if regimes_good:
    print(f"\n✅ Regimes viáveis encontrados:")
    for r in regimes_good:
        print(f"    - {r}")
    print(f"\nPróximo passo: Operar APENAS nestes regimes")
else:
    print(f"\n❌ Nenhum regime com Win Rate + Edge suficiente")
    print(f"Próximo passo: Redesign da estratégia")
    print(f"  - Aumentar Profit Target (3.0x → 4.0x ou 5.0x ATR)")
    print(f"  - Diminuir Stop Loss (2.5x → 1.5x ou 2.0x ATR)")
    print(f"  - Adicionar mais filtros de entrada")
