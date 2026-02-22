"""
Robust Walk-Forward Backtest para MeanReversionStrategy (Adaptado)
Save as: scripts/robust_strategy_backtest.py
"""
import sys
import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from tqdm import tqdm

# Adiciona o caminho do projeto para importar os módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- IMPORTA SUA ESTRATÉGIA VENCEDORA ---
from src.co_piloto_quant.strategies.mean_reversion import MeanReversionStrategy
from src.co_piloto_quant.config import PROCESSED_DATA_PATH, RESULTS_PATH # Importa os caminhos

# --------------------------
# Configurações
# --------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger('WFA')

DATA_DIR = Path('src/co_piloto_quant/data/ml_ready')
OUT_DIR = Path('src/co_piloto_quant/data/reports/wfa_strategy')
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Custos Reais
COMMISSION_PER_TRADE = 0.0006   # 0.06% taxas totais
SLIPPAGE_PCT = 0.001           # 0.1% slippage estimado

# Configuração da Estratégia (A MESMA DO LAB)
STRATEGY_PARAMS = {
    'bb_std_dev': 1.5,
    'bb_std_dev_volatile': 2.5,
    'rsi_period': 120,
    'adaptive_rsi': True,
    'adaptive_bb': True,
    'use_regime_filter': True,
    'max_half_life': 25,         # <--- Seu filtro de elasticidade
    'only_bull_market': True     # <--- Sua trava de segurança
}

# --------------------------
# Ferramentas Matemáticas (Herdadas do seu robust_backtest.py)
# --------------------------
def apply_execution_costs(raw_return):
    """Aplica custos operacionais e slippage no retorno bruto."""
    return raw_return - (2 * SLIPPAGE_PCT) - (2 * COMMISSION_PER_TRADE)

def max_drawdown(cum_returns):
    peak = np.maximum.accumulate(cum_returns)
    dd = (cum_returns - peak) / (peak + 1e-12)
    return abs(dd.min())

def kelly_fraction(win_rate, payoff_ratio):
    if payoff_ratio <= 0: return 0.0
    k = (win_rate - (1 - win_rate) / payoff_ratio)
    return max(k, 0.0)

def bootstrap_confidence(returns, n_iter=1000):
    """Calcula intervalo de confiança de 95% via Bootstrap."""
    if len(returns) < 5: return (0, 0)
    means = []
    for _ in range(n_iter):
        sample = np.random.choice(returns, size=len(returns), replace=True)
        means.append(np.mean(sample))
    return np.percentile(means, 2.5), np.percentile(means, 97.5)

# --------------------------
# Motor de Simulação
# --------------------------
def run_strategy_on_file(file_path, start_date, end_date):
    """Roda a estratégia em um único arquivo e recorta o período."""
    try:
        df = pd.read_parquet(file_path)
        if df.empty: return []
        
        # Garante índice datetime
        if 'data_pregao' in df.columns:
            df.set_index('data_pregao', inplace=True)
        df.index = pd.to_datetime(df.index)
        
        # Instancia a Estratégia
        strategy = MeanReversionStrategy(**STRATEGY_PARAMS)
        
        # Executa (Gera sinais)
        df_eval = strategy._calculate_signals(df) # Usa método interno para ser rápido
        
        # Filtra pelo período do Walk-Forward
        mask = (df_eval.index >= start_date) & (df_eval.index <= end_date)
        df_period = df_eval[mask].copy()
        
        if df_period.empty: return []

        # Simula Trades Simples
        trades = []
        in_trade = False
        entry_price = 0.0
        
        # Lógica simplificada de backtest vetorizado para velocidade
        # Compra no Close do sinal, Vende no Close do sinal
        signals = df_period['SIGNAL']
        prices = df_period['close']
        
        for date, signal in signals.items():
            price = prices.loc[date]
            
            if signal == 'BUY' and not in_trade:
                entry_price = price
                in_trade = True
                
            elif (signal == 'SELL' or signal == 'EXIT') and in_trade:
                raw_ret = (price / entry_price) - 1
                net_ret = apply_execution_costs(raw_ret)
                trades.append({
                    'ticker': file_path.stem.replace('_', '.'),
                    'entry_date': date,
                    'return': net_ret
                })
                in_trade = False
                
        return trades
        
    except Exception as e:
        # logger.error(f"Erro em {file_path.name}: {e}")
        return []

