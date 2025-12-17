import pandas as pd
import numpy as np

df = pd.read_csv('momentum_all_regimes_results.csv')
returns = df['return'].dropna().values

print(f"Total trades: {len(returns)}")
print(f"Min: {returns.min()}")
print(f"Max: {returns.max()}")
print(f"Mean: {returns.mean()}")
print(f"Median: {np.median(returns)}")
print(f"Trades < 0: {(returns < 0).sum()}")
print(f"Trades > 0: {(returns > 0).sum()}")
print(f"Returns == -1.0: {(returns == -1.0).sum()}")
print(f"Returns <= -0.9: {(returns <= -0.9).sum()}")

# Simula UMA vez para ver o que acontece
np.random.seed(42)
simulated = np.random.choice(returns, size=len(returns), replace=True)

print(f"\nSimulação 1:")
print(f"  Mean: {simulated.mean()}")
print(f"  Min: {simulated.min()}")
print(f"  Has values <= -0.9: {(simulated <= -0.9).sum()}")

# Método antigo
cumprod_result = np.cumprod(1 + simulated)
print(f"  Cumprod final: {cumprod_result[-1]}")
print(f"  Cumprod has nan/inf: {np.any(np.isnan(cumprod_result)) or np.any(np.isinf(cumprod_result))}")

# Método novo (log)
log_returns = np.log1p(simulated)
cum_log = np.cumsum(log_returns)
exp_result = np.exp(cum_log)
print(f"  Exp final: {exp_result[-1]}")
print(f"  Exp has nan/inf: {np.any(np.isnan(exp_result)) or np.any(np.isinf(exp_result))}")

final_return_old = (cumprod_result[-1] / 10000) - 1
final_return_new = (exp_result[-1] / 10000) - 1

print(f"\nFinal returns:")
print(f"  Old method: {final_return_old:.4f}")
print(f"  New method: {final_return_new:.4f}")

# Drawdown
peak = np.maximum.accumulate(exp_result)
drawdown = (peak - exp_result) / peak
print(f"  Max DD: {np.max(drawdown):.4f}")
print(f"  Peak[0]: {peak[0]}, Peak[-1]: {peak[-1]}")
print(f"  Exp[0]: {exp_result[0]}, Exp[-1]: {exp_result[-1]}")
