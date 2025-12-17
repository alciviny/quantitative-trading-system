#!/usr/bin/env python3
import pandas as pd
import numpy as np

df = pd.read_csv('walk_forward_results.csv')

print("\n" + "="*70)
print("📊 ANÁLISE: BULL_CALM APENAS (Stress Test vs Walk-Forward)")
print("="*70)

# Stress Test Original
print("\n🔬 STRESS TEST ORIGINAL - BULL_CALM:")
print("  Trades:     74")
print("  Avg Return: 2.84%")
print("  Win Rate:   48.6%")
print("  Total Return: 2.10% (soma dos retornos)")

# Walk-Forward - BULL_CALM apenas
print("\n\n🔄 WALK-FORWARD - BULL_CALM APENAS:")

df_bull = df[df['regime'] == 'BULL_CALM'].copy()

print(f"  Total Trades: {len(df_bull)}")
print(f"  Avg Return:   {df_bull['return'].mean():.4f} ({df_bull['return'].mean()*100:.2f}%)")
print(f"  Win Rate:     {(df_bull['return'] > 0).mean():.1%}")
print(f"  Total Return: {df_bull['return'].sum():.4f} ({df_bull['return'].sum()*100:.2f}%)")
print(f"  Std Dev:      {df_bull['return'].std():.4f}")

# Por fase
print("\n\n  POR FASE (BULL_CALM):")
for phase in ['TRAIN', 'TEST']:
    phase_df = df_bull[df_bull['phase'] == phase]
    if not phase_df.empty:
        avg = phase_df['return'].mean()
        wr = (phase_df['return'] > 0).mean()
        cnt = len(phase_df)
        total = phase_df['return'].sum()
        print(f"\n    {phase}:")
        print(f"      Trades:       {cnt}")
        print(f"      Avg Return:   {avg:.4f}")
        print(f"      Total Return: {total:.4f}")
        print(f"      Win Rate:     {wr:.1%}")

# Degradação
train_ret = df_bull[df_bull['phase'] == 'TRAIN']['return'].mean()
test_ret = df_bull[df_bull['phase'] == 'TEST']['return'].mean()

if train_ret != 0:
    deg = ((test_ret - train_ret) / abs(train_ret)) * 100
else:
    deg = 0

print(f"\n\n  DEGRADAÇÃO TREINO→TESTE: {deg:.2f}%")

# Por janela (BULL_CALM)
print(f"\n\n  PERFORMANCE POR JANELA (BULL_CALM):")
print("  " + "-"*60)

for window in sorted(df_bull['window'].unique()):
    window_df = df_bull[df_bull['window'] == window]
    
    train_df = window_df[window_df['phase'] == 'TRAIN']
    test_df = window_df[window_df['phase'] == 'TEST']
    
    train_count = len(train_df)
    test_count = len(test_df)
    
    if train_count > 0 or test_count > 0:
        print(f"\n  {window}:")
        if train_count > 0:
            train_avg = train_df['return'].mean()
            train_wr = (train_df['return'] > 0).mean()
            print(f"    TRAIN: {train_count:2} trades | {train_avg:7.4f} | {train_wr:5.0%} WR")
        else:
            print(f"    TRAIN: sem trades")
        
        if test_count > 0:
            test_avg = test_df['return'].mean()
            test_wr = (test_df['return'] > 0).mean()
            print(f"    TEST:  {test_count:2} trades | {test_avg:7.4f} | {test_wr:5.0%} WR", end="")
            
            if train_count > 0 and train_avg != 0:
                deg_window = ((test_avg - train_avg) / abs(train_avg)) * 100
                print(f" | deg: {deg_window:6.1f}%")
            else:
                print()
        else:
            print(f"    TEST:  sem trades")

# Estatísticas finais
print("\n\n" + "="*70)
print("📈 VEREDITO: USAR APENAS BULL_CALM?")
print("="*70)

total_bull = len(df_bull)
avg_bull = df_bull['return'].mean()
wr_bull = (df_bull['return'] > 0).mean()

print(f"\nEstatísticas BULL_CALM (todas as fases):")
print(f"  Trades:     {total_bull}")
print(f"  Avg Return: {avg_bull:.4f} ({avg_bull*100:.2f}%)")
print(f"  Win Rate:   {wr_bull:.1%}")

print(f"\nComparação com Stress Test:")
print(f"  Stress Test BULL_CALM:     2.84% (74 trades)")
print(f"  Walk-Forward BULL_CALM:    {avg_bull*100:.2f}% ({total_bull} trades)")

if avg_bull > 0:
    print(f"\n  ✅ POSITIVO! Funciona também no walk-forward")
    if abs(avg_bull - 0.0284) / 0.0284 < 0.3:  # 30% de diferença
        print(f"  ✅ CONSISTENTE! Resultado similar ao stress test")
    else:
        print(f"  ⚠️  DIFERENTE: Retorno menor que stress test")
else:
    print(f"\n  ❌ NEGATIVO: Perde dinheiro no walk-forward")

print("\n" + "="*70)