# --------------------------
# Walk-Forward Routine
# --------------------------
def main():
    files = sorted(list(DATA_DIR.glob("*_SA.parquet")))
    logger.info(f"Encontrados {len(files)} arquivos de dados.")
    
    # Define as Janelas de Tempo (Walk-Forward Anual)
    # Você pode ajustar essas datas conforme seu histórico disponível
    years = [2022, 2023, 2024, 2025] 
    
    global_results = []
    
    print("\n" + "="*60)
    print("🚀 INICIANDO WALK-FORWARD ANALYSIS (WFA)")
    print("="*60)
    
    for year in years:
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        print(f"\n📅 Testando Ano: {year}...")
        
        yearly_trades = []
        for fp in tqdm(files, desc=f"Simulando {year}", leave=False):
            t = run_strategy_on_file(fp, start_date, end_date)
            yearly_trades.extend(t)
            
        if not yearly_trades:
            print(f"   ⚠️ Sem trades em {year}.")
            continue
            
        df_trades = pd.DataFrame(yearly_trades)
        
        # Cálculo de Métricas
        wins = df_trades[df_trades['return'] > 0]
        losses = df_trades[df_trades['return'] <= 0]
        
        n_trades = len(df_trades)
        win_rate = len(wins) / n_trades
        avg_win = wins['return'].mean() if not wins.empty else 0
        avg_loss = abs(losses['return'].mean()) if not losses.empty else 0
        payoff = avg_win / avg_loss if avg_loss > 0 else 0
        profit_factor = wins['return'].sum() / abs(losses['return'].sum()) if not losses.empty else 99.9
        
        # Curva de Capital e Drawdown
        equity_curve = (1 + df_trades['return']).cumprod()
        mdd = max_drawdown(equity_curve)
        total_return = equity_curve.iloc[-1] - 1
        
        # Kelly e Bootstrap
        kelly = kelly_fraction(win_rate, payoff)
        conf_min, conf_max = bootstrap_confidence(df_trades['return'].values)
        
        print(f"   ✅ Resultado {year}:")
        print(f"      Trades: {n_trades} | Win Rate: {win_rate:.1%}")
        print(f"      Profit Factor: {profit_factor:.2f}x | Retorno: {total_return:.1%}")
        print(f"      Max Drawdown: {mdd:.1%} | Kelly Sugerido: {kelly:.1%}")
        print(f"      Confiança 95%: [{conf_min:.2%}, {conf_max:.2%}] por trade")
        
        global_results.append({
            'Year': year,
            'Trades': n_trades,
            'WinRate': win_rate,
            'ProfitFactor': profit_factor,
            'TotalReturn': total_return,
            'MaxDD': mdd,
            'Kelly': kelly
        })

    # --- RELATÓRIO FINAL ---
    if global_results:
        final_df = pd.DataFrame(global_results)
        print("\n" + "="*60)
        print("📊 RESUMO FINAL DE ROBUSTEZ (WALK-FORWARD)")
        print("="*60)
        print(final_df.to_string(index=False, formatters={
            'WinRate': '{:.1%}'.format,
            'ProfitFactor': '{:.2f}'.format,
            'TotalReturn': '{:.1%}'.format,
            'MaxDD': '{:.1%}'.format,
            'Kelly': '{:.1%}'.format
        }))
        
        # Salva
        final_df.to_csv(OUT_DIR / 'wfa_summary.csv', index=False)
        print(f"\n📁 Relatório salvo em: {OUT_DIR / 'wfa_summary.csv'}")
        
        # Validação de Consistência
        pfs = final_df['ProfitFactor']
        if (pfs > 1.5).all():
            print("\n🏆 VEREDITO: SISTEMA APROVADO! Consistente em todos os anos.")
        elif (pfs > 1.0).all():
             print("\n⚠️ VEREDITO: SISTEMA SÓLIDO. Lucrativo, mas requer atenção em anos fracos.")
        else:
             print("\n❌ VEREDITO: INSTÁVEL. Falhou em algum ano.")

if __name__ == '__main__':
    main()