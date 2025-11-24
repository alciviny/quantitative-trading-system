# src/co_piloto_quant/analysis.py

import pandas as pd
import pandas_ta as ta
from pathlib import Path
import argparse
from co_piloto_quant.config import PROCESSED_DATA_PATH

# Imports da arquitetura do projeto
from co_piloto_quant.indicators.bollinger_bands import bollinger_bands
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
    Calcula todos os indicadores técnicos focados na estratégia de "Entrada em Compressão".
    """
    # Se o DataFrame não tiver dados suficientes para a maior janela (200), retorne vazio.
    if len(df) < 200:
        print(f"AVISO: Dados insuficientes para calcular indicadores de 200 períodos. O DataFrame tem {len(df)} linhas.")
        return pd.DataFrame()

    # 1. IFR (RSI) com período 120
    df['IFR_120'] = ta.rsi(df['close'], length=120)

    # 2. Bandas de Bollinger com múltiplos desvios padrão (0.75 e 2.0)
    #    Usando a função customizada do projeto que padroniza os nomes das colunas.
    try:
        bb_df = bollinger_bands(df, period=200, std_devs=[0.75, 2.0])
        df = df.join(bb_df)
    except Exception as e:
        print(f"ERRO ao calcular Bandas de Bollinger: {e}")
        return pd.DataFrame()

    # 3. Oscilador: Estocástico Customizado
    stoch_df = calculate_stochastic_custom(df)
    df = df.join(stoch_df)

    # 4. System TPM com OBTR
    obtr_tpm = calculate_system_tpm(df, indicator='obtr')
    df = df.join(obtr_tpm)

    # 5. System TPM com WAD
    wad_tpm = calculate_system_tpm(df, indicator='wad')
    df = df.join(wad_tpm)
    
    return df

def check_rules(latest_data: pd.Series) -> dict:
    """
    Verifica as regras da estratégia "Entrada em Compressão" e retorna um dicionário
    detalhado com todos os passos para depuração.
    """
    # Nomes de colunas padronizados e seguros, gerados pela função customizada
    period = 200
    
    # Bandas estreitas (0.75) para o filtro de compressão
    bb_lower_squeeze_col = f'BB_Lower_{period}_0.75'
    bb_upper_squeeze_col = f'BB_Upper_{period}_0.75'
    
    # Bandas largas (2.0) ficam disponíveis para checagens futuras (ex: "preço caro/barato")
    # bb_lower_wide_col = f'BB_Lower_{period}_2.0'
    # bb_upper_wide_col = f'BB_Upper_{period}_2.0'

    # Nomes das colunas do System TPM
    obtr_middle_col = 'obtr_bb_middle_band'
    wad_middle_col = 'wad_bb_middle_band'
    
    # Nome da coluna do Estocástico
    stoch_k_col = 'stoch_k_80_3'
    
    # --- Verificação de Regras ---
    
    # 1. Filtro de Consolidação
    ifr_consolidado = (latest_data['IFR_120'] >= 45) & (latest_data['IFR_120'] <= 55)
    
    # Preço em compressão (squeeze) usando as bandas de 0.75 desvio padrão
    preco_em_compressao = (latest_data['close'] < latest_data[bb_upper_squeeze_col]) & \
                          (latest_data['close'] > latest_data[bb_lower_squeeze_col])
                          
    filtro_consolidacao = ifr_consolidado & preco_em_compressao

    # 2. Condições de Força
    forca_compradora = (latest_data['obtr'] > latest_data[obtr_middle_col]) or \
                       (latest_data['wad'] > latest_data[wad_middle_col])
    forca_vendedora = (latest_data['obtr'] < latest_data[obtr_middle_col]) or \
                      (latest_data['wad'] < latest_data[wad_middle_col])

    # 3. Condições de Gatilho do Oscilador
    gatilho_compra = latest_data[stoch_k_col] < 40
    gatilho_venda = latest_data[stoch_k_col] > 60

    # 4. Combinação dos sinais
    sinal_compra = filtro_consolidacao & forca_compradora & gatilho_compra
    sinal_venda = filtro_consolidacao & forca_vendedora & gatilho_venda

    return {
        # Sinais Finais
        'Sinal_Compra': bool(sinal_compra),
        'Sinal_Venda': bool(sinal_venda),
        
        # Etapas Intermediárias para Depuração
        'Filtro_Consolidacao': bool(filtro_consolidacao),
        'IFR_Consolidado': bool(ifr_consolidado),
        'Preco_Em_Compressao': bool(preco_em_compressao),
        'Forca_Compradora': bool(forca_compradora),
        'Forca_Vendedora': bool(forca_vendedora),
        'Gatilho_Compra': bool(gatilho_compra),
        'Gatilho_Venda': bool(gatilho_venda),
    }

def main():
    """
    Função principal para rodar a análise de um ticker.
    """
    parser = argparse.ArgumentParser(description="Script de análise de indicadores para um ativo.")
    parser.add_argument('--ticker', type=str, default="PETR4.SA", help='O ticker do ativo a ser analisado (ex: PETR4.SA).')
    args = parser.parse_args()
    ticker = args.ticker

    df = load_processed_data(ticker)
    if df.empty:
        print(f"Não foram encontrados dados para {ticker}.")
        return

    # Usamos .copy() para garantir que não afetamos o dataframe original
    df_with_indicators = calculate_indicators(df.copy())
    
    if df_with_indicators.empty:
        print(f"Cálculo de indicadores falhou para {ticker}. Abortando.")
        return

    latest_data = df_with_indicators.iloc[-1]
    
    rules_check = check_rules(latest_data)
    
    print(f"\nAnálise para {ticker} em {latest_data.name.date()}:")
    print("-" * 30)
    
    # Colunas relevantes para debug, incluindo as novas bandas de bollinger
    cols_to_show = [
        'close', 'IFR_120', 'stoch_k_80_3', 
        f'BB_Lower_200_0.75', f'BB_Upper_200_0.75', 
        f'BB_Lower_200_2.0', f'BB_Upper_200_2.0',
        'obtr', 'wad'
    ]
    # Filtra colunas que realmente existem no dataframe para evitar KeyErrors no print
    cols_to_show_existing = [col for col in cols_to_show if col in df_with_indicators.columns]
    print(df_with_indicators[cols_to_show_existing].tail())
    
    print("\nVerificação das Regras:")
    for rule, result in rules_check.items():
        status = "SIM [✓]" if result else "NÃO [X]"
        print(f"- {rule:<30}: {status}")

if __name__ == "__main__":
    main()