import sys
import os
import logging
from tqdm import tqdm

# Garante que o src esteja no sys.path para importação correta
SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if SRC_PATH not in sys.path:
    sys.path.insert(0, SRC_PATH)

# Log de ambiente para debug
print(f"[DEBUG] CWD: {os.getcwd()}")
print(f"[DEBUG] PYTHONPATH: {os.environ.get('PYTHONPATH', '')}")
print(f"[DEBUG] sys.path: {sys.path}")

# Adiciona o diretório raiz ao sys.path para permitir importações relativas
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.co_piloto_quant.data.data_manager import data_manager
    from src.co_piloto_quant.universe import get_expanded_universe
except (ModuleNotFoundError, ImportError) as e:
    print(f"❌ Erro: Não foi possível importar os módulos necessários. Verifique a estrutura do projeto.")
    print(f"Detalhe: {e}")
    sys.exit(1)

# Configuração do Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataUpdater")


def update_data():
    """
    Busca e atualiza os dados de mercado para todo o universo de ativos.
    Utiliza o DataManager para buscar apenas os dados incrementais necessários.
    """
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), '..', 'src', 'co_piloto_quant', 'data', 'raw', 'market_data.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS ohlcv (
            date TEXT NOT NULL,
            ticker TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume REAL,
            PRIMARY KEY (date, ticker)
        )''')
        conn.execute('''CREATE TABLE IF NOT EXISTS assets (
            ticker TEXT PRIMARY KEY,
            name TEXT,
            sector TEXT,
            industry TEXT,
            country TEXT,
            last_update TEXT
        )''')
        # Garante que a coluna last_update existe na tabela assets (caso banco antigo)
        cursor = conn.execute("PRAGMA table_info(assets)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'last_update' not in columns:
            conn.execute('ALTER TABLE assets ADD COLUMN last_update TEXT')
            logger.info('Coluna last_update adicionada à tabela assets.')
        conn.commit()
    logger.info('Tabelas ohlcv e assets garantidas no banco de dados.')
    logger.info("🚀 Iniciando atualização de dados de mercado para todo o universo...")
    
    tickers = get_expanded_universe()
    logger.info(f"Universo original contém {len(tickers)} ativos.")
    # Filtra apenas ativos brasileiros (terminam com .SA)
    br_tickers = [t for t in tickers if t.upper().endswith('.SA')]
    logger.info(f"Universo filtrado para ativos brasileiros: {len(br_tickers)} ativos (.SA)")
    if not br_tickers:
        logger.error("Nenhum ativo brasileiro (.SA) encontrado no universo. Abortando.")
        return

    logger.info(f"Universo contém {len(tickers)} ativos para verificar/atualizar.")

    # O DataManager já é otimizado para buscar em paralelo com get_data_batch.
    # No entanto, uma chamada a get_data para cada um também funciona e pode dar um feedback melhor
    # em um loop simples como este. Vamos usar o batch para eficiência.

    print("\n[INFO] O processo pode levar vários minutos, dependendo da quantidade de dados a serem baixados.")

    # O método get_data_batch já mostra um log.
    # Não precisamos de um tqdm aqui, pois o log interno já dá o feedback.
    logger.debug(f"Tickers brasileiros: {br_tickers}")
    logger.info(f"Iniciando download de {len(br_tickers)} ativos brasileiros...")
    
    try:
        results = data_manager.get_data_batch(br_tickers, force_update=False)
    except Exception as e:
        logger.error(f"Erro ao baixar dados em batch: {e}", exc_info=True)
        return

    success_count = sum(1 for df in results.values() if df is not None and not df.empty)
    fail_count = len(br_tickers) - success_count

    # Listar ativos baixados com sucesso
    success_tickers = [t for t, df in results.items() if df is not None and not df.empty]

    print("-" * 50)
    logger.info("✅ Processo de atualização concluído.")
    logger.info(f"Ativos processados com sucesso: {success_count}")
    logger.info(f"Lista de ativos baixados com sucesso: {success_tickers}")
    logger.info(f"Ativos que falharam ou não retornaram dados: {fail_count}")
    if fail_count > 0:
        failed = [t for t, df in results.items() if df is None or df.empty]
        if failed:
            logger.error(f"Ativos que falharam: {failed}")
            logger.warning("Alguns ativos não foram baixados, mas o pipeline continuará com os disponíveis.")


if __name__ == "__main__":
    update_data()
