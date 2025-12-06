"""
Script Mestre de Estratégia - Orquestrador de Sinais e Opções

Este script é o cérebro do sistema, executando o seguinte fluxo:
1.  Recebe um ticker de ativo-objeto como entrada.
2.  Usa o `analysis.py` para gerar um sinal direcional (Compra, Venda, Neutro) para o ativo.
3.  Se houver um sinal, usa a lógica do `scan_options.py` para buscar e processar a cadeia de opções.
4.  Filtra as opções candidatas (CALLs para Compra, PUTs para Venda) com base em critérios de Delta.
5.  Seleciona a "Top Pick" (melhor opção) e apresenta um relatório completo.
"""
import sys
import os
import argparse
import pandas as pd
import yfinance as yf
from joblib import Parallel, delayed

# --- 1. AJUSTE DE PATH PARA ENCONTRAR O PACOTE 'co_piloto_quant' ---
# Adiciona o diretório raiz do projeto ao path do Python
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# --- 2. IMPORTS DOS MÓDULOS DO PROJETO ---
# Importa as engines de análise e precificação
from src.co_piloto_quant.analysis import calculate_indicators, check_rules
# Reutiliza a lógica de busca e processamento de opções do scanner
# (Idealmente, estas funções estariam em um módulo em `src`, como `options_analyzer.py`)
from scripts.scan_options import fetch_option_chain, process_option

# Configurações
RISK_FREE_RATE = 0.1225
pd.set_option('display.width', 1000)

