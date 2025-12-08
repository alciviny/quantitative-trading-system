import requests
import os
from co_piloto_quant.config import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

# --- EMOJI MAP PARA TIPOS DE MENSAGEM ---
EMOJI_MAP = {
    'INFO': 'ℹ️',
    'START': '🚀',
    'TRADE': '📈',
    'SELL': '📉',
    'STOP': '🛑',
    'BREAKEVEN': '✅',
    'ERROR': '⚠️',
    'FATAL': '💀',
    'HEARTBEAT': '❤️'
}

def send_message(message: str, type: str = 'INFO', use_markdown: bool = True):
    """
    Envia uma mensagem para o chat configurado no Telegram.

    Args:
        message (str): O conteúdo da mensagem a ser enviada.
        type (str, optional): O tipo de mensagem (ex: 'TRADE', 'ERROR'). 
                              Controla o emoji prefixado. Defaults to 'INFO'.
        use_markdown (bool, optional): Se True, envia a mensagem usando
                                       o parse_mode 'MarkdownV2'. Defaults to True.
    """
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        # Se as credenciais não estiverem configuradas, apenas imprime no console
        # para não quebrar a aplicação principal.
        print(f"TELEGRAM (dry-run) | {type}: {message}")
        return

    emoji = EMOJI_MAP.get(type.upper(), '💬')
    full_message = f"{emoji} **{type.upper()}**\n\n{message}"

    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': full_message,
    }
    if use_markdown:
        payload['parse_mode'] = 'Markdown' # 'Markdown' é mais tolerante que 'MarkdownV2'

    try:
        # Timeout para evitar que a requisição bloqueie o bot indefinidamente
        response = requests.post(api_url, json=payload, timeout=5)
        response.raise_for_status()  # Lança uma exceção para códigos de erro HTTP (4xx ou 5xx)

    except requests.exceptions.RequestException as e:
        # Se houver qualquer erro de rede ou HTTP, o bot não quebra.
        # Apenas um aviso é impresso no console.
        print(f"\n[Telegram Sender ERROR] Falha ao enviar notificação: {e}\n")
    except Exception as e:
        print(f"\n[Telegram Sender ERROR] Ocorreu um erro inesperado: {e}\n")

# Exemplo de como usar (para testes)
if __name__ == '__main__':
    print("--- Testando Módulo de Notificação Telegram ---")
    
    # Simula a ausência de credenciais
    # ORIGINAL_TOKEN, ORIGINAL_CHAT_ID = TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    # TELEGRAM_TOKEN, TELEGRAM_CHAT_ID = "", ""
    # print("\n1. Testando sem credenciais (dry-run):")
    # send_message("Teste de mensagem sem credenciais.", type='INFO')
    # TELEGRAM_TOKEN, TELEGRAM_CHAT_ID = ORIGINAL_TOKEN, ORIGINAL_CHAT_ID

    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        print("\n2. Testando com credenciais (envio real):")
        
        send_message(
            message="Robô iniciado no servidor `PROD-AWS-01`.",
            type='START'
        )

        send_message(
            message="Ordem de COMPRA enviada para `EURUSD`.\n" \
                    "• Preço: `1.07500`\n" \
                    "• Lote: `0.01`\n" \
                    "• SL: `1.07000`",
            type='TRADE'
        )

        send_message(
            "Ocorreu um erro na análise de `WDOZ25`.\n" \
            "Causa: `Index out of bounds`.",
            type='ERROR'
        )
        
        send_message(
            "Bot encontrou um erro fatal e será encerrado.\n" \
            "Exceção: `MT5ConnectionError - Terminal Desconectado`.",
            type='FATAL'
        )
        
        print("\n✅ Testes concluídos. Verifique seu Telegram.")
    else:
        print("\n⚠️  As variáveis TELEGRAM_TOKEN e TELEGRAM_CHAT_ID não estão definidas.")
        print("    Crie um arquivo .env ou exporte as variáveis de ambiente para testar o envio real.")

    print("\n--- Fim dos Testes ---")
