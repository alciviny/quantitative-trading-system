import sys
import os
import logging
from tqdm import tqdm

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
    logger.info("🚀 Iniciando atualização de dados de mercado para todo o universo...")
    
    tickers = get_expanded_universe()
    if not tickers:
        logger.error("A lista de tickers do universo está vazia. Abortando.")
        return

    logger.info(f"Universo contém {len(tickers)} ativos para verificar/atualizar.")

    # O DataManager já é otimizado para buscar em paralelo com get_data_batch.
    # No entanto, uma chamada a get_data para cada um também funciona e pode dar um feedback melhor
    # em um loop simples como este. Vamos usar o batch para eficiência.
    
    print("\n[INFO] O processo pode levar vários minutos, dependendo da quantidade de dados a serem baixados.")
    
    # O método get_data_batch já mostra um log.
    # Não precisamos de um tqdm aqui, pois o log interno já dá o feedback.
    results = data_manager.get_data_batch(tickers, force_update=False)
    
    success_count = sum(1 for df in results.values() if not df.empty)
    fail_count = len(tickers) - success_count
    
    print("-" * 50)
    logger.info("✅ Processo de atualização concluído.")
    logger.info(f"Ativos processados com sucesso: {success_count}")
    logger.info(f"Ativos que falharam ou não retornaram dados: {fail_count}")


if __name__ == "__main__":
    update_data()
