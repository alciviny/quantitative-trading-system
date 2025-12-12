import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente (Senhas, Tokens) de um arquivo .env se existir
load_dotenv()

# --- 1. ESTRUTURA DE DIRETÓRIOS ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_PATH = PROJECT_ROOT / "src" / "co_piloto_quant" / "data"
RAW_DATA_PATH = DATA_PATH / "raw"
PROCESSED_DATA_PATH = DATA_PATH / "processed"

RAW_DATA_PATH.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_PATH.mkdir(parents=True, exist_ok=True)

# --- 2. CONFIGURAÇÕES DA ESTRATÉGIA (O CÉREBRO) ---
# Mudou aqui, muda no Backtest, no Scanner e no Robô ao mesmo tempo.

# Indicadores
BB_PERIOD = 200
BB_ENTRY_STD_DEV_DEFAULT = 0.45  # Parâmetro de fallback para o robô, caso não encontre no ranking
PRICE_BB_DEVIATIONS = [0.45, 1.0, 1.5, 2.0] # 0.45 é o "Squeeze" do Sniper
IFR_PERIOD = 120            # Período para o IFR (RSI)
SYSTEM_PERIOD = 200         # Período para o System TPM (OBTR/WAD)
SYSTEM_DEVIATIONS = [0.45, 1.5, 2.0] # Desvios para as bandas do System TPM

# Estocástico (Ajustado para 20 conforme seu input, mas monitore se não ficará muito rápido)
STOCH_K_PERIOD = 20
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

if __name__ == '__main__':
    print(f"✅ Configuração Carregada.")
    print(f"   Raiz: {PROJECT_ROOT}")
    print(f"   Modo Risco: {RISK_MODE}")
    print(f"   Filtros Forenses Ativos: Vol<{FILTER_MAX_VOLATILITY}%, Entropy<{FILTER_MAX_RAW_ENTROPY}")
    print(f"   Telegram Configurado? {'Sim' if TELEGRAM_TOKEN else 'Não'}")