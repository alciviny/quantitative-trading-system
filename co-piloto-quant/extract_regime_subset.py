#!/usr/bin/env python3
"""
Extrai subset de dados para um regime específico.
Usa dados VERIFICADOS do CSV original, não regera.
"""

import pandas as pd
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Extrai subset de regime do CSV")
    parser.add_argument("--regime", type=str, default="BULL_VOLATILE", 
                        help="Regime a extrair")
    parser.add_argument("--input", type=str, default="momentum_all_regimes_results.csv",
                        help="CSV de input")
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Arquivo não encontrado: {input_path}")
        return
    
    df = pd.read_csv(input_path)
    
    print(f"\n📊 EXTRAINDO {args.regime}")
    print("="*80)
    
    print(f"Total trades no arquivo: {len(df)}")
    
    # Filtrar regime
    subset = df[df['regime'] == args.regime].copy()
    
    if len(subset) == 0:
        print(f"❌ Regime '{args.regime}' não encontrado no arquivo!")
        print(f"\nRegimes disponíveis:")
        for regime in sorted(df['regime'].unique()):
            count = (df['regime'] == regime).sum()
            print(f"  - {regime:20} ({count} trades)")
        return
    
    # Output
    output_file = Path(f"{args.regime.lower()}_subset.csv")
    subset.to_csv(output_file, index=False)
    
    print(f"\n✅ Extraído {len(subset)} trades para {args.regime}")
    print(f"   Salvo em: {output_file}")
    
    # Estatísticas
    returns = subset['return']
    wr = (returns > 0).mean()
    
    print(f"\n📈 ESTATÍSTICAS DO {args.regime}:")
    print(f"  Total trades:     {len(subset)}")
    print(f"  Win Rate:         {wr*100:.1f}%")
    print(f"  Mean return:      {returns.mean():+.6f}")
    print(f"  Median return:    {returns.median():+.6f}")
    print(f"  Std dev:          {returns.std():.6f}")
    print(f"  Min:              {returns.min():+.6f}")
    print(f"  Max:              {returns.max():+.6f}")
    
    # Profit Factor
    gains = returns[returns > 0].sum()
    losses = abs(returns[returns < 0].sum())
    pf = gains / losses if losses > 0 else float('inf')
    print(f"  Profit Factor:    {pf:.2f}x")

if __name__ == '__main__':
    main()
