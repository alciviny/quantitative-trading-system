#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_atr_multipliers.py
Testa diferentes ATR multipliers para encontrar stop loss ideal
"""

import subprocess
import sys
import pandas as pd
from pathlib import Path

atr_multipliers = [2.0, 2.5, 3.0, 3.5]
results = []

print("\n" + "="*80)
print("TESTANDO ATR MULTIPLIERS PARA OTIMIZAR STOPS")
print("="*80)

for atr_mult in atr_multipliers:
    print(f"\n[TEST] ATR_MULT = {atr_mult}x")
    print("-" * 80)
    
    output_file = f"swing_bear_calm_atr_{atr_mult}.csv"
    
    cmd = [
        sys.executable,
        "scripts/validate_swing_bear_calm.py",
        "--atr-mult", str(atr_mult),
        "--out", output_file
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600, cwd=".")
        
        if result.returncode != 0:
            print(f"  [ERROR] Erro na execução:")
            print(f"     {result.stderr[:200]}")
            continue
        
        if not Path(output_file).exists():
            print(f"  [ERROR] Arquivo não gerado: {output_file}")
            continue
            
        df = pd.read_csv(output_file)
        
        train = df[df['phase'] == 'TRAIN']
        test = df[df['phase'] == 'TEST']
        
        if len(train) > 0 and len(test) > 0:
            train_ret = train['return'].mean()
            test_ret = test['return'].mean()
            train_wr = (train['return'] > 0).mean()
            test_wr = (test['return'] > 0).mean()
            
            gains = train[train['return'] > 0]['return'].sum()
            losses = abs(train[train['return'] < 0]['return'].sum())
            pf = gains / losses if losses > 0 else 0
            
            deg = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
            
            results.append({
                'atr_mult': atr_mult,
                'train_trades': len(train),
                'test_trades': len(test),
                'train_ret': train_ret,
                'test_ret': test_ret,
                'train_wr': train_wr,
                'test_wr': test_wr,
                'pf': pf,
                'degradation': deg
            })
            
            print(f"  [OK] Train: {len(train):4} trades | {train_ret:+.4f} ret | {train_wr:.1%} WR | PF: {pf:.2f}x")
            print(f"       Test:  {len(test):4} trades | {test_ret:+.4f} ret | {test_wr:.1%} WR")
            print(f"       Degradacao: {deg:+.1f}%")
        else:
            print(f"  [WARN] Sem trades gerados")
    except Exception as e:
        print(f"  [ERROR] Erro: {str(e)[:100]}")

# Resumo comparativo
print("\n" + "="*80)
print("COMPARATIVO DE MULTIPLIERS")
print("="*80)

if results:
    df_results = pd.DataFrame(results)
    print("\n" + df_results.to_string(index=False))
    
    # Buscar melhor
    best_test_ret = df_results.loc[df_results['test_ret'].idxmax()]
    best_pf = df_results.loc[df_results['pf'].idxmax()]
    best_consistency = df_results.loc[df_results['degradation'].abs().idxmin()]
    
    print("\n[RECOMENDACOES]:")
    print(f"  Melhor Retorno Test: ATR={best_test_ret['atr_mult']} ({best_test_ret['test_ret']:+.4f})")
    print(f"  Melhor PF Train: ATR={best_pf['atr_mult']} ({best_pf['pf']:.2f}x)")
    print(f"  Mais Consistente: ATR={best_consistency['atr_mult']} (degradacao {best_consistency['degradation']:.1f}%)")
    
    # Salvar resumo
    df_results.to_csv('atr_multiplier_comparison.csv', index=False)
    print("\n  Resumo salvo em: atr_multiplier_comparison.csv")
