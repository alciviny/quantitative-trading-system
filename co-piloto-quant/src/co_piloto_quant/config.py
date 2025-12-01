from pathlib import Path

# Define a raiz do projeto dinamicamente.
# __file__ se refere a este arquivo (config.py).
# .parent se refere ao diretório pai.
# .resolve() torna o caminho absoluto.
# A estrutura é: <project_root>/src/co_piloto_quant/config.py
# Então, precisamos subir três níveis para chegar à raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Define os caminhos para as pastas de dados com base na raiz do projeto.
DATA_PATH = PROJECT_ROOT / "src" / "co_piloto_quant" / "data"
RAW_DATA_PATH = DATA_PATH / "raw"
PROCESSED_DATA_PATH = DATA_PATH / "processed"

# Cria os diretórios se eles não existirem.
# O argumento parents=True garante que todos os diretórios pais necessários sejam criados.
# O argumento exist_ok=True evita um erro se os diretórios já existirem.
RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)


# --- Parâmetros dos Indicadores ---
# Usados como valores padrão nos scripts de visualização e análise.

# Parâmetros para Bandas de Bollinger de Preço
BB_PERIOD = 200
# Desvios para as Bandas de Bollinger de PREÇO
# Inclui 0.45 (Squeeze), 1.0 (Consolidação), 1.5 e 2.0 (Alvos/Exaustão)
PRICE_BB_DEVIATIONS = [0.45, 1.0, 1.5, 2.0]

# Período para o IFR (Índice de Força Relativa)
IFR_PERIOD = 120

# Período para o System TPM
SYSTEM_PERIOD = 200
SYSTEM_DEVIATIONS = [0.45, 1.0, 1.5, 2.0]

# Parâmetros para o Estocástico Lento Customizado
STOCH_K_PERIOD = 80  # Janela de lookback
STOCH_K_SMOOTH = 3   # Suavização do %K (Média Simples)
STOCH_D_SMOOTH = 3   # Suavização do %D (Linha de Sinal - Média Simples)

# Parâmetros Ehlers Hilbert
HILBERT_LONG_PERIOD = 40  # Janela de Swing Trade
HILBERT_SHORT_PERIOD = 6  # Filtro de Ruído


if __name__ == '__main__':
    # Este bloco é útil para depuração, para verificar se os caminhos estão corretos.
    print(f"Raiz do Projeto: {PROJECT_ROOT}")
    print(f"Pasta de Dados: {DATA_PATH}")
    print(f"Pasta de Dados Brutos: {RAW_DATA_PATH}")
    print(f"Pasta de Dados Processados: {PROCESSED_DATA_PATH}")
