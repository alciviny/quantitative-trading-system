import pandas as pd

df = pd.read_csv('walk_forward_extended_results.csv')

print('\n' + '='*80)
print('ANALISE DE OPORTUNIDADES DE MELHORIA')
print('='*80)

train = df[df['phase'] == 'TRAIN']
test = df[df['phase'] == 'TEST']

print(f'\nPERFORMANCE GERAL:')
print(f'  Train: {len(train):3} trades | Ret: {train["return"].mean():+.4f} | WR: {(train["win"].mean()):.1%}')
print(f'  Test:  {len(test):3} trades | Ret: {test["return"].mean():+.4f} | WR: {(test["win"].mean()):.1%}')

print('\nPOR REGIME (TRAIN):')
print('-'*80)
for regime in sorted(df['regime'].unique()):
    regime_train = df[(df['regime'] == regime) & (df['phase'] == 'TRAIN')]
    if len(regime_train) > 0:
        ret = regime_train['return'].mean()
        wr = (regime_train['win'].mean())
        wins = (regime_train['return'] > 0).sum()
        losses = (regime_train['return'] < 0).sum()
        gains = regime_train[regime_train['return'] > 0]['return'].sum()
        gross_loss = abs(regime_train[regime_train['return'] < 0]['return'].sum())
        pf = gains / gross_loss if gross_loss > 0 else 0
        
        status = 'OK' if ret > 0.005 else 'WEAK' if ret > 0 else 'BAD'
        print(f'{status} {regime:20s} {len(regime_train):3} trades | {ret:+.4f} ret | {wr:.1%} WR | PF: {pf:.2f}x')

print('\n\nEXIT REASONS (qual tipo de stop causa melhor retorno):')
print('-'*80)
exit_stats = df[df['phase'] == 'TRAIN'].groupby('reason').agg({
    'return': ['mean', 'count', lambda x: (x > 0).mean()]
}).round(4)
exit_stats.columns = ['AvgReturn', 'Count', 'WinRate']
exit_stats = exit_stats.sort_values('AvgReturn', ascending=False)
print(exit_stats)

print('\n\nHALF-LIFE ANALYSIS (qual range de HL funciona melhor):')
print('-'*80)
df_train = df[df['phase'] == 'TRAIN'].copy()
df_train['hl_bin'] = pd.cut(df_train['halflife_entrada'], bins=[0, 5, 10, 15, 20, 25, 30, 50])
hl_stats = df_train.groupby('hl_bin').agg({
    'return': ['mean', 'count', lambda x: (x > 0).mean()]
}).round(4)
hl_stats.columns = ['AvgReturn', 'Count', 'WinRate']
print(hl_stats)

print('\n\nRECOMENDACOES:')
print('='*80)
print('''
1. REMOVER only_bull_market=True
   - Esta rejeitando SIDEWAYS_VOLATILE que pode ter bom potencial
   - Permite entrar em Bear e Sideways para capturar mais sinais

2. AUMENTAR max_half_life (de 25 para 35-40)
   - Talvez esteja muito restritivo
   - Mean reversion mais lenta pode ser melhor

3. REDUZIR rsi_period (de 120 para 60)
   - RSI muito longo perde reversoes rapidas

4. REMOVER use_regime_filter
   - Esta bloqueando muitas oportunidades

5. INVESTIGAR HURST
   - Valores em 0.5 indicam calculo incorreto
   - Pode estar bloqueando boas entradas
''')
