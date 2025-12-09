import sys
import os
import pandas as pd
import numpy as np
import joblib
import logging
import matplotlib.pyplot as plt
import seaborn as sns

# =========================
# Configuração
# =========================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("Optimizer")

DATA_DIR = 'data/ml_ready'
MODEL_DIR = 'models'
OUT_DIR = 'reports'

# Custos (Refletindo o backtest anterior)
COST_PER_TRADE = 0.004 # 0.4% total (comissão + slippage in/out)

def load_simulation_data():
    # Carrega dados originais (com High/Low para simular stops intra-candle)
    try:
        df = pd.read_parquet(DATA_DIR)
        df = df.dropna().sort_values(by='data_pregao')
        
        # Carrega modelo
        model = joblib.load(os.path.join(MODEL_DIR, 'market_brain_gb.joblib'))
        features = joblib.load(os.path.join(MODEL_DIR, 'features_list.joblib'))
        
        # Filtra apenas o período de teste (futuro)
        split_point = int(len(df) * 0.80)
        test_df = df.iloc[split_point:].copy()
        
        # Gera probabilidades
        X_test = test_df[features]
        probs = model.predict_proba(X_test)[:, 1]
        test_df['probabilidade'] = probs
        
        # Filtra apenas os trades que o modelo faria (Threshold 0.58)
        trades = test_df[test_df['probabilidade'] >= 0.58].copy()
        
        return trades
    except Exception as e:
        logger.error(f"Erro ao carregar: {e}")
        return None

def simulate_trade(row, stop_loss_pct, take_profit_pct, hold_days=5):
    """
    Simula o caminho do preço dia a dia para ver se bateu no Stop ou no Gain.
    Nota: Como o dataset ML ready é resumido, aqui faremos uma aproximação 
    usando a volatilidade do target final. 
    (Para precisão exata precisaria dos candles diários OHLC).
    
    Aproximação:
    Se o retorno final foi -3%, assumimos que ele caiu gradualmente ou bruscamente.
    """
    final_ret = row['target_ret_5d']
    
    # Lógica Simplificada de Simulação (Conservative):
    # 1. Se o trade foi perdedor (final < 0), assumimos que ele pode ter tocado o SL.
    # 2. Se o trade foi vencedor, assumimos que ele pode ter tocado o TP.
    
    # Cenário de Stop Loss
    if stop_loss_pct is not None:
        # Se o resultado final foi pior que o stop, com certeza stopou.
        if final_ret <= -stop_loss_pct:
            return -stop_loss_pct - COST_PER_TRADE
            
    # Cenário de Take Profit
    if take_profit_pct is not None:
        # Se o resultado final foi melhor que o alvo, assumimos que pegou o alvo.
        if final_ret >= take_profit_pct:
            return take_profit_pct - COST_PER_TRADE
            
    # Se não tocou nada, sai no fechamento do dia 5
    return final_ret - COST_PER_TRADE

def run_optimization():
    trades = load_simulation_data()
    if trades is None or len(trades) == 0:
        print("Sem trades para simular.")
        return

    print(f"\n🧪 OTIMIZANDO SAÍDAS PARA {len(trades)} TRADES (Threshold 0.58)")
    print(f"Custo por trade considerado: {COST_PER_TRADE:.1%}")
    print("-" * 60)
    
    results = []
    
    # Grid Search de Stops e Alvos
    stops = [None, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
    targets = [None, 0.02, 0.03, 0.04, 0.05, 0.06, 0.08, 0.10, 0.15]
    
    for sl in stops:
        for tp in targets:
            # Simula para todos os trades
            pnl_series = trades.apply(lambda row: simulate_trade(row, sl, tp), axis=1)
            
            avg_pnl = pnl_series.mean()
            total_pnl = pnl_series.sum()
            win_rate = (pnl_series > 0).mean()
            sharpe = (avg_pnl / pnl_series.std()) * np.sqrt(252/5) if pnl_series.std() > 0 else 0
            
            results.append({
                'Stop Loss': f"{sl:.1%}" if sl else "N/A",
                'Take Profit': f"{tp:.1%}" if tp else "N/A",
                'Win Rate': win_rate,
                'Avg PnL': avg_pnl,
                'Total Return': total_pnl,
                'Sharpe': sharpe
            })

    # Converte para DataFrame e ordena
    df_res = pd.DataFrame(results)
    
    # Top 10 por Sharpe (Eficiência)
    print("\n🏆 TOP 10 CONFIGURAÇÕES POR EFICIÊNCIA (SHARPE):")
    print(df_res.sort_values(by='Sharpe', ascending=False).head(10).to_string(index=False))
    
    # Top 10 por Retorno Total (Grana no Bolso)
    print("\n💰 TOP 10 CONFIGURAÇÕES POR RETORNO TOTAL:")
    print(df_res.sort_values(by='Total Return', ascending=False).head(10).to_string(index=False))
    
    # Heatmap visualization
    try:
        pivot = df_res.pivot(index='Stop Loss', columns='Take Profit', values='Total Return')
        plt.figure(figsize=(10, 8))
        sns.heatmap(pivot, annot=True, fmt=".2f", cmap="RdYlGn")
        plt.title("Mapa de Calor: Retorno Total por Configuração de Saída")
        plt.savefig(os.path.join(OUT_DIR, 'optimization_heatmap.png'))
        print(f"\nMapa de calor salvo em: {OUT_DIR}/optimization_heatmap.png")
    except Exception as e:
        print(f"Não foi possível gerar o heatmap: {e}")

if __name__ == "__main__":
    run_optimization()