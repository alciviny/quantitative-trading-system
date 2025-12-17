#!/usr/bin/env python3
"""
Roda Monte Carlo em um subset extraído de regime.
Garante que está usando dados verificados do CSV original.
"""

import pandas as pd
import numpy as np
import argparse
from pathlib import Path
import sys

sys.path.insert(0, 'src')
from co_piloto_quant.analysis.monte_carlo import full_monte_carlo_analysis, strategy_is_robust

def main():
    parser = argparse.ArgumentParser(description="Monte Carlo em subset de regime")
    parser.add_argument("--regime", type=str, default="BULL_VOLATILE")
    parser.add_argument("--simulations", type=int, default=5000)
    parser.add_argument("--input", type=str, default="momentum_all_regimes_results.csv")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        return
    
    df = pd.read_csv(input_path)
    
    # Filtrar regime
    subset = df[df['regime'] == args.regime]
    
    if len(subset) == 0:
        print(f"❌ Regime '{args.regime}' não encontrado!")
        print(f"Regimes disponíveis: {sorted(df['regime'].unique())}")
        return
    
    returns = subset['return'].dropna().values
    
    print("\n" + "="*80)
    print(f"MONTE CARLO EM {args.regime}")
    print("="*80)
    
    print(f"\n📊 DADOS:")
    print(f"  Total trades: {len(returns)}")
    print(f"  Mean: {returns.mean():+.6f}")
    print(f"  Median: {np.median(returns):+.6f}")
    print(f"  Win Rate: {(returns > 0).mean()*100:.1f}%")
    
    print(f"\n🎲 EXECUTANDO {args.simulations} SIMULAÇÕES...")
    
    results = full_monte_carlo_analysis(
        trade_returns=returns,
        num_simulations=args.simulations,
        block_size=5,
        ruin_level=0.5
    )
    
    report_block = results['report_block']
    
    print("\n" + "="*80)
    print(f"RESULTADOS MONTE CARLO - {args.regime}")
    print("="*80)
    
    print("\n📈 BLOCK BOOTSTRAP (mais conservador e realista):")
    print(f"  Return P5:        {report_block.loc['ROBUSTEZ', 'return_P5']:+.6f}")
    print(f"  Return P10:       {report_block.loc['ROBUSTEZ', 'return_P10']:+.6f}")
    print(f"  Return Median:    {report_block.loc['ROBUSTEZ', 'return_median']:+.6f}")
    print(f"  Max DD P90:       {report_block.loc['ROBUSTEZ', 'maxDD_P90']:.6f}")
    print(f"  Max DD P95:       {report_block.loc['ROBUSTEZ', 'maxDD_P95']:.6f}")
    print(f"  Prob de Ruína:    {report_block.loc['ROBUSTEZ', 'prob_ruin']*100:.1f}%")
    print(f"  Calmar (P10):     {report_block.loc['ROBUSTEZ', 'calmar_pessimista']:.4f}")
    
    is_robust = strategy_is_robust(report_block)
    
    print("\n" + "="*80)
    print("VEREDITO")
    print("="*80)
    
    if is_robust:
        print(f"✅ ESTRATÉGIA ROBUSTA EM {args.regime}")
        print(f"   Pronta para operação!")
    else:
        print(f"❌ ESTRATÉGIA NÃO ROBUSTA EM {args.regime}")
        
        # Diagnóstico
        p5 = report_block.loc['ROBUSTEZ', 'return_P5']
        prob_ruin = report_block.loc['ROBUSTEZ', 'prob_ruin']
        calmar = report_block.loc['ROBUSTEZ', 'calmar_pessimista']
        
        if p5 <= 0:
            print(f"   ⚠️  Problema: Pior 5% dos casos são negativos")
        if prob_ruin >= 0.05:
            print(f"   ⚠️  Problema: Probabilidade de ruína > 5%")
        if calmar <= 1.0:
            print(f"   ⚠️  Problema: Calmar Ratio (P10) < 1.0")
    
    # Salvando
    output_file = Path(f"monte_carlo_{args.regime.lower()}.csv")
    report_block.to_csv(output_file)
    print(f"\n📁 Relatório salvo em: {output_file}")

if __name__ == '__main__':
    main()
