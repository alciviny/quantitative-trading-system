import sys
import os
import pandas as pd
import MetaTrader5 as mt5

# Ajuste de path para importar seus módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.co_piloto_quant.analysis import calculate_indicators

def check_asset_dna(ticker):
    """Analisa o DNA do ativo e mostra seus níveis relativos."""
    print(f"\n🔬 ANALISANDO DNA DE: {ticker}...")
    
    # Busca 400 candles diários para ter histórico suficiente para o Z-Score
    rates = mt5.copy_rates_from_pos(ticker, mt5.TIMEFRAME_D1, 0, 400)
    
    if rates is None or len(rates) == 0:
        print(f"❌ Sem dados para {ticker}. \n   👉 Dica: Adicione-o na Observação de Mercado (Ctrl+M) ou verifique o nome (ex: GOLD vs XAUUSD).")
        return

    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    df.set_index('time', inplace=True)
    df.rename(columns={'tick_volume': 'volume'}, inplace=True)
    
    # Aplica a matemática (analysis.py atualizado)
    try:
        df = calculate_indicators(df)
    except Exception as e:
        print(f"Erro no cálculo: {e}")
        return

    # Diagnóstico
    last = df.iloc[-1]
    # Média de 1 ano (252 dias úteis)
    mean_entropy = df['Entropy_20'].rolling(252).mean().iloc[-1]
    
    print(f"   - Preço Atual:      {last['close']}")
    print(f"   - Entropia (Ruído): {last['Entropy_20']:.2f}")
    print(f"   - Média Histórica:  {mean_entropy:.2f} (O 'Normal' para {ticker})")
    print(f"   - Z-Score:          {last['Entropy_Z']:.2f}σ")
    
    # Interpretação
    if last['Entropy_Z'] > 2.0:
        print("   ⚠️ STATUS: ANOMALIA! (Comportamento muito mais caótico que o normal)")
    elif last['Entropy_Z'] < -1.0:
        print("   ✅ STATUS: ESTÁVEL (Mercado excepcionalmente calmo)")
    else:
        print("   ℹ️ STATUS: NORMAL (Dentro do padrão do ativo)")

def main():
    if not mt5.initialize():
        print("Erro ao conectar no MT5")
        return

    # COMPARAÇÃO: O "Calmo" vs o "Agitado"
    check_asset_dna("EURUSD")  # O par mais líquido do mundo
    check_asset_dna("XAUUSD")  # Ouro (Costuma ser mais volátil)
    
    # Se XAUUSD não funcionar, tente "GOLD" ou "GBPUSD"
    
    mt5.shutdown()

if __name__ == "__main__":
    main()