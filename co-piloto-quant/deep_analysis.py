import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

df_2_0 = pd.read_csv('swing_bear_calm_atr_2.0.csv')

print("="*80)
print("ANALISE PROBABILISTICA PROFUNDA - BEAR_CALM (ATR 2.0x)")
print("="*80)

for phase in ['TRAIN', 'TEST']:
    phase_df = df_2_0[df_2_0['phase'] == phase]
    returns = phase_df['return'].values
    
    print(f"\n[{phase}] n={len(phase_df)} trades")
    print("-" * 80)
    
    # Estatisticas basicas
    print(f"  Mean Return: {returns.mean():.6f}")
    print(f"  Std Dev:     {returns.std():.6f}")
    print(f"  Median:      {np.median(returns):.6f}")
    print(f"  Min:         {returns.min():.6f}")
    print(f"  Max:         {returns.max():.6f}")
    
    # Skewness e Kurtosis
    skewness = stats.skew(returns)
    kurtosis = stats.kurtosis(returns)
    
    print(f"\n  Skewness: {skewness:.4f}")
    if abs(skewness) < 0.5:
        print(f"    -> Distribuicao simetrica (BOM)")
    elif skewness < 0:
        print(f"    -> Cauda esquerda longa (RUINS PIORES QUE GANHOS)")
    else:
        print(f"    -> Cauda direita longa (GANHOS MAIORES QUE RUINS)")
    
    print(f"\n  Excess Kurtosis: {kurtosis:.4f}")
    if kurtosis > 1:
        print(f"    -> Distribuicao leptocurtica (CAUDAS PESADAS, BLACK SWANS)")
    elif kurtosis < -1:
        print(f"    -> Distribuicao platicurtica (CAUDAS LEVES)")
    else:
        print(f"    -> Distribuicao normal")
    
    # Normality test
    _, p_value = stats.normaltest(returns)
    print(f"\n  Teste Normalidade (p-value): {p_value:.6f}")
    if p_value < 0.05:
        print(f"    -> REJEITA normalidade (distribuicao anomala)")
    else:
        print(f"    -> Nao rejeita normalidade")
    
    # Risk metrics
    win_trades = (returns > 0).sum()
    loss_trades = (returns < 0).sum()
    win_avg = returns[returns > 0].mean() if win_trades > 0 else 0
    loss_avg = returns[returns < 0].mean() if loss_trades > 0 else 0
    
    print(f"\n  Win Trades: {win_trades} ({100*win_trades/len(phase_df):.1f}%)")
    print(f"  Loss Trades: {loss_trades} ({100*loss_trades/len(phase_df):.1f}%)")
    print(f"  Avg Win: {win_avg:.6f}")
    print(f"  Avg Loss: {loss_avg:.6f}")
    
    if loss_trades > 0:
        ratio = abs(win_avg / loss_avg)
        print(f"  Profit Factor (Win/Loss): {ratio:.2f}x")
    
    # Sharpe Ratio (assuming 0% risk-free)
    sharpe = 0
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
        print(f"\n  Sharpe Ratio (annualized): {sharpe:.4f}")
        if sharpe > 1.0:
            print(f"    -> BOM")
        elif sharpe > 0.5:
            print(f"    -> ACEITAVEL")
        else:
            print(f"    -> RUIM")

print("\n" + "="*80)
print("AUTOCORRELACAO (EXISTE MEAN REVERSION?)")
print("="*80)

all_returns = df_2_0['return'].values
lag1_corr = np.corrcoef(all_returns[:-1], all_returns[1:])[0, 1]

print(f"\nAutocorrelacao Lag-1: {lag1_corr:.6f}")
if lag1_corr < -0.05:
    print(f"  -> EVIDENCIA DE MEAN REVERSION (reversao media)")
    print(f"  -> Autocorr negativa significa: retorno positivo seguido de negativo")
elif lag1_corr > 0.05:
    print(f"  -> EVIDENCIA DE MOMENTUM/TENDENCIA")
    print(f"  -> Autocorr positiva significa: movimento continua na mesma direcao")
else:
    print(f"  -> RANDOM WALK (sem padrao, apenas ruido)")
    print(f"  -> Nenhuma dependencia entre trades consecutivos")

print("\n" + "="*80)
print("CUSTOS OPERACIONAIS")
print("="*80)

custo_total = 0.0006
print(f"\nCusto por trade (spread + taxa): {custo_total:.4%}")

train_df = df_2_0[df_2_0['phase'] == 'TRAIN']
test_df = df_2_0[df_2_0['phase'] == 'TEST']

train_gross = train_df['return'].sum()
train_net = train_gross - (len(train_df) * custo_total)

test_gross = test_df['return'].sum()
test_net = test_gross - (len(test_df) * custo_total)

print(f"\nTREINO:")
print(f"  Retorno bruto: {train_gross:.4f} ({len(train_df)} trades)")
print(f"  Custo operacional: {len(train_df) * custo_total:.4f}")
print(f"  Retorno liquido: {train_net:.4f}")
print(f"  Impacto: {((train_net - train_gross) / abs(train_gross) * 100):.1f}%")

print(f"\nTESTE:")
print(f"  Retorno bruto: {test_gross:.4f} ({len(test_df)} trades)")
print(f"  Custo operacional: {len(test_df) * custo_total:.4f}")
print(f"  Retorno liquido: {test_net:.4f}")
print(f"  Impacto: {((test_net - test_gross) / abs(test_gross) * 100):.1f}%")

if train_net < 0:
    print("\n[ALERTA] Retorno de treino NEGATIVO apos custos!")
if test_net < 0:
    print("[ALERTA] Retorno de teste NEGATIVO apos custos!")

print("\n" + "="*80)
print("CONCLUSOES")
print("="*80)

print("\n1. DISTRIBUICAO:")
if skewness < -0.5:
    print("   PROBLEMA: Cauda esquerda pesada (ruins maiores que ganhos)")
else:
    print("   OK: Distribuicao razoavel")

print("\n2. MEAN REVERSION:")
if lag1_corr < -0.1:
    print("   FORTE: Existe reversao media detectavel")
elif lag1_corr < -0.05:
    print("   FRACA: Existe reversao media, mas muito fraca")
else:
    print("   NENHUMA: Trades sao independentes (random walk)")

print("\n3. CUSTOS:")
if abs((train_net - train_gross) / abs(train_gross)) > 0.10:
    print("   ALTO: Custos comem mais de 10% do retorno")
else:
    print("   RAZOAVEL: Custos sao gerenciaveis")

print("\n4. VERDICT:")
if train_net > 0 and lag1_corr < -0.05 and sharpe > 0.5:
    print("   VIAVEL: Merece desenvolvimento")
else:
    print("   NAO VIAVEL: Nao tem edge suficiente")
