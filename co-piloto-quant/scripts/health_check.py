import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Adiciona o diretório raiz ao sys.path para permitir importações de módulos do projeto
# Isso torna o script executável de qualquer lugar
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    # Tenta importar o DB_PATH da configuração central
    from src.co_piloto_quant.data.database import DB_PATH
except (ModuleNotFoundError, ImportError) as e:
    print(f"❌ Erro Crítico: Não foi possível importar a configuração do banco de dados. Verifique o sys.path e a estrutura do projeto.")
    print(f"Detalhe: {e}")
    # Fallback para um caminho padrão se a importação falhar
    DB_PATH = "data/market_data.db"


def run_health_check():
    """
    Executa uma série de verificações para garantir a saúde e integridade do banco de dados.
    Retorna True se tudo estiver OK, False caso contrário.
    """
    print("🩺 Iniciando Health Check do Banco de Dados...")
    print(f"Database alvo: {DB_PATH}")
    print("-" * 50)

    all_checks_ok = True
    
    # --- Verificação 1: Conectividade e Existência do Arquivo ---
    if not os.path.exists(DB_PATH):
        print("❌ FALHA: Arquivo do banco de dados não encontrado.")
        return False
        
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True) # Conecta em modo read-only
        cursor = conn.cursor()
        print("✅ OK: Conexão com o banco de dados estabelecida (read-only).")
    except Exception as e:
        print(f"❌ FALHA: Não foi possível conectar ao banco de dados: {e}")
        return False

    # --- Verificação 2: Existência das Tabelas Essenciais ---
    required_tables = ['assets', 'ohlcv', 'signals_history', 'trades_execution']
    print("\nVerificando tabelas essenciais...")
    for table in required_tables:
        try:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}';")
            if cursor.fetchone():
                print(f"  ✅ OK: Tabela '{table}' encontrada.")
            else:
                print(f"  ❌ FALHA: Tabela '{table}' não encontrada.")
                all_checks_ok = False
        except Exception as e:
            print(f"  ❌ ERRO: Ocorreu um erro ao verificar a tabela '{table}': {e}")
            all_checks_ok = False

    # --- Verificação 3: Dados Recentes na Tabela OHLCV ---
    print("\nVerificando dados recentes (OHLCV)...")
    if 'ohlcv' in required_tables:
        try:
            query = "SELECT MAX(date) FROM ohlcv;"
            latest_date_str = cursor.execute(query).fetchone()[0]
            
            if latest_date_str:
                latest_date = pd.to_datetime(latest_date_str)
                time_diff = datetime.now() - latest_date
                
                print(f"  - Data mais recente encontrada: {latest_date.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if time_diff.days <= 2:
                    print(f"  ✅ OK: Os dados de preço são recentes (idade: {time_diff.days} dias).")
                else:
                    print(f"  ⚠️ ALERTA: Os dados de preço parecem desatualizados (idade: {time_diff.days} dias).")
                    # Pode ser um alerta em vez de uma falha, dependendo do caso de uso (ex: fim de semana)
                    if time_diff.days > 4: # Considera fim de semana
                        print("  ❌ FALHA: Dados com mais de 4 dias de idade.")
                        all_checks_ok = False

            else:
                print("  ❌ FALHA: Nenhum dado encontrado na tabela 'ohlcv'.")
                all_checks_ok = False
        except Exception as e:
            print(f"  ❌ ERRO: Não foi possível verificar a data dos dados em 'ohlcv': {e}")
            all_checks_ok = False

    # --- Verificação 4: Dados na Tabela signals_history ---
    print("\nVerificando conteúdo da tabela de sinais (signals_history)...")
    if 'signals_history' in required_tables:
        try:
            query = "SELECT COUNT(*) FROM signals_history;"
            count = cursor.execute(query).fetchone()[0]
            if count > 0:
                print(f"  ✅ OK: Tabela 'signals_history' contém {count} registros.")
            else:
                print(f"  ⚠️ ALERTA: Tabela 'signals_history' está vazia.")
                # Não é necessariamente uma falha, mas um aviso importante.
        except Exception as e:
            print(f"  ❌ ERRO: Não foi possível contar os registros em 'signals_history': {e}")
            all_checks_ok = False
            
    conn.close()
    
    print("-" * 50)
    if all_checks_ok:
        print("🎉 SUCESSO: Todos os checks de saúde do banco de dados passaram.")
    else:
        print("🔥 FALHA: Um ou mais checks de saúde falharam. Revise os logs acima.")
        
    return all_checks_ok


if __name__ == "__main__":
    if run_health_check():
        sys.exit(0)  # Sucesso
    else:
        sys.exit(1)  # Falha
