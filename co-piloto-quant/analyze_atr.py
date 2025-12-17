import pandas as pd
import sys

df_2_0 = pd.read_csv('swing_bear_calm_atr_2.0.csv')
df_3_0 = pd.read_csv('swing_bear_calm_atr_3.0.csv')

print("="*80)
print("ATR 2.0x EXIT REASON ANALYSIS (TRAIN)")
print("="*80)

train_2_0 = df_2_0[df_2_0['phase'] == 'TRAIN']
reason_2_0 = train_2_0.groupby('reason').agg({
    'return': ['mean', 'count', lambda x: (x > 0).sum()]
}).round(4)
reason_2_0.columns = ['AvgReturn', 'Count', 'Wins']
reason_2_0['TotalGain'] = train_2_0.groupby('reason')['return'].sum().round(4)
reason_2_0 = reason_2_0.sort_values('AvgReturn', ascending=False)
print(reason_2_0)

print("\n" + "="*80)
print("ATR 3.0x EXIT REASON ANALYSIS (TRAIN)")
print("="*80)

train_3_0 = df_3_0[df_3_0['phase'] == 'TRAIN']
reason_3_0 = train_3_0.groupby('reason').agg({
    'return': ['mean', 'count', lambda x: (x > 0).sum()]
}).round(4)
reason_3_0.columns = ['AvgReturn', 'Count', 'Wins']
reason_3_0['TotalGain'] = train_3_0.groupby('reason')['return'].sum().round(4)
reason_3_0 = reason_3_0.sort_values('AvgReturn', ascending=False)
print(reason_3_0)

print("\n" + "="*80)
print("COMPARACAO: 2.0x vs 3.0x")
print("="*80)

stop_loss_2_0 = train_2_0[train_2_0['reason'] == 'STOP_LOSS']
stop_loss_3_0 = train_3_0[train_3_0['reason'] == 'STOP_LOSS']

print(f"STOP_LOSS exits at 2.0x: {len(stop_loss_2_0)} trades, avg return {stop_loss_2_0['return'].mean():.4f}")
print(f"STOP_LOSS exits at 3.0x: {len(stop_loss_3_0)} trades, avg return {stop_loss_3_0['return'].mean():.4f}")
print(f"Reduction in stop_loss exits: {len(stop_loss_2_0) - len(stop_loss_3_0)} trades")

hard_stop_2_0 = train_2_0[train_2_0['reason'] == 'HARD_STOP']
hard_stop_3_0 = train_3_0[train_3_0['reason'] == 'HARD_STOP']

print(f"\nHARD_STOP exits at 2.0x: {len(hard_stop_2_0)} trades, avg return {hard_stop_2_0['return'].mean():.4f}")
print(f"HARD_STOP exits at 3.0x: {len(hard_stop_3_0)} trades, avg return {hard_stop_3_0['return'].mean():.4f}")
print(f"Reduction in hard_stop exits: {len(hard_stop_2_0) - len(hard_stop_3_0)} trades")

print(f"\nTotal training return improvement: {train_2_0['return'].mean():.4f} -> {train_3_0['return'].mean():.4f}")
