from pathlib import Path
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente (Senhas, Tokens) de um arquivo .env se existir
load_dotenv()


# --- 1. ESTRUTURA DE DIRETÓRIOS ---
# Detecta a raiz do projeto (assumindo que o config.py está em src/co_piloto_quant/config.py)
# Isso torna o código robusto para ser executado de qualquer lugar.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Define o diretório de dados principal DENTRO do src (padrão novo)
DATA_DIR = PROJECT_ROOT / "src" / "co_piloto_quant" / "data"

# Cria constantes explícitas para cada subdiretório de dados
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = DATA_DIR / "results"
MODELS_DIR = PROJECT_ROOT / "models" # Adicionado para consistência

# Não cria diretórios automaticamente aqui para evitar sobrescrita indevida


# --- 2. CONFIGURAÇÕES DA ESTRATÉGIA (O CÉREBRO) ---
# Mudou aqui, muda no Backtest, no Scanner e no Robô ao mesmo tempo.

# Indicadores
BB_PERIOD = 80
BB_ENTRY_STD_DEV_DEFAULT = 0.45  # Parâmetro de fallback para o robô, caso não encontre no ranking
PRICE_BB_DEVIATIONS = [0.45, 1.0, 1.5, 2.0] # 0.45 é o "Squeeze" do Sniper
IFR_PERIOD = 14            # Período para o IFR (RSI)
SYSTEM_PERIOD = 200         # Período para o System TPM (OBTR/WAD)
SYSTEM_DEVIATIONS = [0.45, 1.5, 2.0] # Desvios para as bandas do System TPM

# Estocástico (Ajustado para 20 conforme seu input, mas monitore se não ficará muito rápido)
STOCH_K_PERIOD = 14
STOCH_K_SMOOTH = 3
STOCH_D_SMOOTH = 3

# Períodos do Filtro Hilbert (Ehlers)
HILBERT_SHORT_PERIOD = 10
HILBERT_LONG_PERIOD = 20

# Filtros de Regime (Hurst/Entropia)
HURST_WINDOW = 72
ENTROPY_WINDOW = 20
REGIME_STRICTNESS = 'NORMAL' # 'LOOSE', 'NORMAL', 'STRICT'
HURST_THRESHOLD_TREND = 0.54
HURST_THRESHOLD_REVERSION = 0.46

# --- 2.1. SELEÇÃO DA ESTRATÉGIA ATIVA ---
# Define qual arquivo de estratégia dentro da pasta 'strategies' será carregado.
# O nome deve ser exatamente o do arquivo, sem a extensão .py.
# Ex: 'rules' para carregar 'strategies/rules.py'
ACTIVE_STRATEGY = 'rules'

# --- NOVO: FILTROS FORENSES (A "Vacina" Anti-Loss) ---
# Baseado na Análise Forense de 07/12/2025:
# - Ativos com Volatilidade > 2.1% ao dia tendem a estopar.
# - Ativos com Entropia > 2.80 são caóticos demais para o setup.
FILTER_MAX_VOLATILITY = 2.1
FILTER_MAX_RAW_ENTROPY = 2.80

# --- 3. CONFIGURAÇÕES OPERACIONAIS (ROBÔ MT5) ---
# Parâmetros de execução
MT5_TIMEFRAME_STR = "M15"  # String para logs/relatórios
MT5_MAGIC_NUMBER = 777888  # Identidade do robô
MT5_DEVIATION = 20         # Desvio máximo aceitável em pontos
MT5_MAX_POSITIONS = 5      # Gerenciamento de Risco: Máximo de trades simultâneos

# Gestão de Risco por Trade (Fixo ou Calculado)
RISK_MODE = "FIXED_LOT"    # Opções: 'FIXED_LOT' ou 'PERCENT_RISK'
FIXED_LOT_SIZE = 0.01      # Se usar lote fixo
RISK_PERCENT = 1.0         # Se usar risco percentual (1% da conta)

