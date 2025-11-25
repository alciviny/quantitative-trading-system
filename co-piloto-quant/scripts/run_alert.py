
import os
import requests
import logging
from datetime import datetime

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Funções Stubs (Substitutos para simulação) ---
# Substitua estas com as importações reais do seu projeto.
# Exemplo: from co_piloto_quant.utils import get_top_50_tickers
# Exemplo: from co_piloto_quant.data.data_fetching import fetch_batch_data
# Exemplo: from co_piloto_quant.analysis import check_rules

def get_top_50_tickers():
    """Retorna os 50 principais tickers da B3."""
    logging.info("Obtendo os 50 principais tickers...")
    # Esta é uma lista de exemplo. A função real buscaria isso dinamicamente.
    tickers = [f'TICKER{i}.SA' for i in range(1, 51)]
    logging.info(f"Encontrados {len(tickers)} tickers.")
    return tickers

def fetch_batch_data(tickers):
    """
    Busca dados de mercado para uma lista de tickers.
    Retorna um dicionário onde as chaves são os tickers e os valores são DataFrames.
    """
    logging.info(f"Buscando dados para {len(tickers)} tickers...")
    # Simula o download de dados. A função real usaria yfinance ou outra API.
    # Em caso de sucesso, o valor seria um pandas.DataFrame.
    # Para este exemplo, usamos um dicionário simples.
    data = {ticker: {"Close": [100, 102, 105], "Volume": [1000, 1200, 1100]} for ticker in tickers}
    return data

def check_rules(df, ticker):
    """
    Verifica as regras de trading para um determinado ativo.
    Retorna um dicionário com os resultados das regras.
    """
    logging.info(f"Verificando regras para {ticker}...")
    # Simula a lógica de análise. A função real aplicaria os indicadores.
    # Exemplo de retorno: {'Sinal_Compra': True, 'Sinal_Venda': False}
    # Para simular, vamos alternar os sinais.
    import random
    sinal_compra = random.choice([True, False])
    sinal_venda = not sinal_compra if sinal_compra else random.choice([True, False])
    
    # Garante que não haja compra e venda ao mesmo tempo
    if sinal_compra and sinal_venda:
        sinal_venda = False

    return {'Sinal_Compra': sinal_compra, 'Sinal_Venda': sinal_venda}

# --- Fim das Funções Stubs ---


def send_telegram_message(message):
    """Envia uma mensagem para um chat do Telegram."""
    token = os.getenv('TELEGRAM_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        logging.error("As variáveis de ambiente TELEGRAM_TOKEN e TELEGRAM_CHAT_ID não foram configuradas.")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }

    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        logging.info("Mensagem enviada com sucesso para o Telegram!")
    except requests.exceptions.RequestException as e:
        logging.error(f"Falha ao enviar mensagem para o Telegram: {e}")

def main():
    """Função principal para executar o scanner de alertas."""
    logging.info("Iniciando o scanner de oportunidades.")
    
    try:
        tickers = get_top_50_tickers()
    except Exception as e:
        logging.error(f"Falha ao obter a lista de tickers: {e}")
        return

    all_data = fetch_batch_data(tickers)
    
    opportunities = {
        'compra': [],
        'venda': []
    }

    for ticker in tickers:
        try:
            logging.info(f"Processando ativo: {ticker}")
            df = all_data.get(ticker)
            if df is None:
                logging.warning(f"Não foram encontrados dados para o ticker {ticker}.")
                continue

            results = check_rules(df, ticker)
            
            if results.get('Sinal_Compra'):
                opportunities['compra'].append(ticker)
                logging.info(f"Oportunidade de COMPRA encontrada para: {ticker}")

            if results.get('Sinal_Venda'):
                opportunities['venda'].append(ticker)
                logging.info(f"Oportunidade de VENDA encontrada para: {ticker}")

        except Exception as e:
            logging.error(f"Erro ao processar o ticker {ticker}: {e}", exc_info=True)
            # Continua para o próximo ticker
            continue
    
    if not opportunities['compra'] and not opportunities['venda']:
        logging.info("Nenhuma oportunidade encontrada na varredura de hoje.")
        # Se você quiser receber uma notificação mesmo quando nada for encontrado,
        # desmonte as linhas abaixo.
        # title = f"📢 Scanner Co-Piloto Quant ({datetime.now().strftime('%d/%m/%Y')})"
        # message = f"{title}\n\nNenhuma oportunidade de compra ou venda foi encontrada na varredura de hoje."
        # send_telegram_message(message)
        return

    # Formata a mensagem
    title = f"🚨 *Scanner Co-Piloto Quant* 🚨\n_{datetime.now().strftime('%d/%m/%Y %H:%M:%S')}_"
    
    message_parts = [title]

    if opportunities['compra']:
        compra_str = "\n\n✅ *Oportunidades de Compra:*\n" + "\n".join([f"`{ticker}`" for ticker in opportunities['compra']])
        message_parts.append(compra_str)

    if opportunities['venda']:
        venda_str = "\n\n❌ *Oportunidades de Venda:*\n" + "\n".join([f"`{ticker}`" for ticker in opportunities['venda']])
        message_parts.append(venda_str)
        
    final_message = "".join(message_parts)

    send_telegram_message(final_message)
    logging.info("Scanner finalizado.")


if __name__ == "__main__":
    main()
