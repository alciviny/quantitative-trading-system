#!/usr/bin/env python3
"""
Valida integridade dos dados - procura por problemas:
1. NaN, inf, valores extremos
2. Inconsistências de regime
3. Registros duplicados
4. Dados fora do intervalo esperado
"""

import pandas as pd
import numpy as np
from pathlib import Path

def validate_csv(filepath):
    """Valida arquivo CSV para problemas de dados sujos."""
    
    df = pd.read_csv(filepath)
    
    print("\n" + "="*80)
    print(f"VALIDAÇÃO DE INTEGRIDADE - {filepath.name}")
    print("="*80)
    
    print(f"\n📊 DIMENSÕES:")
    print(f"  Total linhas: {len(df)}")
    print(f"  Total colunas: {len(df.columns)}")
    
    # 1. Verificar NaN
    print(f"\n🔍 NaN/Missing Values:")
    nan_cols = df.isnull().sum()
    if nan_cols.sum() > 0:
        print(f"  ⚠️  Detectados!")
        for col in nan_cols[nan_cols > 0].index:
            print(f"    {col}: {nan_cols[col]} ({nan_cols[col]/len(df)*100:.1f}%)")
    else:
        print(f"  ✅ Nenhum NaN detectado")
    
    # 2. Verificar infinitos
    print(f"\n🔍 Valores Infinitos:")
    inf_count = 0
    for col in df.select_dtypes(include=[np.number]).columns:
        inf_in_col = np.isinf(df[col]).sum()
        if inf_in_col > 0:
            print(f"  ⚠️  {col}: {inf_in_col} valores inf")
            inf_count += inf_in_col
    if inf_count == 0:
        print(f"  ✅ Nenhum infinito detectado")
    
    # 3. Verificar retornos
    print(f"\n🔍 Coluna 'return' (se existir):")
    if 'return' in df.columns:
        returns = df['return']
        print(f"  Min: {returns.min():.6f}")
        print(f"  Max: {returns.max():.6f}")
        print(f"  Mean: {returns.mean():.6f}")
        print(f"  Median: {returns.median():.6f}")
        print(f"  Std: {returns.std():.6f}")
        
        # Valores extremos
        extreme_neg = (returns < -0.95).sum()
        extreme_pos = (returns > 1.0).sum()
        print(f"  Valores < -95%: {extreme_neg}")
        print(f"  Valores > 100%: {extreme_pos}")
        
        if extreme_neg > 0 or extreme_pos > 0:
            print(f"  ⚠️  ALERTA: Valores extremos encontrados!")
    
    # 4. Verificar regimes
    print(f"\n🔍 Coluna 'regime' (se existir):")
    if 'regime' in df.columns:
        regime_counts = df['regime'].value_counts()
        print(f"  Total regimes únicos: {len(regime_counts)}")
        for regime, count in regime_counts.items():
            print(f"    {regime:20} {count:4} ({count/len(df)*100:5.1f}%)")
    
    # 5. Verificar duplicatas
    print(f"\n🔍 Duplicatas:")
    if len(df.columns) > 0:
        dups = df.duplicated().sum()
        if dups > 0:
            print(f"  ⚠️  {dups} linhas duplicadas ({dups/len(df)*100:.2f}%)")
        else:
            print(f"  ✅ Nenhuma duplicata detectada")
    
    # 6. Verificar tipos de dados
    print(f"\n🔍 Tipos de Dados:")
    print(df.dtypes)
    
    return df

def compare_expected_vs_actual():
    """Compara dados esperados (aggregate) vs. resultado da estratégia."""
    
    print("\n" + "="*80)
    print("COMPARAÇÃO: Dados Agregados vs. Execução da Estratégia")
    print("="*80)
    
    # Dados do CSV original
    original = pd.read_csv('momentum_all_regimes_results.csv')
    
    print(f"\nOriginal CSV:")
    print(f"  Total trades: {len(original)}")
    for regime in sorted(original['regime'].unique()):
        count = (original['regime'] == regime).sum()
        wr = (original[original['regime'] == regime]['return'] > 0).mean()
        print(f"    {regime:20} {count:4} trades, WR: {wr*100:5.1f}%")
    
    # Comparar com dados que o test_volatile_momentum gerou
    test_files = list(Path('.').glob('momentum_*_results.csv'))
    
    if test_files:
        print(f"\nArquivos de teste gerados:")
        for test_file in test_files:
            test_df = pd.read_csv(test_file)
            print(f"\n  {test_file.name}:")
            print(f"    Total trades: {len(test_df)}")
            for regime in sorted(test_df['regime'].unique()):
                count = (test_df['regime'] == regime).sum()
                wr = (test_df[test_df['regime'] == regime]['return'] > 0).mean()
                mean = test_df[test_df['regime'] == regime]['return'].mean()
                print(f"      {regime:18} {count:4} trades, WR: {wr*100:5.1f}%, Mean: {mean:+.4f}")
    
    print("\n" + "="*80)
    print("ANÁLISE DE DISCREPÂNCIAS")
    print("="*80)
    
    # Procura por ticker específico
    print("\nVerificando TIGER por ticker:")
    tickers_original = original['ticker'].unique()
    
    if test_files:
        test_df = pd.read_csv(test_files[0])
        tickers_test = test_df['ticker'].unique()
        
        missing_in_test = set(tickers_original) - set(tickers_test)
        extra_in_test = set(tickers_test) - set(tickers_original)
        
        if missing_in_test:
            print(f"  Tickers no original mas NÃO no teste: {len(missing_in_test)}")
        if extra_in_test:
            print(f"  Tickers no teste mas NÃO no original: {len(extra_in_test)}")

def main():
    # 1. Validar arquivo principal
    original_path = Path('momentum_all_regimes_results.csv')
    if original_path.exists():
        validate_csv(original_path)
    
    # 2. Comparar
    compare_expected_vs_actual()
    
    # 3. Recomendação final
    print("\n" + "="*80)
    print("RECOMENDAÇÕES")
    print("="*80)
    print("""
Se há discrepância entre dados agregados (114 BULL_VOLATILE) 
e resultado da estratégia (14 BULL_VOLATILE):

1. ✅ Usar os dados agregados DIRETAMENTE para análise
   - Arquivo: momentum_all_regimes_results.csv
   - Esses são os dados validados/confiáveis

2. ⚠️  Não confiar em teste_volatile_momentum.py para estes dados
   - Pode estar regenerando dados (walk-forward)
   - Período pode ser diferente

3. 🔧 Para análise final, usar:
   python extract_regime_subset.py --regime BULL_VOLATILE
   para extrair apenas BULL_VOLATILE do CSV original
""")

if __name__ == '__main__':
    main()
