""" 
import yfinance as yf
import pandas as pd
from typing import List, Dict

# Importa a função para salvar os dados no banco de dados.
from co_piloto_quant.data.database import save_price_data, init_db

def fetch_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
  
  
    print(f"Buscando dados para {ticker} de {start_date} a {end_date}...")
    data = yf.download(ticker, start=start_date, end=end_date)

    if data.empty:
        print(f"Nenhum dado encontrado para {ticker}. O ticker pode estar incorreto ou não há dados para o período.")
        return data

    try:
        # Salva os dados baixados no banco de dados.
        save_price_data(data, ticker)
        print(f"Dados de {ticker} salvos com sucesso no banco de dados.")
    except Exception as e:
        print(f"Erro ao salvar os dados de {ticker} no banco de dados: {e}")

    return data

def fetch_batch_data(tickers: List[str], start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
 
    print(f"Iniciando busca em lote para {len(tickers)} ativos...")
    # O yfinance baixa os dados de todos os tickers de uma vez
    # O resultado é um DataFrame com multi-index nas colunas (ex: ('Open', 'PETR4.SA'))
    all_data = yf.download(tickers, start=start_date, end=end_date, group_by='ticker')

    processed_data = {}
    if all_data.empty:
        print("Nenhum dado foi retornado na busca em lote.")
        return processed_data

    for ticker in tickers:
        # Extrai os dados de cada ticker do DataFrame multi-indexado
        ticker_data = all_data[ticker]

        # Remove linhas onde todos os valores são NaN (pode acontecer em buscas em lote)
        ticker_data.dropna(inplace=True)

        if ticker_data.empty:
            print(f"Nenhum dado válido para {ticker} no lote.")
            continue

        try:
            # Salva os dados do ticker específico no banco de dados
            save_price_data(ticker_data, ticker)
            print(f"Dados de {ticker} do lote salvos com sucesso no banco de dados.")
            processed_data[ticker] = ticker_data
        except Exception as e:
            print(f"Erro ao salvar dados de {ticker} do lote no banco de dados: {e}")

    print("Busca em lote finalizada.")
    return processed_data

if __name__ == '__main__':
    # Exemplo de uso do módulo
    
    # Primeiro, garanta que o banco de dados e as tabelas existam
    print("Inicializando o banco de dados para o teste...")
    init_db()

    # Tickers de exemplo
    ativos_exemplo = ["PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "WEGE3.SA"]
    data_inicio = "2023-01-01"
    data_fim = "2023-12-31"

    # 1. Testando a busca de um único ativo
    print("\n--- Teste de Busca Individual ---")
    petr4_data = fetch_data("PETR4.SA", start_date=data_inicio, end_date=data_fim)
    if not petr4_data.empty:
        print(f"\nExemplo de dados baixados para PETR4.SA:")
        print(petr4_data.head())

    # 2. Testando a busca em lote
    print("\n--- Teste de Busca em Lote ---")
    # Usando uma lista menor para o exemplo não ser muito longo
    dados_em_lote = fetch_batch_data(
        tickers=["VALE3.SA", "WEGE3.SA", "TICKER_INVALIDO"],
        start_date=data_inicio,
        end_date=data_fim
    )

    if dados_em_lote:
        print("\nVerificando dados baixados em lote:")
        for ticker, df in dados_em_lote.items():
            print(f"\n--- {ticker} ---")
            print(df.head())
    else:
        print("Nenhum dado foi processado no lote.")
 """

"""
Módulo para buscar dados de mercado usando a API yfinance.
Salva os dados diretamente no banco SQLite, eliminando CSVs brutos.
"""
import yfinance as yf
import pandas as pd
from typing import List, Dict, Optional

# Importa a função para salvar no banco
from co_piloto_quant.data.database import save_price_data, init_db

def fetch_data(ticker: str, period: str = "max", interval: str = "1d", 
               start: Optional[str] = None, end: Optional[str] = None) -> pd.DataFrame:
    """
    Busca dados históricos de um ativo e salva no banco de dados.
    Suporta tanto 'period' (ex: '1y') quanto datas específicas (start/end).
    """
    print(f"Buscando dados para {ticker}...")
    
    # Lógica Híbrida: Se passar datas, usa datas. Se não, usa período.
    if start and end:
        data = yf.download(ticker, start=start, end=end, interval=interval, progress=False)
    else:
        data = yf.download(ticker, period=period, interval=interval, progress=False)

    if data.empty:
        print(f"ALERTA: Nenhum dado encontrado para {ticker}.")
        return data

    try:
        # O Pulo do Gato: Salvamos no banco, não em CSV
        save_price_data(data, ticker)
    except Exception as e:
        print(f"ERRO CRÍTICO ao salvar {ticker} no banco: {e}")

    return data

def fetch_batch_data(tickers: List[str], period: str = "max", interval: str = "1d") -> Dict[str, pd.DataFrame]:
    """
    Busca dados em lote para otimizar a conexão e salva no banco.
    """
    print(f"Iniciando download em lote para {len(tickers)} ativos (Periodo: {period})...")
    
    # Download massivo
    all_data = yf.download(tickers, period=period, interval=interval, group_by='ticker', threads=True)
    
    processed_data = {}
    
    if all_data.empty:
        print("Falha total no download em lote.")
        return processed_data

    # Itera sobre os tickers para salvar um por um no banco
    for ticker in tickers:
        try:
            # Em lote, o yfinance retorna um MultiIndex se houver mais de 1 ticker
            # Se for só 1 ticker na lista, ele não retorna MultiIndex (cuidado!)
            if len(tickers) > 1:
                ticker_data = all_data[ticker]
            else:
                ticker_data = all_data

            # Limpeza básica de linhas vazias que vêm no lote
            ticker_data = ticker_data.dropna(how='all')

            if not ticker_data.empty:
                save_price_data(ticker_data, ticker)
                processed_data[ticker] = ticker_data
        except KeyError:
            print(f"Aviso: Dados para {ticker} não encontrados no pacote do lote.")
        except Exception as e:
            print(f"Erro ao processar {ticker}: {e}")

    print(f"Processamento em lote concluído. {len(processed_data)} ativos atualizados no Banco de Dados.")
    return processed_data