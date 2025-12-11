import importlib
from co_piloto_quant import config

def load_strategy(mode: str = 'live'):
    """
    Carrega dinamicamente uma função de estratégia do módulo especificado
    em `config.ACTIVE_STRATEGY`.

    Args:
        mode (str): O modo de operação, 'live' para tempo real ou 
                    'vectorized' para backtesting.

    Returns:
        function: A função de estratégia apropriada.

    Raises:
        ImportError: Se o módulo da estratégia não for encontrado.
        AttributeError: Se uma função de estratégia adequada não for encontrada.
    """
    strategy_name = config.ACTIVE_STRATEGY
    module_path = f"co_piloto_quant.strategies.{strategy_name}"

    try:
        strategy_module = importlib.import_module(module_path)
    except ImportError:
        print(f"ERRO: Módulo da estratégia '{module_path}' não encontrado.")
        raise

    # Nomes das funções a procurar, em ordem de prioridade
    func_name_specific = f"check_rules_{mode}"
    func_name_generic = "check_rules"

    if hasattr(strategy_module, func_name_specific):
        print(f"INFO: Estratégia '{strategy_name}' (modo {mode}) carregada com sucesso.")
        return getattr(strategy_module, func_name_specific)
    
    if hasattr(strategy_module, func_name_generic):
        print(f"INFO: Estratégia genérica '{strategy_name}' carregada (fallback).")
        return getattr(strategy_module, func_name_generic)

    raise AttributeError(
        f"ERRO: Nenhuma função de estratégia encontrada no módulo '{module_path}'.\n"
        f"      O loader procurou por '{func_name_specific}' e '{func_name_generic}'.\n"
        f"      Certifique-se que sua estratégia define uma dessas funções."
    )

if __name__ == '__main__':
    # Teste rápido para verificar o carregador
    print("--- Testando o Carregador de Estratégia ---")
    
    # Teste 1: Carregar a estratégia 'rules' no modo vetorial
    config.ACTIVE_STRATEGY = 'rules'
    try:
        print(f"\n1. Carregando '{config.ACTIVE_STRATEGY}' no modo 'vectorized'")
        strategy_function = load_strategy(mode='vectorized')
        print(f"   -> Sucesso! Função: '{strategy_function.__name__}'")
        assert strategy_function.__name__ == 'check_rules_vectorized'
    except (ImportError, AttributeError) as e:
        print(f"   -> Falha no teste: {e}")

    # Teste 2: Carregar a estratégia 'rules' no modo live
    try:
        print(f"\n2. Carregando '{config.ACTIVE_STRATEGY}' no modo 'live'")
        strategy_function = load_strategy(mode='live')
        print(f"   -> Sucesso! Função: '{strategy_function.__name__}'")
        assert strategy_function.__name__ == 'check_rules_live'
    except (ImportError, AttributeError) as e:
        print(f"   -> Falha no teste: {e}")

    # Teste 3: Carregar a estratégia 'simple_trend' (que só tem 'check_rules')
    config.ACTIVE_STRATEGY = 'simple_trend'
    try:
        print(f"\n3. Carregando '{config.ACTIVE_STRATEGY}' (fallback genérico)")
        strategy_function = load_strategy(mode='live')
        print(f"   -> Sucesso! Função: '{strategy_function.__name__}'")
        assert strategy_function.__name__ == 'check_rules'
    except (ImportError, AttributeError) as e:
        print(f"   -> Falha no teste: {e}")

    # Teste 4: Tentar carregar uma estratégia que não existe
    print("\n4. Testando carregar uma estratégia inexistente...")
    config.ACTIVE_STRATEGY = 'non_existent_strategy'
    try:
        load_strategy()
    except ImportError:
        print("   -> SUCESSO: O erro de importação foi capturado como esperado.")
    finally:
        # Restaura a configuração original
        config.ACTIVE_STRATEGY = 'rules'
    
    print("\n--- Testes concluídos ---")
