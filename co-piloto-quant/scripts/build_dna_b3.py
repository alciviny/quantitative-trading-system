import sys
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging

# Configuração de Path e Logs
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Importações do seu projeto
from src.co_piloto_quant.data.data_fetching import fetch_data
from src.co_piloto_quant.analysis import calculate_indicators
from src.co_piloto_quant.utils import get_b3_tickers

# Configurações
LOOKBACK_WINDOW = 252  # 1 Ano de aprendizado para a média
MIN_HISTORY = 300      # Precisa ter pelo menos isso de dados

def analyze_asset_dna(ticker):
    """
    Baixa dados e extrai o DNA estatístico do ativo.
    """
    try:
        # 1. Baixa 2 anos de dados
        # auto_adjust=True ajuda a pegar preços ajustados por dividendos/splits
        df = fetch_data(ticker, period="2y", interval="1d")
        
        if df.empty or len(df) < MIN_HISTORY:
            return None

        # --- CORREÇÃO DE COLUNAS (O PULO DO GATO) ---
        # O yfinance devolve 'Close', mas o analysis.py quer 'close'.
        # Também removemos MultiIndex se houver.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.columns = [col.lower() for col in df.columns]
        
        # Garante que temos 'close' (as vezes vem como 'adj close')
        if 'adj close' in df.columns and 'close' not in df.columns:
            df.rename(columns={'adj close': 'close'}, inplace=True)
            
        # ---------------------------------------------

        # 2. Calcula Indicadores e Z-Scores
        # O analysis.py agora vai encontrar a coluna 'close' e funcionar!
        df_calc = calculate_indicators(df)
        
        # Se o cálculo falhou (retornou vazio ou sem as colunas Z), ignora
        if df_calc.empty or 'Entropy_Z' not in df_calc.columns:
            return None

        last = df_calc.iloc[-1]
        
        # 3. Extrai o Perfil (DNA)
        dna = {
            'Ticker': ticker,
            'Preco': last['close'],
            
            # ENTROPIA (Ruído)
            'Entropy_Atual': last['Entropy_20'],
            'Entropy_Media': df_calc['Entropy_20'].rolling(LOOKBACK_WINDOW).mean().iloc[-1],
            'Entropy_Z': last.get('Entropy_Z', 0),
            
            # VOLATILIDADE (Risco)
            'Vol_Diaria_Atual': df_calc['close'].pct_change().rolling(20).std().iloc[-1] * 100,
            'VolVol_Z': last.get('VolVol_Z', 0),
            
            # TENDÊNCIA (Hurst)
            'Hurst_Z': last.get('Hurst_Z', 0),
            
            # DIAGNÓSTICO FINAL
            'Estado': 'NORMAL'
        }
        
        # Define o rótulo do estado atual baseada no Z-Score
        if dna['Entropy_Z'] > 2.0:
            dna['Estado'] = 'CAÓTICO (Perigo)'
        elif dna['Entropy_Z'] < -1.5:
            dna['Estado'] = 'ESTÁVEL (Oportunidade)'
            
        return dna

    except Exception as e:
        # logger.error(f"Erro em {ticker}: {e}")
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