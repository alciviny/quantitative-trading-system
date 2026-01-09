# scripts/verify_strategy_rules.py
import pandas as pd
import numpy as np
import os
import sys
from pathlib import Path

# --- Configuração do Path ---
# Adiciona o diretório raiz do projeto ao sys.path para permitir importações de módulos locais.
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from src.co_piloto_quant.config import PROCESSED_DATA_PATH, RESULTS_PATH
from src.co_piloto_quant.strategies.volatile_momentum_professional import VolatileMomentumProfessional

def run_vectorized_backtest(df_signals: pd.DataFrame, initial_capital: float = 100000.0):
    """
    Executa um backtest vetorizado simples baseado nos sinais gerados pela estratégia.
    
    Args:
        df_signals (pd.DataFrame): DataFrame com as colunas SIGNAL, STOP_LOSS, PROFIT_TARGET.
        initial_capital (float): Capital inicial para o backtest.

    Returns:
        pd.Series: Uma série de pandas com as métricas de resultado do backtest.
    """
    print("Iniciando backtest vetorizado...")

    # --- Preparação do DataFrame ---
    # Isola as colunas necessárias para o backtest para maior clareza.
    df = df_signals[['open', 'high', 'low', 'close', 'SIGNAL', 'STOP_LOSS', 'PROFIT_TARGET']].copy()
    
    # --- Lógica de Execução de Trades (Vetorizada) ---
    # Shift(1) para evitar lookahead bias. A decisão é tomada no fechamento do dia D-1 e a ação no dia D.
    df['POSITION'] = df['SIGNAL'].shift(1).replace({'BUY': 1, 'SELL': -1, 'HOLD': 0})
    df['POSITION'] = df['POSITION'].fillna(0) # Garante que não há NaNs no início

    # Garante que não há posições sobrepostas (uma posição por vez)
    # Identifica o início de um novo trade (mudança de 0 para 1 ou -1)
    is_new_trade = (df['POSITION'] != 0) & (df['POSITION'] != df['POSITION'].shift(1))
    
    # Encontra os dias em que estamos em uma posição
    in_position = df['POSITION'].replace(0, np.nan).ffill().fillna(0)
    
    # Zera as posições que não são o início de um novo trade
    df.loc[~is_new_trade, 'POSITION'] = 0

    # Retorno diário do ativo
    df['MARKET_RETURN'] = df['close'].pct_change()

    # --- Simulação de Saídas (Stop Loss e Profit Target) ---
    # Criamos colunas para marcar quando as saídas são atingidas.
    # Inicializamos como False.
    df['HIT_PROFIT_TARGET'] = False
    df['HIT_STOP_LOSS'] = False

    # Itera pelas linhas onde um trade é iniciado para encontrar o ponto de saída.
    # Um loop aqui é mais claro e seguro para a lógica de "qual foi atingido primeiro".
    for i in df[df['POSITION'] != 0].index:
        position = df.loc[i, 'POSITION']
        sl = df.loc[i, 'STOP_LOSS']
        pt = df.loc[i, 'PROFIT_TARGET']
        
        # Procura por saídas nos dias seguintes ao trade.
        future_market = df.loc[i+1:]

        hit_sl = pd.Series(False, index=future_market.index)
        hit_pt = pd.Series(False, index=future_market.index)

        if position == 1: # Posição comprada
            hit_sl = future_market['low'] <= sl
            hit_pt = future_market['high'] >= pt
        elif position == -1: # Posição vendida
            hit_sl = future_market['high'] >= sl
            hit_pt = future_market['low'] <= pt
            
        # Combina os hits e encontra o primeiro dia em que qualquer um deles ocorre.
        any_hit = (hit_sl | hit_pt)
        first_hit_day = any_hit.idxmax() if any_hit.any() else None

        if first_hit_day:
            # Marca o tipo de saída naquele dia
            if hit_sl[first_hit_day]:
                df.loc[first_hit_day, 'HIT_STOP_LOSS'] = True
            if hit_pt[first_hit_day]:
                df.loc[first_hit_day, 'HIT_PROFIT_TARGET'] = True
                
            # Força a zeragem da posição no dia da saída para calcular o retorno corretamente.
            # E zera posições intermediárias até a saída.
            df.loc[i+1:first_hit_day, 'POSITION'] = df.loc[i, 'POSITION'] # Mantém a posição
            df.loc[first_hit_day, 'POSITION'] = -df.loc[i, 'POSITION'] # Marca a saída
    
    # Calcula o retorno da estratégia
    df['STRATEGY_RETURN'] = df['MARKET_RETURN'] * in_position.shift(1) # Retorno baseado na posição do dia anterior
    df['STRATEGY_RETURN'].fillna(0, inplace=True)
    
    # --- Cálculo de Métricas ---
    df['CUM_MARKET_RETURN'] = (1 + df['MARKET_RETURN']).cumprod()
    df['CUM_STRATEGY_RETURN'] = (1 + df['STRATEGY_RETURN']).cumprod()
    
    total_return = df['CUM_STRATEGY_RETURN'].iloc[-1] - 1
    
    # Trades
    trades = df[df['POSITION'] != 0]
    num_trades = len(trades[trades['POSITION'].isin([1, -1])])
    
    # Win Rate
    wins = df['HIT_PROFIT_TARGET'].sum()
    losses = df['HIT_STOP_LOSS'].sum()
    if num_trades == 0:
        win_rate = 0.0
    else:
        # Apenas considera trades que tiveram um fim (SL ou PT)
        win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0

    # Drawdown
    running_max = df['CUM_STRATEGY_RETURN'].cummax()
    drawdown = (df['CUM_STRATEGY_RETURN'] - running_max) / running_max
    max_drawdown = drawdown.min()

    print("Backtest concluído.")

    return pd.Series({
        'Total Return': f"{total_return:.2%}",
        'Max Drawdown': f"{max_drawdown:.2%}",
        'Win Rate': f"{win_rate:.2%}",
        'Number of Trades': num_trades,
        'Wins (Profit Target)': wins,
        'Losses (Stop Loss)': losses
    })

