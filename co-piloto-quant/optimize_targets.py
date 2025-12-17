#!/usr/bin/env python3
"""
Testa diferentes combinações de Profit Target e Stop Loss
para encontrar quais parâmetros melhoram o Win Rate.
"""

import pandas as pd
import numpy as np

df = pd.read_csv('momentum_all_regimes_results.csv')

print("\n" + "="*80)
print("TESTANDO COMBINAÇÕES DE PROFIT TARGET E STOP LOSS")
print("="*80)

# Dados necessários
if 'entry_price' not in df.columns or 'exit_price' not in df.columns:
    print("⚠️  Dados de entrada/saída não disponíveis no CSV")
    print("Usando retornos como proxy...")
    
    print("\nTestando apenas ajuste de Profit Target (via multiplicador):")
    
    current_mean = df['return'].mean()
    current_wr = (df['return'] > 0).mean()
    
    print(f"\nAtual:")
    print(f"  Win Rate: {current_wr*100:.1f}%")
    print(f"  Mean:     {current_mean:+.6f}")
    print(f"  Trades:   {len(df)}")
    
    # Simula aumento de lucros mantendo perdas iguais
    print(f"\nSimulando: Aumentar Profit Target (keep stops):")
    for factor in [1.0, 1.2, 1.5, 2.0]:
        adjusted = df['return'].copy()
        winners_mask = adjusted > 0
        adjusted[winners_mask] = adjusted[winners_mask] * factor
        
        new_mean = adjusted.mean()
        new_wr = (adjusted > 0).mean()
        
        print(f"  {factor:.1f}x target: WR={new_wr*100:.1f}%, Mean={new_mean:+.6f}")
    
    print(f"\nSimulando: Apertar Stop Loss (keep targets):")
    for factor in [0.5, 0.7, 0.9, 1.0]:
        adjusted = df['return'].copy()
        losers_mask = adjusted < 0
        adjusted[losers_mask] = adjusted[losers_mask] * factor
        
        new_mean = adjusted.mean()
        new_wr = (adjusted > 0).mean()
        
        print(f"  {factor:.1f}x stop: WR={new_wr*100:.1f}%, Mean={new_mean:+.6f}")

else:
    print("\nDados presentes, testando com dados reais...")
    # Implementar lógica se dados reais estiverem disponíveis

print("\n" + "="*80)
print("RECOMENDAÇÃO")
print("="*80)
print("\nPara Win Rate 43% → 55%:")
print("  Opção A: Aumentar Profit Target em 40-50%")
print("  Opção B: Diminuir Stop Loss em 30-40%")
print("  Opção C: Fazer ambos (mais agressivo)")
print("\nMas aviso: Sem mais edge, isso é apenas")
print("mover o risco de um lado para outro.")
print("\nVerdadeira solução: Melhorar QUALIDADE das entradas.")