def get_underlying_data(ticker):
    """Busca dados históricos e o preço spot do ativo-objeto."""
    try:
        hist_data = yf.download(ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
        if hist_data.empty:
            print(f"ERRO: Não foram encontrados dados históricos para {ticker}.")
            return None, None

        # Garante que os nomes das colunas sejam simples (sem MultiIndex) e minúsculos.
        if isinstance(hist_data.columns, pd.MultiIndex):
            # No caso de MultiIndex (ex: [('Close', 'PETR4.SA')]), mantém apenas o primeiro nível.
            hist_data.columns = hist_data.columns.get_level_values(0)

        # Converte todas as colunas para minúsculas para padronizar (ex: 'Close' -> 'close').
        hist_data.columns = [col.lower() for col in hist_data.columns]

        spot_price = hist_data['close'].iloc[-1]
        return hist_data, spot_price
    except Exception as e:
        print(f"ERRO ao baixar dados do ativo-objeto: {e}")
        return None, None

def run_strategy(ticker: str):
    """
    Executa a estratégia completa de análise do ativo e seleção de opção.
    """
    print(f"--- Iniciando Estratégia para: {ticker} ---")

    # --- PASSO 1: ANÁLISE DIRECIONAL DO ATIVO-OBJETO ---
    print("\n[PASSO 1/3] Analisando sinal direcional do ativo-objeto...")
    df_hist, spot_price = get_underlying_data(ticker)
    if df_hist is None:
        return

    # Calcula indicadores e regras
    df_indicators = calculate_indicators(df_hist)
    
    # --- MODO DE TESTE (COMENTE A LINHA ORIGINAL ABAIXO) ---
    # rules_result = check_rules(df_indicators) # <--- Linha original comentada
    
    print("\n⚠️ MODO DE TESTE ATIVADO: Forçando sinal de COMPRA em PETR4...")
    rules_result = {
        'Sinal_Compra': True,      # Forçando TRUE para testar o fluxo de Call
        'Sinal_Venda': False,
        'Motivo_Bloqueio': 'Teste de Integração (Sinal Forçado)'
    }
    # -------------------------------------------------------

    # Extrai informações de diagnóstico do último registro
    latest_data = df_indicators.iloc[-1]
    diagnostico = {
        "Preço Spot": f"R$ {spot_price:.2f}",
        "Sinal": rules_result.get('Motivo_Bloqueio', 'NEUTRO'),
        "Hurst": f"{latest_data.get('Hurst_72_returns', 0):.2f}",
        "Entropia": f"{latest_data.get('Entropy_20', 0):.2f}",
        "Half-Life": f"{latest_data.get('HalfLife_60', 0):.0f} dias"
    }

    # Decide a direção
    option_type = None
    if rules_result.get('Sinal_Compra', False):
        option_type = 'call'
        delta_range = (0.40, 0.60)
        print("sinal de COMPRA detectado. Buscando CALLs...")
    elif rules_result.get('Sinal_Venda', False):
        option_type = 'put'
        # Delta de PUT é negativo
        delta_range = (-0.60, -0.40)
        print("sinal de VENDA detectado. Buscando PUTs...")
    else:
        print("Sinal NEUTRO. Nenhuma operação de opção recomendada.")
        # Imprime o relatório final mesmo se for neutro
        print_report(diagnostico)
        return

    # --- PASSO 2: BUSCA E ANÁLISE DA CADEIA DE OPÇÕES ---
    print(f"\n[PASSO 2/3] Buscando e processando opções ({option_type.upper()})...")
    
    # Reutiliza a função do scanner (com fallback de simulação embutido)
    df_options_raw = fetch_option_chain(ticker, spot_price)
    if df_options_raw.empty:
        print("ERRO: Falha ao obter a cadeia de opções.")
        return

    # Filtra apenas o tipo de opção que nos interessa ANTES de processar
    df_options_filtered_type = df_options_raw[df_options_raw['type'] == option_type].copy()
    
    # Processa as opções em paralelo usando a lógica do scanner
    results = Parallel(n_jobs=-1)(
        delayed(process_option)(row, spot_price) 
        for _, row in df_options_filtered_type.iterrows()
    )
    
    clean_results = [r for r in results if r is not None]
    if not clean_results:
        print("Nenhuma opção válida encontrada após processamento.")
        print_report(diagnostico) # Imprime o diagnóstico mesmo sem opção
        return
        
    df_processed_options = pd.DataFrame(clean_results)

    # --- PASSO 3: FILTRAGEM E SELEÇÃO DA "TOP PICK" ---
    print(f"\n[PASSO 3/3] Filtrando e selecionando a melhor opção...")

    # Filtra pelo range de Delta
    candidates = df_processed_options[
        (df_processed_options['Delta'] >= delta_range[0]) &
        (df_processed_options['Delta'] <= delta_range[1])
    ].copy()

    if candidates.empty:
        print(f"Nenhuma opção encontrada com Delta entre {delta_range[0]:.2f} e {delta_range[1]:.2f}.")
        print_report(diagnostico)
        return

    # Critério de seleção: A opção "mais barata" em termos de Volatilidade Implícita
    top_pick = candidates.sort_values(by='IV', ascending=True).iloc[0]
    
    # --- RELATÓRIO FINAL ---
    print_report(diagnostico, option_type, top_pick)


def print_report(diagnostico, decision=None, top_pick=None):
    """Imprime o relatório final da estratégia."""
    print("\n" + "="*50)
    print("      RELATÓRIO DE ESTRATÉGIA QUANTITATIVA")
    print("="*50)
    
    print("\n--- Diagnóstico do Ativo Objeto ---")
    for key, value in diagnostico.items():
        print(f"  - {key:<12}: {value}")
        
    print("\n--- Decisão da Estratégia ---")
    if decision is None:
        print("  >> AGUARDAR: Ativo sem sinal direcional claro.")
    elif top_pick is None:
        print(f"  >> AGUARDAR: Sinal de {decision.upper()} presente, mas nenhuma opção candidata encontrada.")
    else:
        print(f"  >> EXECUTAR: Comprar {decision.upper()}")
        print("\n--- Opção Selecionada (Top Pick) ---")
        print(f"  - Ticker      : {top_pick['Ticker']}")
        print(f"  - Strike      : R$ {top_pick['Strike']:.2f}")
        print(f"  - Preço       : R$ {top_pick['Preco']:.2f}")
        print(f"  - Vencimento  : {top_pick['Dias']} dias úteis")
        print(f"  - Delta       : {top_pick['Delta']:.3f} (Dentro do alvo)")
        print(f"  - IV          : {top_pick['IV']:.2%} (Mais baixa encontrada)")
        print(f"  - Theta       : {top_pick['Theta']:.4f} (Custo por dia)")
        
    print("\n" + "="*50)


if __name__ == "__main__":
    # Configura o parser de argumentos para receber o ticker da linha de comando
    parser = argparse.ArgumentParser(description="Roda a estratégia de análise de ativo e seleção de opção.")
    parser.add_argument("ticker", type=str, help="O ticker do ativo-objeto a ser analisado (ex: PETR4.SA).")
    
    args = parser.parse_args()
    
    run_strategy(args.ticker)