# Ativos Permitidos (Whitelist)
# Se vazio [], o robô pega o que estiver na "Observação de Mercado" do MT5
TRADING_WHITELIST = []
# Exemplo: TRADING_WHITELIST = ['EURUSD', 'GBPUSD', 'XAUUSD']

# --- 4. INTEGRAÇÕES (TELEGRAM) ---
# Pega do sistema ou arquivo .env para segurança
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- 5. BANCO DE DADOS ---
# Centraliza a definição do caminho do banco de dados
DATABASE_PATH = RAW_DIR / "market_data.db"


class Config:
    """
    Classe de configuração para agrupar todas as constantes do projeto.
    Fornece acesso fácil e autocompletar em IDEs.
    """
    # Paths
    PROJECT_ROOT = PROJECT_ROOT
    DATA_DIR = DATA_DIR
    RAW_DIR = RAW_DIR
    PROCESSED_DIR = PROCESSED_DIR
    RESULTS_DIR = RESULTS_DIR
    MODELS_DIR = MODELS_DIR
    DATABASE_PATH = DATABASE_PATH

    # Strategy
    BB_PERIOD = BB_PERIOD
    BB_ENTRY_STD_DEV_DEFAULT = BB_ENTRY_STD_DEV_DEFAULT
    PRICE_BB_DEVIATIONS = PRICE_BB_DEVIATIONS
    IFR_PERIOD = IFR_PERIOD
    SYSTEM_PERIOD = SYSTEM_PERIOD
    SYSTEM_DEVIATIONS = SYSTEM_DEVIATIONS
    STOCH_K_PERIOD = STOCH_K_PERIOD
    STOCH_K_SMOOTH = STOCH_K_SMOOTH
    STOCH_D_SMOOTH = STOCH_D_SMOOTH
    HILBERT_SHORT_PERIOD = HILBERT_SHORT_PERIOD
    HILBERT_LONG_PERIOD = HILBERT_LONG_PERIOD
    HURST_WINDOW = HURST_WINDOW
    ENTROPY_WINDOW = ENTROPY_WINDOW
    REGIME_STRICTNESS = REGIME_STRICTNESS
    HURST_THRESHOLD_TREND = HURST_THRESHOLD_TREND
    HURST_THRESHOLD_REVERSION = HURST_THRESHOLD_REVERSION
    ACTIVE_STRATEGY = ACTIVE_STRATEGY

    # Forensic Filters
    FILTER_MAX_VOLATILITY = FILTER_MAX_VOLATILITY
    FILTER_MAX_RAW_ENTROPY = FILTER_MAX_RAW_ENTROPY

    # MT5
    MT5_TIMEFRAME_STR = MT5_TIMEFRAME_STR
    MT5_MAGIC_NUMBER = MT5_MAGIC_NUMBER
    MT5_DEVIATION = MT5_DEVIATION
    MT5_MAX_POSITIONS = MT5_MAX_POSITIONS
    RISK_MODE = RISK_MODE
    FIXED_LOT_SIZE = FIXED_LOT_SIZE
    RISK_PERCENT = RISK_PERCENT
    TRADING_WHITELIST = TRADING_WHITELIST

    # Integrations
    TELEGRAM_TOKEN = TELEGRAM_TOKEN
    TELEGRAM_CHAT_ID = TELEGRAM_CHAT_ID


if __name__ == '__main__':
    print(f"✅ Configuração do Projeto Carregada")
    print(f"   - Raiz do Projeto: {Config.PROJECT_ROOT}")
    print(f"   - Diretório de Dados: {Config.DATA_DIR}")
    print(f"   - Banco de Dados: {Config.DATABASE_PATH}")
    print(f"   - Filtros Forenses: Volatilidade < {Config.FILTER_MAX_VOLATILITY}%, Entropia Bruta < {Config.FILTER_MAX_RAW_ENTROPY}")
    print(f"   - Estratégia Ativa: '{Config.ACTIVE_STRATEGY}'")
    print(f"   - Telegram Configurado: {'Sim' if Config.TELEGRAM_TOKEN else 'Não'}")

