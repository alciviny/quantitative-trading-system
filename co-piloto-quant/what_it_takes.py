#!/usr/bin/env python3
"""
REALITY CHECK: O que a estratégia precisa para sair da ruína?
"""

import pandas as pd
import numpy as np

df = pd.read_csv('momentum_all_regimes_results.csv')
returns = df['return'].values

print("\n" + "="*80)
print("REALITY CHECK: O QUE VOCÊ PRECISA?")
print("="*80)

current_wr = (returns > 0).mean()
current_mean = returns.mean()
current_median = np.median(returns)

print(f"\nESTADO ATUAL:")
print(f"  Win Rate:  {current_wr*100:.1f}%")
print(f"  Mean:      {current_mean:+.6f}")
print(f"  Median:    {current_median:+.6f}")
print(f"  Prob Ruína: 85.8%")

print(f"\n" + "="*80)
print(f"CENÁRIO 1: Aumentar Win Rate")
print(f"="*80)

for target_wr in [0.50, 0.55, 0.60, 0.65]:
    # Simulação simples: muda Win Rate mantendo distribuição
    n_trades = len(returns)
    n_winners_needed = int(n_trades * target_wr)
    n_losers = n_trades - n_winners_needed
    
    # Pega top winners e bottom losers
    sorted_ret = np.sort(returns)
    winners = sorted_ret[-n_winners_needed:]
    losers = sorted_ret[:n_losers]
    
    new_mean = np.mean(np.concatenate([winners, losers]))
    
    print(f"\n  Win Rate {target_wr*100:.0f}%:")
    print(f"    Novo Mean: {new_mean:+.6f}")
    if new_mean > 0.01:
        print(f"    ✅ Viável!")
    else:
        print(f"    ⚠️  Ainda insuficiente")

print(f"\n" + "="*80)
print(f"CENÁRIO 2: Aumentar Profit Target (3x → Nx ATR)")
print(f"="*80)

for multiplier in [1.5, 2.0, 3.0, 5.0]:
    # Simula aumento de lucros
    adjusted = returns.copy()
    winners_mask = adjusted > 0
    
    # Assumindo que Target = média dos ganhos
    avg_win = adjusted[winners_mask].mean()
    adjusted[winners_mask] = avg_win * multiplier
    
    new_mean = adjusted.mean()
    new_wr = (adjusted > 0).mean()
    
    print(f"\n  Profit Target {multiplier:.1f}x:")
    print(f"    Mean: {new_mean:+.6f}")
    print(f"    WR:   {new_wr*100:.1f}%")
    if new_mean > 0.01:
        print(f"    ✅ Potencialmente viável!")

print(f"\n" + "="*80)
print(f"CENÁRIO 3: Apertar Stop Loss (2.5x → Nx ATR)")
print(f"="*80)

for multiplier in [0.3, 0.5, 0.7, 0.9]:
    # Simula redução de perdas
    adjusted = returns.copy()
    losers_mask = adjusted < 0
    
    avg_loss = abs(adjusted[losers_mask].mean())
    adjusted[losers_mask] = -(avg_loss * multiplier)
    
    new_mean = adjusted.mean()
    new_wr = (adjusted > 0).mean()
    
    print(f"\n  Stop Loss {multiplier:.1f}x:")
    print(f"    Mean: {new_mean:+.6f}")
    print(f"    WR:   {new_wr*100:.1f}%")
    if new_mean > 0.01:
        print(f"    ✅ Potencialmente viável!")

print(f"\n" + "="*80)
print(f"DIAGNÓSTICO FINAL")
print(f"="*80)

print(f"""
Sua estratégia PRECISA DE UMA (OU MAIS) DESTAS MUDANÇAS:

1. Win Rate 43% → 55%+
   Implica: Melhor entrada ou mais filtros
   Dificuldade: ALTA (requer redesign)

2. Profit Target +50-100%
   Implica: Deixar lucros correram mais
   Dificuldade: MÉDIA (teste parâmetros)

3. Stop Loss -40-50%
   Implica: Sair rápido de trades ruins
   Dificuldade: MÉDIA (mas pode aumentar False Positives)

4. Combinação de 2 + 3
   Melhor abordagem: Fazer ambos moderadamente

RECOMENDAÇÃO:
  Próximas ações em ordem:
  ✅ 1. Rodar analyze_winning_regimes.py
  ✅ 2. Rodar pareto_analysis.py
  ✅ 3. Testar novos parâmetros (PT 5.0x, SL 1.5x)
  ✅ 4. Se nada funcionar: Voltar ao drawing board
""")
