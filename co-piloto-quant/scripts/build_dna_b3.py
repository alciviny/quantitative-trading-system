import sys
from pathlib import Path
import pandas as pd
import numpy as np
from tqdm import tqdm
import logging

# Adiciona o diretório raiz ao path para garantir que os módulos sejam encontrados
sys.path.append(str(Path(__file__).resolve().parent.parent))
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# --- NOVAS IMPORTAÇÕES ---
from co_piloto_quant.data.data_manager import data_manager
from co_piloto_quant.universe import get_b3_tickers
from co_piloto_quant.data.indicator_engine import IndicatorEngine
from co_piloto_quant.utils.math_tools import calculate_z_score
from co_piloto_quant.indicators.names import IndicatorNames
from co_piloto_quant.config import RESULTS_DIR

LOOKBACK_WINDOW = 252
MIN_HISTORY = 300

def analyze_asset_dna(ticker, df):
    """
    Calcula o 'DNA' de um ativo a partir de seu DataFrame, agora recebido como parâmetro.
    Salva o DataFrame enriquecido de volta no banco de dados.
    """
    try:
        # 1. Validação dos dados de entrada
        if df.empty or len(df) < MIN_HISTORY:
            return None

        # Limpeza básica (mantida por segurança, mas DataManager deve padronizar)
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.columns = [col.lower() for col in df.columns]
        if 'adj close' in df.columns: df.rename(columns={'adj close': 'close'}, inplace=True)

        # 2. Cálculo de indicadores com IndicatorEngine
        engine = IndicatorEngine(df)
        engine.add_indicator('entropy', window=20)
        engine.add_indicator('hurst', window=72, kind='returns')
        engine.add_indicator('half_life', window=60)
        
        df_calc = engine.get_data()

        # 3. Cálculo de métricas específicas
        df_calc['vol_20'] = df_calc['close'].pct_change().rolling(20).std()
        vol_of_vol = df_calc['vol_20'].rolling(20).std()
        
        entropy_col = IndicatorNames.entropy(20)
        hurst_col = IndicatorNames.hurst(72, 'returns')
        
        if entropy_col not in df_calc.columns: return None

        # Calcula Z-Scores
        entropy_z = calculate_z_score(df_calc[entropy_col], window=LOOKBACK_WINDOW).iloc[-1]
        hurst_z = calculate_z_score(df_calc[hurst_col], window=LOOKBACK_WINDOW).iloc[-1] if hurst_col in df_calc.columns else np.nan
        volvol_z = calculate_z_score(vol_of_vol, window=LOOKBACK_WINDOW).iloc[-1]
        
        hl_col = 'half_life_60' # Nome da coluna gerada pelo indicador
        current_hl = df_calc[hl_col].iloc[-1] if hl_col in df_calc.columns else 999

        # --- PONTO CRÍTICO DA REFATORAÇÃO ---
        # 4. Persiste o DataFrame enriquecido com todos os novos indicadores
        data_manager.save_data(ticker, df_calc)
        # logging.debug(f"DNA e indicadores para {ticker} salvos no banco de dados.")

        # 5. Monta o resumo do DNA para o relatório
        dna = {
            'Ticker': ticker,
            'Preco': df_calc['close'].iloc[-1],
            'Entropy_Z': entropy_z,
            'Hurst_Z': hurst_z,
            'VolVol_Z': volvol_z,
            'HalfLife': current_hl,
            'Estado': 'NORMAL'
        }

        # Classificação do estado do ativo
        if dna['Entropy_Z'] > 2.0 or dna['VolVol_Z'] > 3.0:
            dna['Estado'] = 'TÓXICO (Ficar Fora)'
        elif dna['HalfLife'] < 25 and dna['Hurst_Z'] < -1.0:
            dna['Estado'] = 'REVERSÃO (Sniper)'
        elif dna['Hurst_Z'] > 1.0:
            dna['Estado'] = 'TENDÊNCIA'
            
        return dna

    except Exception as e:
        logger.error(f"Erro ao analisar DNA de {ticker}: {e}")
        return None

def build_market_dna():
    """
    Orquestra a construção do DNA de mercado. Agora busca os dados em lote primeiro
    e depois processa os ativos, de forma muito mais eficiente.
    """
    print("\n🧬 --- INICIANDO MAPEAMENTO DE DNA DA B3 (Infra Otimizada) ---")
    
    tickers = get_b3_tickers()
    print(f"Buscando dados para {len(tickers)} ativos...")

    # --- PONTO CRÍTICO DA REFATORAÇÃO ---
    # 1. Busca todos os dados em lote usando o DataManager.
    #    Isso acelera o processo e utiliza o cache de forma inteligente.
    all_data = data_manager.get_data_batch(tickers)
    
    valid_data = {t: df for t, df in all_data.items() if df is not None and not df.empty}
    print(f"Dados válidos obtidos para {len(valid_data)} ativos. Iniciando análise...")

    results = []
    
    # 2. Processa os dados já em memória (muito mais rápido)
    for ticker, df in tqdm(valid_data.items(), desc="Analisando DNA dos Ativos"):
        dna = analyze_asset_dna(ticker, df)
        if dna:
            results.append(dna)
            
    # 3. Consolida e salva o relatório
    if not results:
        print("❌ Nenhum DNA de ativo pôde ser gerado.")
        return

    df_dna = pd.DataFrame(results).dropna(subset=['Entropy_Z', 'Hurst_Z', 'VolVol_Z'])
    
    # Cria o diretório de relatórios dentro de RESULTS_DIR e define o caminho do arquivo
    report_dir = RESULTS_DIR / 'reports'
    report_dir.mkdir(parents=True, exist_ok=True)
    file_path = report_dir / 'b3_market_dna.csv'
    
    df_dna.sort_values(by='Entropy_Z', ascending=True, inplace=True)
    df_dna.to_csv(file_path, index=False)
    
    # --- RELATÓRIO NO TERMINAL ---
    pd.set_option('display.max_rows', 20)
    pd.set_option('display.float_format', '{:.2f}'.format)
    
    print("\n" + "="*80)
    print(f"✅ RELATÓRIO DE DNA GERADO COM {len(df_dna)} ATIVOS")
    print("="*80)
    
    print("\n🏆 TOP 10 MAIS ESTÁVEIS HOJE (Z-Score Entropia Baixo)")
    print(" (Oportunidades de Tendência Limpa)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].head(10).to_string(index=False))
    
    print("\n💀 TOP 10 MAIS TÓXICOS HOJE (Z-Score Entropia Alto)")
    print(" (Cuidado: Risco de Reversão/Violência)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].tail(10).sort_values(by='Entropy_Z', ascending=False).to_string(index=False))
    
    print(f"\n📁 Arquivo de relatório salvo em: {file_path}")
    print("💡 Os DataFrames enriquecidos com todos os indicadores foram salvos no banco de dados para uso futuro.")

if __name__ == "__main__":
    build_market_dna()