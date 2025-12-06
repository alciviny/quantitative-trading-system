import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

# Configuração
ATIVO = "EURUSD"  # No MT5 geralmente não tem o ".SA"

def main():
    # 1. Conectar ao Terminal
    if not mt5.initialize():
        print(f"❌ Falha ao conectar no MT5. Erro: {mt5.last_error()}")
        return
    
    print(f"✅ Conectado ao MetaTrader 5 (Terminal: {mt5.version()})")
    print(f"   Conta: {mt5.account_info().login} | Servidor: {mt5.account_info().server}")

    # 2. Pegar Preço Spot
    tick = mt5.symbol_info_tick(ATIVO)
    if tick is None:
        print(f"❌ Ativo {ATIVO} não encontrado (verifique se está na Observação de Mercado).")
        mt5.shutdown()
        return
    
    spot_price = tick.last
    print(f"\n📈 {ATIVO} Spot Real: R$ {spot_price:.2f}")

    # 3. Buscar Opções (A Mágica)
    # No MT5, buscamos símbolos que começam com a raiz do ativo (ex: PETR*)
    print(f"🔍 Buscando opções de {ATIVO} no servidor...")
    
    # Pega todos os símbolos que contêm PETR (isso inclui a ação e as opções)
    symbols = mt5.symbols_get(group=f"*{ATIVO}*")
    
    options_data = []
    
    for s in symbols:
        # Filtra o que é Opção (básico)
        # Nota: A lógica exata de nome depende da corretora, mas geralmente opções têm letras de vencimento
        # Exemplo simples: ignorar o próprio ativo e fracionário
        if s.name in [ATIVO, f"{ATIVO}F"]:
            continue
            
        # Pega dados de mercado da opção
        opt_tick = mt5.symbol_info_tick(s.name)
        if opt_tick is None or opt_tick.last == 0:
            continue # Sem liquidez agora
            
        # Tenta inferir se é CALL ou PUT e Strike pelo nome (Ex: PETRA300)
        # Essa parte requer uma biblioteca de parser ou lógica específica da B3
        # Mas vamos apenas listar o que tem liquidez para testar
        options_data.append({
            'Ticker': s.name,
            'Preço': opt_tick.last,
            'Bid': opt_tick.bid,
            'Ask': opt_tick.ask,
            'Volume': opt_tick.volume_real
        })

    mt5.shutdown()

    # 4. Mostrar Resultado
    if options_data:
        df = pd.DataFrame(options_data)
        df = df.sort_values(by='Volume', ascending=False).head(10)
        print("\n📊 Top 10 Opções Mais Líquidas (Dados Reais):")
        print(df.to_string(index=False))
    else:
        print("⚠️ Nenhuma opção com liquidez encontrada agora (O mercado está aberto?).")

if __name__ == "__main__":
    main()