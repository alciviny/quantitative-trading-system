import pandas as pd

df = pd.read_csv('momentum_all_regimes_results.csv')

print("="*80)
print("ANALISE DOS MELHORES REGIMES - MOMENTUM")
print("="*80)

for regime in sorted(df['regime'].unique()):
    if pd.isna(regime):
        continue
    
    train = df[(df['regime'] == regime) & (df['phase'] == 'TRAIN')]
    test = df[(df['regime'] == regime) & (df['phase'] == 'TEST')]
    
    if len(train) > 5 and len(test) > 5:
        train_ret = train['return'].mean()
        test_ret = test['return'].mean()
        train_wr = (train['return'] > 0).mean()
        test_wr = (test['return'] > 0).mean()
        
        gains = train[train['return'] > 0]['return'].sum()
        losses = abs(train[train['return'] < 0]['return'].sum())
        pf = gains / losses if losses > 0 else 0
        
        deg = ((test_ret - train_ret) / abs(train_ret) * 100) if train_ret != 0 else 0
        
        print(f"\n{regime}")
        print(f"  Train: {train_ret:+.4f} ({len(train):4} trades, {train_wr:.0%} WR, PF={pf:.2f}x)")
        print(f"  Test:  {test_ret:+.4f} ({len(test):4} trades, {test_wr:.0%} WR)")
        print(f"  Degradacao: {deg:+.0f}%")
        
        if train_ret > 0.02 and test_ret > 0.02:
            print("  -> EXCELENTE CANDIDATO!")
        elif train_ret > 0.01 and abs(deg) < 100:
            print("  -> BOM CANDIDATO")
        else:
            print("  -> DESCARTA")

print("\n" + "="*80)
print("RESUMO - RECOMENDACOES")
print("="*80)

recommendations = []
for regime in sorted(df['regime'].unique()):
    if pd.isna(regime):
        continue
    
    train = df[(df['regime'] == regime) & (df['phase'] == 'TRAIN')]
    test = df[(df['regime'] == regime) & (df['phase'] == 'TEST')]
    
    if len(train) > 5 and len(test) > 5:
        train_ret = train['return'].mean()
        test_ret = test['return'].mean()
        
        if train_ret > 0:
            recommendations.append({
                'regime': regime,
                'train_ret': train_ret,
                'test_ret': test_ret,
                'rank': train_ret + (test_ret * 0.5)
            })

recommendations_df = pd.DataFrame(recommendations).sort_values('rank', ascending=False)

print("\nTop regimes para OPERAR:")
for idx, row in recommendations_df.head(5).iterrows():
    print(f"  {row['regime']:20} -> Train: {row['train_ret']:+.4f}, Test: {row['test_ret']:+.4f}")