def main():
    """
    Função principal para executar o backtest da estratégia de regras.
    """
    print("="*50)
    print("INICIANDO VERIFICAÇÃO DE ESTRATÉGIA BASEADA EM REGRAS")
    print("="*50)

    # --- 1. Carregar Dados ---
    # O script espera encontrar os dados de exemplo no caminho especificado.
    # Se o arquivo não existir, o script irá parar.
    ticker = 'PETR4_SA'
    # Usa o caminho de dados processados do arquivo de configuração central
    data_path = PROCESSED_DATA_PATH / f"{ticker}.parquet"
    
    if not data_path.exists():
        print(f"ERRO: Arquivo de dados não encontrado em '{data_path}'")
        print("Por favor, garanta que o arquivo Parquet de dados de mercado exista.")
        return

    print(f"Carregando dados para {ticker} de '{data_path}'...")
    df = pd.read_parquet(data_path)
    # Garante que o índice é do tipo Datetime
    df.index = pd.to_datetime(df.index)

    # --- 2. Instanciar a Estratégia ---
    # Instancia a classe da estratégia que queremos testar.
    # Os parâmetros (como períodos de EMA, multiplicadores de ATR) podem ser ajustados aqui.
    print("Instanciando a estratégia 'VolatileMomentumProfessional'...")
    strategy = VolatileMomentumProfessional(
        ema_fast=12,
        ema_slow=26,
        atr_period=14,
        atr_stop_multiplier=2.5,
        atr_profit_multiplier=3.0,
        target_regimes=['BULL_VOLATILE', 'BEAR_VOLATILE'] # Foco apenas em regimes voláteis
    )

    # --- 3. Avaliar a Estratégia ---
    # O método 'evaluate' executa a lógica da estratégia e retorna um DataFrame
    # com as colunas 'SIGNAL', 'STOP_LOSS', e 'PROFIT_TARGET'.
    # Comentário: A lógica de fallback para 'REGIME' será acionada aqui se a coluna não existir no Parquet.
    print("Calculando sinais da estratégia...")
    df_with_signals = strategy.evaluate(df, ticker)
    
    # --- 4. Executar o Backtest ---
    # Passamos o DataFrame com os sinais para a função de backtest.
    backtest_results = run_vectorized_backtest(df_with_signals)

    # --- 5. Apresentar Resultados ---
    print("\n--- RESULTADOS DO BACKTEST ---")
    print(backtest_results)
    print("------------------------------\n")
    
    # Opcional: Salvar os sinais para análise
    output_path = RESULTS_PATH / "verify_strategy_rules_output.csv"
    df_with_signals.to_csv(output_path)
    print(f"DataFrame com sinais salvo para análise em: '{output_path}'")


if __name__ == "__main__":
    main()
