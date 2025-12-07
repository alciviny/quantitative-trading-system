import os
import sys
import pandas as pd
import MetaTrader5 as mt5
from datetime import datetime

# --- Adiciona o diretório 'src' ao sys.path para importações do projeto ---
# Isso garante que o script possa encontrar módulos como 'co_piloto_quant'
try:
    # Navega um nível acima (de 'scripts' para 'co-piloto-quant') e depois entra em 'src'
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    
    from co_piloto_quant.data.database import save_price_data
    from co_piloto_quant.config import TRADING_WHITELIST, MT5_TIMEFRAME_STR
except ImportError as e:
    print(f"❌ Erro de importação: {e}")
    print(f"Verifique se o diretório '{src_path}' foi adicionado corretamente ao path e contém o pacote 'co_piloto_quant'.")
    sys.exit(1)

# --- Constantes ---
# Converte a string do timeframe (ex: "M15") para a constante do MT5
TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1, "MN1": mt5.TIMEFRAME_MN1
}
TIMEFRAME = TIMEFRAME_MAP.get(MT5_TIMEFRAME_STR, mt5.TIMEFRAME_M15)
NUM_BARS = 10000

def sync_mt5_ticker_data(ticker: str):
    """
    Busca os dados de um ativo no MT5 e salva no banco de dados local.
    """
    print(f"🔄 Buscando dados para {ticker}...")
    try:
        # Busca os dados do MT5
        rates = mt5.copy_rates_from_pos(ticker, TIMEFRAME, 0, NUM_BARS)
        if rates is None or len(rates) == 0:
            print(f"  -> ⚠️ Não foram encontrados dados para {ticker}. Verifique se o ativo está disponível no seu terminal MT5.")
            return False

        # Converte para DataFrame
        df = pd.DataFrame(rates)
        
        # Formata as colunas para o padrão do projeto
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.rename(columns={
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume' # O banco de dados e a análise esperam 'volume'
        }, inplace=True)
        
        # Mantém apenas as colunas necessárias e define o índice
        df = df[['time', 'open', 'high', 'low', 'close', 'volume']]
        df.set_index('time', inplace=True)
        
        # Salva no banco de dados usando a função do projeto
        save_price_data(df, ticker)
        print(f"  -> ✅ Sucesso! {len(df)} barras de {ticker} salvas no banco de dados.")
        return True

    except Exception as e:
        print(f"  -> ❌ Erro ao processar {ticker}: {e}")
        return False

def get_assets_to_sync():
    """
    Determina a lista de ativos a sincronizar.
    Usa a TRADING_WHITELIST do config.py, ou uma lista padrão se estiver vazia.
    """
    if TRADING_WHITELIST:
        print("ℹ️ Usando a lista de ativos do arquivo de configuração (TRADING_WHITELIST).")
        return TRADING_WHITELIST
    else:
        print("⚠️ TRADING_WHITELIST está vazia. Usando uma lista padrão de ativos do mercado brasileiro.")
        # Símbolos comuns para contratos contínuos na B3 e principais ações.
        # Adapte conforme os símbolos exatos da sua corretora no MT5.
        default_assets = ['WIN$N', 'WDO$N', 'PETR4', 'VALE3', 'ITUB4', 'BBDC4']
        return default_assets

if __name__ == "__main__":
    # --- Conexão com o MetaTrader 5 ---
    try:
        if not mt5.initialize():
            print("❌ Falha ao inicializar o MetaTrader 5. Verifique se o terminal está em execução e se a integração está permitida.")
            sys.exit(1)
        print("✅ MetaTrader 5 inicializado com sucesso.")

        assets = get_assets_to_sync()
        
        print(f"\nIniciando sincronização para {len(assets)} ativo(s) no timeframe {MT5_TIMEFRAME_STR}.")
        print("-" * 50)

        success_count = 0
        fail_count = 0

        for asset in assets:
            if sync_mt5_ticker_data(asset):
                success_count += 1
            else:
                fail_count += 1
        
        print("-" * 50)
        print("Sincronização concluída.")
        print(f"  -> Ativos sincronizados com sucesso: {success_count}")
        print(f"  -> Falhas: {fail_count}")

    except Exception as e:
        print(f"❌ Ocorreu um erro inesperado: {e}")
    
    finally:
        # --- Encerra a conexão de forma segura ---
        mt5.shutdown()
        print("\n🔌 Conexão com MetaTrader 5 encerrada.")
