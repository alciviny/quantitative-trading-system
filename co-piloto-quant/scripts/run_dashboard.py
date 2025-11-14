

from co_piloto_quant.data import fetch_data
from co_piloto_quant.analysis import calculate_indicators, check_rules


ATIVO = "PETR4.SA"
TIMEFRAME = "1d"

def run_analysis(asset: str, timeframe: str):
   
    dados = fetch_data(ativo=asset, timeframe=timeframe)

    dados_com_indicadores = calculate_indicators(dados)

    ultimo_candle = dados_com_indicadores.iloc[-1]

    resultados = check_rules(ultimo_candle)

 
    print("\n" + "="*40)
    print(f"--- Dashboard de Confirmação: {asset} ({timeframe}) ---")
    print("="*40)

    for regra, ativada in resultados.items():
        status = "SIM [✓]" if ativada else "NÃO [X]"
        print(f"[ ] {regra:<18}: {status}")

    regras_ativas = sum(resultados.values())
    total_regras = len(resultados)

    print("------------------------------------------")
    print(f"RESUMO: {regras_ativas} de {total_regras} regras ativas.")
    print("------------------------------------------\n")

if __name__ == "__main__":
  
    run_analysis(ATIVO, TIMEFRAME)