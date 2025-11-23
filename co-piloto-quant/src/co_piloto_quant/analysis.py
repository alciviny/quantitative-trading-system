
# src/co_piloto_quant/analysis.py

import pandas as pd
from pathlib import Path
import argparse  # Adicionado
from co_piloto_quant.config import PROCESSED_DATA_PATH
from co_piloto_quant.indicators.ww_moving_average import ww_moving_average
from co_piloto_quant.indicators.stochastic_custom import calculate_stochastic_custom
from co_piloto_quant.indicators.system_tpm import calculate_system_tpm

def load_processed_data(ticker: str) -> pd.DataFrame:
    """Carrega os dados processados de um arquivo CSV."""
    file_path = PROCESSED_DATA_PATH / f"{ticker}_processed.csv"
    if not file_path.exists():
        print(f"Arquivo de dados processados não encontrado para {ticker} em {file_path}")
        return pd.DataFrame()
    
    print(f"Carregando dados processados de {file_path}...")
    df = pd.read_csv(file_path, index_col=0, parse_dates=True)
    return df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula todos os indicadores técnicos necessários para a estratégia.
    Foca no System TPM e Estocástico Customizado.
    """
    # 1. Indicador de Tendência: WWMA 200
    # Correção: Usando 'column' e 'period' e atribuindo a uma nova coluna
    df['WWMA_200'] = ww_moving_average(df, period=200, column='close')

    # 2. Estocástico Customizado
    # Correção: Usando join para adicionar as colunas sem perder os dados originais
    stoch_df = calculate_stochastic_custom(df)
    df = df.join(stoch_df)

    # 3. System TPM com OBTR
    # Correção: Usando join
    obtr_tpm = calculate_system_tpm(df, indicator='obtr')
    # O calculate_system_tpm retorna o indicador + bandas. 
    # Precisamos tratar colunas duplicadas se já existirem, mas o join lida bem com índices alinhados.
    # Para segurança, removemos colunas que possam conflitar antes do join ou usamos sufixos, 
    # mas aqui vamos assumir que as colunas são únicas.
    df = df.join(obtr_tpm)

    # 4. System TPM com WAD
    wad_tpm = calculate_system_tpm(df, indicator='wad')
    df = df.join(wad_tpm)
    
    return df

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica as regras de trading baseadas nos dados mais recentes.
    """
    rules = {
        'Tendencia Macro': latest_data['close'] > latest_data['WWMA_200'],
        'Sinal Estocastico': latest_data['stoch_k_80_3'] > latest_data['stoch_d_14'],
        'OBTR - Tendencia': latest_data['obtr'] > latest_data['obtr_bb_middle_band'],
        'OBTR - Consolidacao (0.45)': (
            (latest_data['obtr'] > latest_data['obtr_bb_lower_band_0_45']) &
            (latest_data['obtr'] < latest_data['obtr_bb_upper_band_0_45'])
        ),
        'WAD - Tendencia': latest_data['wad'] > latest_data['wad_bb_middle_band'],
        'WAD - Consolidacao (0.45)': (
            (latest_data['wad'] > latest_data['wad_bb_lower_band_0_45']) &
            (latest_data['wad'] < latest_data['wad_bb_upper_band_0_45'])
        ),
    }
    return rules

def main():
    """
    Função principal para rodar a análise de um ticker.
    """
    # Adicionado para aceitar argumento de linha de comando
    parser = argparse.ArgumentParser(description="Script de análise de indicadores para um ativo.")
    parser.add_argument('--ticker', type=str, default="PETR4.SA", help='O ticker do ativo a ser analisado (ex: PETR4.SA).')
    args = parser.parse_args()
    ticker = args.ticker

    # Carregar dados
    df = load_processed_data(ticker)
    if df.empty:
        print(f"Não foram encontrados dados para {ticker}.")
        return

    # Calcular indicadores
    # Usamos .copy() para garantir que não afetamos o dataframe original se ele for usado fora daqui
    df_with_indicators = calculate_indicators(df.copy())
    
    # Pegar o dado mais recente (último candle)
    latest_data = df_with_indicators.iloc[-1]
    
    # Verificar regras
    rules_check = check_rules(latest_data)
    
    # Imprimir resultados
    print(f"\nAnálise para {ticker} em {latest_data.name.date()}:")
    print("-" * 30)
    # Mostra colunas relevantes para debug
    cols_to_show = ['close', 'WWMA_200', 'stoch_k_80_3', 'obtr', 'wad']
    print(df_with_indicators[cols_to_show].tail())
    
    print("\nVerificação das Regras:")
    for rule, result in rules_check.items():
        status = "SIM [✓]" if result else "NÃO [X]"
        print(f"- {rule:<30}: {status}")

if __name__ == "__main__":
    main()