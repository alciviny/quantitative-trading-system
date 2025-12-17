#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compare_stress_vs_wf.py
Compara resultados do stress test original vs walk-forward
Identifica onde está a divergência
"""

import pandas as pd
import numpy as np
from pathlib import Path

print("\n" + "="*70)
print("🔍 COMPARANDO STRESS TEST vs WALK-FORWARD")
print("="*70)

# Lê walk-forward results
wf_path = Path("walk_forward_results.csv")
if not wf_path.exists():
    print(f"\n❌ Arquivo {wf_path} não encontrado")
    exit(1)

df_wf = pd.read_parquet(wf_path) if str(wf_path).endswith('.parquet') else pd.read_csv(wf_path)

print(f"\n✓ Walk-Forward carregado: {len(df_wf)} trades")
print(f"  Colunas: {list(df_wf.columns)}")

# Análise do walk-forward
print("\n" + "="*70)
print("📊 WALK-FORWARD ANALYSIS")
print("="*70)

# Por fase
print("\nPOR FASE:")
for phase in ['TRAIN', 'TEST']:
    phase_df = df_wf[df_wf['phase'] == phase]
    if not phase_df.empty:
        avg = phase_df['return'].mean()
        wr = (phase_df['return'] > 0).mean()
        total = phase_df['return'].sum()
        count = len(phase_df)
        std = phase_df['return'].std()
        print(f"\n  {phase}:")
        print(f"    Trades:    {count}")
        print(f"    Avg Ret:   {avg:.4f}")
        print(f"    Total Ret: {total:.4f}")
        print(f"    Win Rate:  {wr:.1%}")
        print(f"    Std Dev:   {std:.4f}")

# Por regime (se existir)
if 'regime' in df_wf.columns:
    print("\n\nPOR REGIME (WF):")
    regime_stats = df_wf.groupby('regime')['return'].agg(['count', 'mean', 'sum'])
    regime_stats['win_rate'] = df_wf.groupby('regime')['return'].apply(lambda x: (x > 0).mean())
    print(regime_stats)

# Por janela
if 'window' in df_wf.columns:
    print("\n\nPOR JANELA (primeiras 5):")
    for window in sorted(df_wf['window'].unique())[:5]:
        window_df = df_wf[df_wf['window'] == window]
        
        train_df = window_df[window_df['phase'] == 'TRAIN']
        test_df = window_df[window_df['phase'] == 'TEST']
        
        print(f"\n  {window}:")
        if not train_df.empty:
            train_avg = train_df['return'].mean()
            train_wr = (train_df['return'] > 0).mean()
            train_cnt = len(train_df)
            print(f"    TRAIN: {train_cnt:3} | {train_avg:7.4f} | {train_wr:6.1%}")
        
        if not test_df.empty:
            test_avg = test_df['return'].mean()
            test_wr = (test_df['return'] > 0).mean()
            test_cnt = len(test_df)
            print(f"    TEST:  {test_cnt:3} | {test_avg:7.4f} | {test_wr:6.1%}")

# Análise do stress test original
print("\n\n" + "="*70)
print("📊 STRESS TEST ORIGINAL (do resultado que você mostrou)")
print("="*70)

original_results = {
    'BULL_CALM': {'trades': 74, 'avg_return': 0.028445, 'win_rate': 0.486486},
    'SIDEWAYS_VOLATILE': {'trades': 12, 'avg_return': 0.026750, 'win_rate': 0.583333},
    'SIDEWAYS_CALM': {'trades': 52, 'avg_return': 0.005449, 'win_rate': 0.269231},
    'BULL_VOLATILE': {'trades': 19, 'avg_return': 0.000156, 'win_rate': 0.210526},
}

total_trades_original = sum(r['trades'] for r in original_results.values())
avg_return_original = sum(r['trades'] * r['avg_return'] for r in original_results.values()) / total_trades_original

print(f"\nTOTAL: {total_trades_original} trades")
print(f"AVG RETURN GERAL: {avg_return_original:.4f}")

print("\n\nPOR REGIME:")
for regime, data in original_results.items():
    print(f"  {regime:20} | {data['trades']:3} trades | {data['avg_return']:.4f} | {data['win_rate']:.1%}")

# Comparação
print("\n\n" + "="*70)
print("⚖️ COMPARAÇÃO")
print("="*70)

print(f"\nTOTAL DE TRADES:")
print(f"  Stress Test Original: {total_trades_original}")
print(f"  Walk-Forward TRAIN:   {len(df_wf[df_wf['phase'] == 'TRAIN'])}")
print(f"  Walk-Forward TEST:    {len(df_wf[df_wf['phase'] == 'TEST'])}")
print(f"  Ratio WF/Original:    {len(df_wf) / total_trades_original:.2f}x")

print(f"\nRETORNO MÉDIO:")
print(f"  Stress Test Original: {avg_return_original:8.4f}")
print(f"  Walk-Forward TRAIN:   {df_wf[df_wf['phase'] == 'TRAIN']['return'].mean():8.4f}")
print(f"  Walk-Forward TEST:    {df_wf[df_wf['phase'] == 'TEST']['return'].mean():8.4f}")

# Hipóteses
print("\n\n" + "="*70)
print("🔬 POSSÍVEIS EXPLANAÇÕES")
print("="*70)

print("""
1. PERIOD SELECTION:
   - Stress Test: 2021-12-08 até TODAY (4 anos completos)
   - Walk-Forward: 40 janelas diferentes (treino separado de teste)
   
2. LOOKBACK PERIOD:
   - Stress Test pode usar todo histórico para indicadores
   - Walk-Forward treina com 6 meses (menos dados históricos)
   
3. MARKET CONDITIONS:
   - Stress Test pegou um período BULL (2021-2024)
   - Walk-Forward inclui períodos com diferentes regimes
   
4. REGIME FILTERING:
   - Stress Test filtra por regime (BULL_CALM é 74 trades)
   - Walk-Forward processa todos os regimes igualmente
   
5. PARAMETER OPTIMIZATION:
   - Parâmetros podem estar otimizados para a janela específica
   do stress test (2021-2024)
   - Não funcionam bem em outros períodos
""")

print("="*70)
