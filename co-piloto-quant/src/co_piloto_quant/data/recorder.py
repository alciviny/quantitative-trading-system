import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional

# Importamos a conexão do seu módulo de banco existente
from co_piloto_quant.data.database import DB_PATH



def record_signal(ticker: str, 
                  signal_type: str, 
                  price: float, 
                  indicators: Dict[str, any]):
    """
    Grava um novo sinal no banco de dados.
    Deve ser chamado pelo scanner quando um trade é identificado.
    """
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # Data de hoje (ou do último candle processado)
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Extrai os indicadores do dicionário de regras
        hurst = indicators.get('Hurst_Score', 0)
        entropy = indicators.get('Entropy_Score', 0)
        cycle = indicators.get('Hilbert_Ciclo', 'Neutro')
        period = indicators.get('Hilbert_Periodo', 0)
        hl = indicators.get('Half_Life_Val', 0)
        r2 = indicators.get('OU_R2', 0)
        
        try:
            cursor.execute('''
                INSERT INTO signals_history (
                    date, ticker, signal_type, price_at_signal,
                    hurst_val, entropy_val, hilbert_cycle, hilbert_period, half_life, ou_r2
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (today, ticker, signal_type, price, hurst, entropy, cycle, period, hl, r2))
            
            conn.commit()
            # print(f"Sinal gravado: {ticker} | {signal_type}") # Descomente para debug
        except Exception as e:
            print(f"Erro ao gravar sinal para {ticker}: {e}")

def update_outcomes():
    """
    Rotina de Manutenção:
    Percorre sinais antigos que ainda não têm resultado e verifica o preço futuro.
    Isso rotula os dados automaticamente (Auto-Labeling).
    """
    with sqlite3.connect(DB_PATH) as conn:
        # 1. Carregar sinais pendentes (que têm mais de 5 dias e sem resultado)
        query = """
        SELECT id, date, ticker, price_at_signal 
        FROM signals_history 
        WHERE price_5d_later IS NULL
        """
        pending_signals = pd.read_sql(query, conn)
        
        if pending_signals.empty:
            print("Nenhum sinal pendente para atualização de resultado.")
            return

        print(f"Atualizando resultados para {len(pending_signals)} sinais antigos...")
        
        cursor = conn.cursor()
        
        for _, row in pending_signals.iterrows():
            signal_date = datetime.strptime(row['date'], "%Y-%m-%d")
            target_date = signal_date + timedelta(days=5)
            target_date_str = target_date.strftime("%Y-%m-%d")
            
            # Busca o preço no futuro (na tabela ohlcv existente)
            # Nota: Assume que você tem a tabela 'ohlcv' populada pelo data_fetching.py
            price_query = """
            SELECT close FROM ohlcv 
            WHERE ticker = ? AND date >= ? 
            ORDER BY date ASC LIMIT 1
            """
            future_price_row = cursor.execute(price_query, (row['ticker'], target_date_str)).fetchone()
            
            if future_price_row:
                future_price = future_price_row[0]
                pct_change = (future_price - row['price_at_signal']) / row['price_at_signal']
                
                # Define sucesso (Ex: > 1% de lucro para compra, < -1% para venda)
                # Simplificação: Aqui assume que todos são COMPRA. 
                # Se tiver VENDA, precisa inverter a lógica do pct_change.
                is_success = pct_change > 0.01 
                
                cursor.execute('''
                    UPDATE signals_history
                    SET price_5d_later = ?, result_5d_pct = ?, success_5d = ?
                    WHERE id = ?
                ''', (future_price, pct_change, is_success, row['id']))
                
        conn.commit()
    print("Atualização de resultados concluída.")
