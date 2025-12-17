# -*- coding: utf-8 -*-
"""
analyze_parameters.py
Analisa os parâmetros da estratégia para identificar melhorias
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("\n" + "="*80)
print("🔍 ANÁLISE DE PARÂMETROS - OPORTUNIDADES DE MELHORIA")
print("="*80)

df = pd.read_csv('walk_forward_extended_results.csv')

print("\n📊 PERFORMANCE GERAL:")
train_all = df[df['phase'] == 'TRAIN']
test_all = df[df['phase'] == 'TEST']

print(f"  Train: {len(train_all)} trades | {train_all['return'].mean():+.4f} ret | {(train_all['win'].mean()):.1%} WR")
print(f"  Test:  {len(test_all)} trades | {test_all['return'].mean():+.4f} ret | {(test_all['win'].mean()):.1%} WR")

# Análise: Qual regime melhoraria com menos restrições?
print("\n📈 ANÁLISE POR REGIME (Potencial de Melhoria):")
print("-"*80)

for regime in sorted(df['regime'].unique()):
    regime_df = df[df['regime'] == regime]
    train_r = regime_df[regime_df['phase'] == 'TRAIN']
    test_r = regime_df[regime_df['phase'] == 'TEST']
    
    if len(train_r) == 0:
        continue
    
    train_ret = train_r['return'].mean()
    train_wr = (train_r['win'].mean())
    test_ret = test_r['return'].mean() if len(test_r) > 0 else 0
    test_trades = len(test_r)
    
    # Indicadores de qualidade
    wins = (train_r['return'] > 0).sum()
    losses = (train_r['return'] < 0).sum()
    
    # Win rate e avg win/loss
    avg_win = train_r[train_r['return'] > 0]['return'].mean() if wins > 0 else 0
    avg_loss = train_r[train_r['return'] < 0]['return'].mean() if losses > 0 else 0
    
    # Profit factor
    gross_wins = train_r[train_r['return'] > 0]['return'].sum()
    gross_losses = abs(train_r[train_r['return'] < 0]['return'].sum())
    pf = gross_wins / gross_losses if gross_losses > 0 else 0
    
    status = "✅" if train_ret > 0 and train_wr > 0.35 else "⚠️ " if train_wr > 0.30 else "❌"
    
    print(f"\n{status} {regime:20s}")
    print(f"   Train: {len(train_r):3} trades | {train_ret:+.4f} ret | {train_wr:6.1%} WR | PF: {pf:.2f}x")
    print(f"   Test:  {len(test_r):3} trades | {test_ret:+.4f} ret | {(test_r['win'].mean() if len(test_r)>0 else 0):.1%} WR")
    print(f"   Avg Win/Loss: {avg_win:+.4f} / {avg_loss:+.4f}")

# Análise: Exit reasons
print("\n\n⚠️  ANÁLISE DE EXITS (Por quê os trades fecham):")
print("-"*80)

exit_analysis = df[df['phase'] == 'TRAIN'].groupby('reason').agg({
    'return': ['mean', 'count', lambda x: (x > 0).mean()]
}).round(4)

exit_analysis.columns = ['Avg Return', 'Count', 'Win Rate']
exit_analysis = exit_analysis.sort_values('Avg Return', ascending=False)

print(exit_analysis)

# Análise: Half-life
print("\n\n🔄 ANÁLISE DE HALF-LIFE (Qualidade das reversões):")
print("-"*80)

hl_bins = [0, 5, 10, 15, 20, 25, 30, 50]
df['hl_bucket'] = pd.cut(df['halflife_entrada'], bins=hl_bins)

hl_analysis = df[df['phase'] == 'TRAIN'].groupby('hl_bucket').agg({
    'return': ['mean', 'count', lambda x: (x > 0).mean()]
}).round(4)

hl_analysis.columns = ['Avg Return', 'Count', 'Win Rate']
print(hl_analysis)
print("\n   📍 Conclusão: HL > 25 traz trades ruins? Ou HL < 10 é melhor?")

# Análise: Hurst vs performance
print("\n\n📊 ANÁLISE DE HURST (Mean Reversion Signal):")
print("-"*80)

hurst_bins = [0.45, 0.48, 0.50, 0.52, 0.55]
df['hurst_bucket'] = pd.cut(df['hurst_entrada'], bins=hurst_bins)

hurst_analysis = df[df['phase'] == 'TRAIN'].groupby('hurst_bucket').agg({
    'return': ['mean', 'count', lambda x: (x > 0).mean()]
}).round(4)

hurst_analysis.columns = ['Avg Return', 'Count', 'Win Rate']
print(hurst_analysis)
print("\n   📍 Nota: Hurst = 0.5 significa dados não suficientes")
print("   💡 Extended lookback deveria calcular melhor, mas ainda está em 0.5")

# Recomendações
print("\n\n" + "="*80)
print("🎯 RECOMENDAÇÕES PARA REDESENHO:")
print("="*80)

print("""
1. **REMOVER only_bull_market=True**
   - Está rejeitando SIDEWAYS_VOLATILE (melhor regime: 55% WR, +3.36%)
   - Bear market trading pode ser viável
   - Custo: permite mais trades ruins em BEAR_CALM, mas ganho em SIDEWAYS

2. **AUMENTAR max_half_life de 25 para 35-40**
   - Mean reversion muito rápida pode estar perdendo trades bons
   - Check: trades com HL > 25 realmente são piores?

3. **REDUZIR rsi_period de 120 para 60**
   - RSI muito longo pode estar perdendo reversões rápidas
   - Período 60 é comum para mean reversion

4. **REMOVER use_regime_filter ou suavizar**
   - Está bloqueando muitas oportunidades
   - Testar: manter apenas os filtros mais importantes

5. **TESTAR BB_STD menor (1.0 vs 1.5)**
   - Bandas mais apertadas = mais sinais, pode encontrar melhor WR

6. **INVESTIGAR HURST**
   - Indicador está em 0.5 (default) - não está calculando corretamente
   - Verificar se 12 meses é realmente suficiente
   - Pode estar bloqueando boas oportunidades (Hurst > 0.5 = trend, < 0.5 = mean reversion)
""")

print("\n" + "="*80)
print("💻 PRÓXIMO PASSO: Testar combinações de parâmetros com walk-forward")
print("="*80)
