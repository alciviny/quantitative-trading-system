import sys
import os
import sqlite3

# Adiciona o diretório raiz ao sys.path para permitir importações relativas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.co_piloto_quant.data.database import init_db, DB_PATH
except (ModuleNotFoundError, ImportError):
    print("❌ Erro: Não foi possível importar 'init_db'. Verifique a estrutura do projeto.")
    sys.exit(1)

def setup():
    """
    Executa a função de inicialização do banco de dados para criar
    tabelas que possam estar faltando.
    """
    print(f"🛠️  Executando setup para o banco de dados em: {DB_PATH}")
    
    if not os.path.exists(os.path.dirname(DB_PATH)):
        print(f"Criando diretório de dados em: {os.path.dirname(DB_PATH)}")
        os.makedirs(os.path.dirname(DB_PATH))

    try:
        # A função init_db usa 'CREATE TABLE IF NOT EXISTS',
        # então é seguro executá-la em um banco de dados existente.
        init_db()
        print("✅ Sucesso! O banco de dados foi inicializado/verificado.")
        print("As tabelas 'assets', 'ohlcv', 'trades_execution' e 'signals_history' agora devem existir.")
    except Exception as e:
        print(f"🔥 Falha na inicialização do banco de dados: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup()
