import pandas as pd
from datetime import datetime
from co_piloto_quant.analysis import calculate_indicators, check_rules, load_processed_data

def run_analysis(asset: str, timeframe: str, rsi_period: int) -> dict:
   
    dados = load_processed_data(ticker=asset)
    print(f"Total de dados carregados: {len(dados)} candles")

    if dados.empty:
        return {"success": False, "error": f"Não foi possível obter dados para o ativo '{asset}'. Execute o pipeline de dados primeiro."}

    dados_com_indicadores = calculate_indicators(dados, rsi_period=rsi_period)

    if 'RSI' not in dados_com_indicadores.columns or dados_com_indicadores['RSI'].isna().all():
        error_msg = (
            f"[ERRO] Não foi possível calcular o IFR (RSI) para o período {rsi_period}. "
            f"Dados disponíveis: {len(dados)} candles. "
            "Tente um período de IFR menor ou um timeframe maior."
        )
        return {"success": False, "error": error_msg}

    ultimo_candle = dados_com_indicadores.iloc[-1]
    resultados_regras = check_rules(ultimo_candle)
    
   
    dashboard_data = {
        "success": True,
        "asset": asset,
        "timeframe": timeframe,
        "rsi_period": rsi_period,
        "ultimo_rsi": ultimo_candle['RSI'],
        "resultados_regras": resultados_regras,
        "regras_ativas": sum(resultados_regras.values()),
        "total_regras": len(resultados_regras),
        "debug_df": dados_com_indicadores[['close', 'RSI']] 
    }
    return dashboard_data

def display_dashboard(data: dict):
  
    print("\n" + "="*40)
    print(f"--- Dashboard de Confirmação: {data['asset']} ({data['timeframe']}) ---")
    print(f"Período IFR: {data['rsi_period']}")
    print("="*40)

    for regra, ativada in data['resultados_regras'].items():
        status = "SIM [✓]" if ativada else "NÃO [X]"
        print(f"[ ] {regra:<18}: {status}")

    print("------------------------------------------")
    print(f"RESUMO: {data['regras_ativas']} de {data['total_regras']} regras ativas.")
    print("------------------------------------------\n")


import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dashboard de Análise Técnica de Ativos.")
    parser.add_argument("--ticker", type=str, required=True, help="O ticker do ativo a ser analisado (ex: PETR4.SA).")
    
    args = parser.parse_args()

    
    TIMEFRAME = "1d"
    RSI_PERIOD = 120 
    
  
    analysis_result = run_analysis(args.ticker, TIMEFRAME, RSI_PERIOD)
    
    # 2. Se a análise for bem-sucedida, exibe os resultados
    if analysis_result["success"]:
        print("\nÚltimos 5 candles com indicadores:")
        print(analysis_result['debug_df'].tail())
        print(f"\nO valor do último IFR calculado é: {analysis_result['ultimo_rsi']:.2f}")
        
        display_dashboard(analysis_result)
    else:
        print(f"\n[FALHA NA ANÁLISE] {analysis_result['error']}")
        print("Por favor, execute 'python scripts/run_pipeline.py --ticker SEU_ATIVO' para gerar os dados necessários.")