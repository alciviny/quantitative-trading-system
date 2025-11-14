import pandas as pd
import yahooquery as yq


def fetch_data(ativo: str, periodo: str = "5y", timeframe: str = "1d") -> pd.DataFrame:
   
    try:
        ticker = yq.Ticker(ativo)
        dados = ticker.history(period=periodo, interval=timeframe)

        if dados.empty:
            print(f"Aviso: Nenhum dado retornado para o ativo {ativo}.")
            return pd.DataFrame()

       
        if isinstance(dados.index, pd.MultiIndex):
            dados = dados.reset_index()
        else:
            dados = dados.reset_index()
            
        
        if 'index' in dados.columns:
            dados.rename(columns={'index': 'timestamp'}, inplace=True)
        if 'date' in dados.columns:
            dados.rename(columns={'date': 'timestamp'}, inplace=True)

        return dados
        
    except Exception as e:
        print(f"Erro ao buscar dados para {ativo}: {e}")
        return pd.DataFrame()


