# scripts/test_infrastructure.py

import sys
from pathlib import Path

# --- Início da Correção ---
# Adiciona o diretório 'src' ao sys.path para que o Python encontre o pacote co_piloto_quant.
# O caminho funciona da seguinte forma:
# Path(__file__) -> /caminho/completo/para/co-piloto-quant/scripts/teste_infra.py
# .parent -> /caminho/completo/para/co-piloto-quant/scripts
# .parent -> /caminho/completo/para/co-piloto-quant
# / "src" -> /caminho/completo/para/co-piloto-quant/src
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
# --- Início do Código de Depuração ---
src_path = Path(__file__).parent.parent / "src"
print("="*60)
print(f"🔍 DEBUG: Caminho do Script: {Path(__file__).resolve()}")
print(f"🔍 DEBUG: Caminho calculado para 'src': {src_path.resolve()}")
print(f"🔍 DEBUG: O caminho 'src' existe? -> {src_path.exists()}")

# Verifica se o diretório do pacote realmente existe
package_path = src_path / "co_piloto_quant"
print(f"🔍 DEBUG: Caminho do pacote 'co_piloto_quant' existe? -> {package_path.exists()}")

sys.path.insert(0, str(src_path))

print("\n🐍 DEBUG: Conteúdo final do sys.path (caminhos de busca do Python):")
import pprint
pprint.pprint(sys.path)
print("="*60)
# --- Fim do Código de Depuração ---

import pandas as pd

from co_piloto_quant.data.database import init_db, load_price_data, DB_PATH
from co_piloto_quant.data.data_fetching import fetch_data
from co_piloto_quant.data.data_processing import process_data

def run_smoke_test():
    print("="*60)
    print("🚦 INICIANDO TESTE DE INFRAESTRUTURA (SMOKE TEST)")
    print("="*60)

    # 1. Teste do Banco de Dados
    print("\n[1/4] Testando Inicialização do Banco de Dados...")
    try:
        init_db()
        if DB_PATH.exists():
            print(f"✅ Banco de dados encontrado/criado em: {DB_PATH}")
        else:
            print("❌ ERRO: Arquivo do banco de dados não foi criado.")
            return
    except Exception as e:
        print(f"❌ ERRO CRÍTICO no Banco: {e}")
        return

    # 2. Teste de Coleta e Salvamento (Yahoo -> SQLite)
    ticker = "PETR4.SA"
    print(f"\n[2/4] Testando Download e Salvamento para {ticker}...")
    try:
        # Busca dados recentes (últimos 6 meses para ser rápido)
        # Repare que agora fetch_data salva no banco automaticamente
        df_downloaded = fetch_data(ticker, period="6mo")
        
        if df_downloaded.empty:
            print("⚠️ AVISO: Download retornou vazio. Verifique sua internet.")
            return
        print(f"✅ Download concluído: {len(df_downloaded)} candles baixados.")
    except Exception as e:
        print(f"❌ ERRO no Download/Salvamento: {e}")
        return

    # 3. Teste de Leitura (SQLite -> Pandas)
    print(f"\n[3/4] Testando Leitura do Banco de Dados...")
    try:
        df_loaded = load_price_data(ticker)
        
        if df_loaded.empty:
            print("❌ ERRO: O banco retornou um DataFrame vazio. O salvamento falhou.")
            return
            
        print(f"✅ Leitura bem-sucedida: {len(df_loaded)} candles carregados do SQLite.")
        print(f"   Última data no banco: {df_loaded.index.max()}")
        
        # Verifica se as colunas estão em minúsculo (nosso padrão)
        cols = df_loaded.columns.tolist()
        if 'close' in cols and 'open' in cols:
            print("✅ Padronização de colunas (minúsculas) correta.")
        else:
            print(f"❌ ERRO: Colunas inesperadas: {cols}")
    except Exception as e:
        print(f"❌ ERRO na Leitura: {e}")
        return

    # 4. Teste de Processamento (Memória -> Indicadores)
    print(f"\n[4/4] Testando Cálculo de Indicadores (In-Memory)...")
    try:
        df_processed = process_data(df_loaded, ticker)
        
        # Verifica se criou colunas novas
        novas_colunas = len(df_processed.columns) - len(df_loaded.columns)
        if novas_colunas > 0:
            print(f"✅ Sucesso! {novas_colunas} novos indicadores calculados.")
            print("\nExemplo das colunas geradas:")
            # Mostra algumas colunas chave para confirmar
            cols_to_show = [c for c in df_processed.columns if 'bb_' in c or 'ifr' in c or 'stoch' in c][:5]
            print(f"   {cols_to_show} ...")
            
            print("\n🔍 Amostra dos Dados Finais (Tail):")
            print(df_processed[['close'] + cols_to_show].tail(3))
        else:
            print("❌ ERRO: Nenhuma coluna de indicador foi adicionada.")
            
    except Exception as e:
        print(f"❌ ERRO no Processamento: {e}")
        return

    print("\n" + "="*60)
    print("🎉 TESTE CONCLUÍDO: A INFRAESTRUTURA ESTÁ SÓLIDA!")
    print("="*60)

if __name__ == "__main__":
    run_smoke_test()