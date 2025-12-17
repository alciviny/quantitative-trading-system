import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

from src.co_piloto_quant.data.data_fetching import fetch_data
from src.co_piloto_quant.utils import get_b3_tickers
# SUBSTITUIÇÃO: Sai analysis.py, entra IndicatorEngine e Math Tools
from src.co_piloto_quant.data.indicator_engine import IndicatorEngine
from src.co_piloto_quant.utils.math_tools import calculate_z_score
from src.co_piloto_quant.indicators.names import IndicatorNames

LOOKBACK_WINDOW = 252
MIN_HISTORY = 300

def analyze_asset_dna(ticker):
    try:
        # 1. Baixa dados
        df = fetch_data(ticker, period="2y", interval="1d")
        if df.empty or len(df) < MIN_HISTORY: return None

        # Limpeza básica
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [col.lower() for col in df.columns]
        if 'adj close' in df.columns: df.rename(columns={'adj close': 'close'}, inplace=True)

        # 2. O "Novo Jeito" com IndicatorEngine
        engine = IndicatorEngine(df)
        engine.add_indicator('entropy', window=20)
        engine.add_indicator('hurst', window=72, kind='returns') # Usando returns para ficar igual ao analysis
        engine.add_indicator('half_life', window=60) # <--- Seu novo Half-Life aqui
        
        df_calc = engine.get_data()

        # 3. Cálculo Manual de Métricas Específicas (Volatilidade e Z-Scores)
        # O analysis.py fazia isso "escondido", agora fazemos explicitamente:
        
        # Volatilidade (Rolling Std de 20 dias)
        df_calc['vol_20'] = df_calc['close'].pct_change().rolling(20).std()
        
        # Volatilidade da Volatilidade (Simplificada para o DNA)
        vol_of_vol = df_calc['vol_20'].rolling(20).std()
        
        # Z-Scores (Essenciais para o DNA)
        # Precisamos dos nomes corretos que o IndicatorEngine gerou
        entropy_col = IndicatorNames.entropy(20)
        hurst_col = IndicatorNames.hurst(72, 'returns')
        
        if entropy_col not in df_calc.columns: return None

        # Calcula Z-Scores usando janela de aprendizado (252 dias)
        entropy_z = calculate_z_score(df_calc[entropy_col], window=LOOKBACK_WINDOW).iloc[-1]
        hurst_z = calculate_z_score(df_calc[hurst_col], window=LOOKBACK_WINDOW).iloc[-1] if hurst_col in df_calc.columns else 0
        volvol_z = calculate_z_score(vol_of_vol, window=LOOKBACK_WINDOW).iloc[-1]
        
        # Pega o Half-Life atual (coluna gerada pelo engine)
        hl_col = 'half_life_60' # Nome padrão do seu script half_life.py
        current_hl = df_calc[hl_col].iloc[-1] if hl_col in df_calc.columns else 999

        # 4. Monta o DNA
        dna = {
            'Ticker': ticker,
            'Preco': df_calc['close'].iloc[-1],
            'Entropy_Z': entropy_z,
            'Hurst_Z': hurst_z,
            'VolVol_Z': volvol_z,
            'HalfLife': current_hl, # <--- Nova métrica no relatório!
            'Estado': 'NORMAL'
        }

        # Classificação baseada no novo Risk Regime
        if dna['Entropy_Z'] > 2.0 or dna['VolVol_Z'] > 3.0:
            dna['Estado'] = 'TÓXICO (Ficar Fora)'
        elif dna['HalfLife'] < 25 and dna['Hurst_Z'] < -1.0:
            dna['Estado'] = 'REVERSÃO (Sniper)'
        elif dna['Hurst_Z'] > 1.0:
            dna['Estado'] = 'TENDÊNCIA'
            
        return dna

    except Exception as e:
        # logger.error(f"Erro {ticker}: {e}")
        return None


def build_market_dna():
    print("\n🧬 --- INICIANDO MAPEAMENTO DE DNA DA B3 (CORRIGIDO) ---")
    
    tickers = get_b3_tickers()
    print(f"Processando {len(tickers)} ativos...")
    
    results = []
    
    # Barra de progresso
    for ticker in tqdm(tickers):
        dna = analyze_asset_dna(ticker)
        if dna:
            results.append(dna)
            
    # 2. Consolida
    df_dna = pd.DataFrame(results)
    
    if df_dna.empty:
        print("❌ Nenhum dado processado mesmo após a correção.")
        print("Verifique se o seu analysis.py está retornando o DataFrame corretamente.")
        return

    # 3. Salva o Banco de Dados de DNA
    os.makedirs('data/reports', exist_ok=True)
    file_path = 'data/reports/b3_market_dna.csv'
    
    # Ordena pelos melhores (mais estáveis primeiro)
    df_dna.sort_values(by='Entropy_Z', ascending=True, inplace=True)
    
    df_dna.to_csv(file_path, index=False)
    
    # --- RELATÓRIO NO TERMINAL ---
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("\n" + "="*80)
    print(f"✅ RELATÓRIO GERADO COM {len(df_dna)} ATIVOS")
    print("="*80)
    
    print("\n🏆 TOP 10 MAIS ESTÁVEIS HOJE (Z-Score Entropia Baixo)")
    print(" (Oportunidades de Tendência Limpa)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].head(10))
    
    print("\n💀 TOP 10 MAIS TÓXICOS HOJE (Z-Score Entropia Alto)")
    print(" (Cuidado: Risco de Reversão/Violência)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].tail(10).sort_values(by='Entropy_Z', ascending=False))
    
    print(f"\n📁 Arquivo salvo em: {file_path}")

if __name__ == "__main__":
    build_market_dna()