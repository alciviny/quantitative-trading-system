#!/usr/bin/env python3
"""
Análise Pareto: O que diferencia traders vencedores de perdedores?
Se conseguirmos filtrar por uma característica que aumenta WR de 43% → 55%+, achamos o filtro.
"""

import pandas as pd
import numpy as np

df = pd.read_csv('momentum_all_regimes_results.csv')

winners = df[df['return'] > 0]
losers = df[df['return'] <= 0]

print("\n" + "="*80)
print("ANÁLISE PARETO - O QUE DIFERENCIA VENCEDORES DE PERDEDORES?")
print("="*80)

print(f"\nWINNERS ({len(winners)} trades, {len(winners)/len(df)*100:.1f}%):")
print(f"  Mean return:   {winners['return'].mean():+.6f}")
print(f"  Median return: {winners['return'].median():+.6f}")
print(f"  Max return:    {winners['return'].max():+.6f}")
print(f"  Std dev:       {winners['return'].std():.6f}")

print(f"\nLOSERS ({len(losers)} trades, {len(losers)/len(df)*100:.1f}%):")
print(f"  Mean return:   {losers['return'].mean():+.6f}")
print(f"  Median return: {losers['return'].median():+.6f}")
print(f"  Min return:    {losers['return'].min():+.6f}")
print(f"  Std dev:       {losers['return'].std():.6f}")

print("\n" + "="*80)
print("DIFERENÇAS ESTATÍSTICAS")
print("="*80)

cols_to_compare = [col for col in df.columns if col not in ['ticker', 'regime', 'return', 'win', 'reason', 'sinal_tipo']]

differences = []
for col in cols_to_compare:
    if col in df.columns and df[col].dtype in ['float64', 'int64']:
        try:
            w_mean = winners[col].mean()
            l_mean = losers[col].mean()
            diff = abs(w_mean - l_mean)
            pct_diff = (diff / max(abs(w_mean), abs(l_mean), 1e-6)) * 100
            
            differences.append({
                'column': col,
                'winner_mean': w_mean,
                'loser_mean': l_mean,
                'abs_diff': diff,
                'pct_diff': pct_diff
            })
        except:
            pass

diff_df = pd.DataFrame(differences).sort_values('pct_diff', ascending=False)

print("\nTop Diferenças (pct):")
for idx, row in diff_df.head(10).iterrows():
    col = row['column']
    print(f"  {col:20} | Winners: {row['winner_mean']:8.4f} | Losers: {row['loser_mean']:8.4f} | Diff: {row['pct_diff']:6.1f}%")

print("\n" + "="*80)
print("SUGESTÃO DE FILTRO")
print("="*80)

# Procura por padrões
if 'days_held' in df.columns:
    w_days = winners['days_held'].mean()
    l_days = losers['days_held'].mean()
    print(f"\nDias em trade:")
    print(f"  Winners: {w_days:.1f} dias | Losers: {l_days:.1f} dias")
    if w_days < l_days:
        print(f"  💡 Sugestão: Reduzir Max Hold Days (trades rápidos ganham mais)")

if 'regime' in df.columns:
    print(f"\nTaxas de acerto por regime:")
    for regime in sorted(df['regime'].unique()):
        regime_trades = df[df['regime'] == regime]
        wr = (regime_trades['return'] > 0).mean()
        n = len(regime_trades)
        print(f"  {regime:20} {wr*100:5.1f}% ({n:4} trades)")

print("\n" + "="*80)
print("CONCLUSÃO")
print("="*80)
print(f"\nWin Rate global: {(df['return'] > 0).mean()*100:.1f}%")
print(f"Precisa aumentar para: > 55% ou melhorar Risk-Reward")
print(f"\nOpções:")
print(f"  1. Filtrar mais (regime específico)")
print(f"  2. Aumentar Profit Target (deixar lucrar mais)")
print(f"  3. Diminuir Stop Loss (sair mais rápido de trades ruins)")
print(f"  4. Adicionar confirmação extra (MACD + RSI, por exemplo)")
