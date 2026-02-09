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
    Analisa o DNA de um ativo LENDO features pré-computadas do Parquet Feature Store.
    🚀 OTIMIZADO: Não recalcula indicadores - apenas lê do cache.
    """
    try:
        # 1. Validação dos dados de entrada
        if df.empty or len(df) < MIN_HISTORY:
            return None

        # Normaliza colunas
        df.columns = [str(col).lower() for col in df.columns]
        
        # 2. Lê indicadores PRÉ-COMPUTADOS do Parquet Feature Store
        entropy_col = IndicatorNames.entropy(20).lower()
        hurst_col = IndicatorNames.hurst(72, 'returns').lower()
        half_life_col = IndicatorNames.half_life(60).lower()
        
        # Verifica se indicadores existem no Parquet
        if entropy_col not in df.columns:
            logger.warning(f"{ticker}: Feature Store incompleto! Execute: python scripts/update_all_data.py")
            return None

        # 3. Calcula apenas volatilidade (métrica auxiliar não salva no Feature Store)
        df['vol_20'] = df['close'].pct_change().rolling(20).std()
        vol_of_vol = df['vol_20'].rolling(20).std()
        
        # 4. Calcula Z-Scores dos indicadores pré-computados
        try:
            entropy_z = calculate_z_score(df[entropy_col], window=LOOKBACK_WINDOW).iloc[-1]
        except Exception as e:
            logger.warning(f"{ticker}: Erro ao calcular Entropy Z-Score: {e}")
            entropy_z = np.nan
            
        try:
            hurst_z = calculate_z_score(df[hurst_col], window=LOOKBACK_WINDOW).iloc[-1] if hurst_col in df.columns else np.nan
        except:
            hurst_z = np.nan
            
        try:
            volvol_z = calculate_z_score(vol_of_vol, window=LOOKBACK_WINDOW).iloc[-1]
        except:
            volvol_z = np.nan
        
        current_hl = df[half_life_col].iloc[-1] if half_life_col in df.columns else 999

        # Validação
        if pd.isna(entropy_z):
            logger.warning(f"Entropy Z-Score inválido para {ticker}")
            return None
        
        if pd.isna(volvol_z):
            volvol_z = 0.0
        
        logger.info(f"✓ {ticker}: Entropy_Z={entropy_z:.2f}, Hurst_Z={hurst_z:.2f}, VolVol_Z={volvol_z:.2f}")

        # 5. Monta o resumo do DNA para o relatório
        dna = {
            'Ticker': ticker,
            'Preco': df['close'].iloc[-1],
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
    Orquestra a construção do DNA de mercado lendo do Feature Store (Parquet).
    MUITO MAIS RÁPIDO: não precisa calcular indicadores, só lê features pré-computadas.
    """
    print("\n[DNA] --- INICIANDO MAPEAMENTO DE DNA DA B3 (Feature Store) ---")
    
    # Path do Feature Store
    features_path = Path(__file__).parent.parent / "data" / "features"
    
    if not features_path.exists():
        print("[ERRO] Feature Store não encontrado!")
        print(f"Execute: python scripts/update_all_data.py")
        return
    
    # Lista arquivos Parquet disponíveis
    parquet_files = list(features_path.glob("*_enriched.parquet"))
    
    if not parquet_files:
        print("[ERRO] Nenhum arquivo de features encontrado!")
        print(f"Execute: python scripts/update_all_data.py")
        return
    
    print(f"[INFO] {len(parquet_files)} ativos com features pré-computadas")

    results = []
    
    # 2. Processa os arquivos Parquet (MUITO MAIS RÁPIDO que calcular)
    for parquet_file in tqdm(parquet_files, desc="Analisando DNA dos Ativos"):
        # Extrai ticker do nome do arquivo
        ticker = parquet_file.stem.replace('_enriched', '').replace('_SA', '.SA')
        
        try:
            # Lê DataFrame enriquecido do Parquet
            df = pd.read_parquet(parquet_file)
            dna = analyze_asset_dna(ticker, df)
            if dna:
                results.append(dna)
        except Exception as e:
            logger.warning(f"Erro ao processar {ticker}: {e}")
            continue
            
    # 3. Consolida e salva o relatório
    if not results:
        print("[ERRO] Nenhum DNA de ativo pôde ser gerado.")
        return

    # Remove apenas ativos sem Entropy_Z (requisito mínimo)
    # Hurst_Z e VolVol_Z podem ser NaN para ativos com histórico curto
    df_dna = pd.DataFrame(results).dropna(subset=['Entropy_Z'])
    
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
    print(f"[OK] RELATÓRIO DE DNA GERADO COM {len(df_dna)} ATIVOS")
    print("="*80)
    
    print("\n[TOP] TOP 10 MAIS ESTÁVEIS HOJE (Z-Score Entropia Baixo)")
    print(" (Oportunidades de Tendência Limpa)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].head(10).to_string(index=False))
    
    print("\n[ALERTA] TOP 10 MAIS TÓXICOS HOJE (Z-Score Entropia Alto)")
    print(" (Cuidado: Risco de Reversão/Violência)")
    print(df_dna[['Ticker', 'Preco', 'Entropy_Z', 'Estado']].tail(10).sort_values(by='Entropy_Z', ascending=False).to_string(index=False))
    
    print(f"\n[ARQUIVO] Relatório salvo em: {file_path}")
    print("[INFO] Os DataFrames enriquecidos com todos os indicadores foram salvos no banco de dados para uso futuro.")

if __name__ == "__main__":
    build_market_dna()