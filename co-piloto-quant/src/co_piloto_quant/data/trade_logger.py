import sqlite3
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
import numpy as np

# Tenta importar a configuração, com fallback seguro
try:
    from co_piloto_quant.config import DATA_DIR
except (ModuleNotFoundError, ImportError):
    # Fallback para o caso de o script ser executado de forma isolada
    DATA_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "co_piloto_quant" / "data"

# Não cria diretórios automaticamente aqui
DB_PATH = DATA_DIR / "trades.db"

class CustomJSONEncoder(json.JSONEncoder):
    """
    Encoder JSON customizado para lidar com tipos de dados do NumPy e Pandas
    que não são serializáveis por padrão (ex: np.nan, np.int64).
    """
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if pd.isna(obj):
            return None
        return super(CustomJSONEncoder, self).default(obj)

class TradeLogger:
    """
    Responsável por gravar um registro histórico de todas as operações enviadas,
    incluindo um snapshot dos dados que levaram à decisão (auditoria/caixa preta).
    """
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self):
        """Cria o banco de dados e a tabela de trades se não existirem."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP NOT NULL,
                        ticket INTEGER NOT NULL,
                        symbol TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume REAL NOT NULL,
                        stop_loss REAL,
                        take_profit REAL,
                        reason_data TEXT
                    )
                """)
                conn.commit()
        except sqlite3.Error as e:
            print(f"❌ [TradeLogger] Erro ao inicializar o banco de dados: {e}")
            # Em um cenário real, poderia enviar uma notificação crítica aqui.
            raise

    def log_trade(
        self,
        ticket: int,
        symbol: str,
        operation: str,
        price: float,
        volume: float,
        stop_loss: float,
        reason_data: pd.Series,
        take_profit: float = None
    ):
        """
        Grava um único registro de trade no banco de dados.

        Args:
            ticket (int): ID da ordem retornado pelo MT5.
            symbol (str): Símbolo do ativo.
            operation (str): 'BUY' ou 'SELL'.
            price (float): Preço de execução.
            volume (float): Volume da operação (lotes).
            stop_loss (float): Preço do Stop Loss.
            reason_data (pd.Series): Snapshot dos indicadores no momento da decisão.
            take_profit (float, optional): Preço do Take Profit. Defaults to None.
        """
        timestamp = datetime.now()
        
        # Converte a Série do Pandas para um dicionário e depois para JSON
        try:
            # Filtra apenas os dados relevantes para evitar poluir o JSON
            relevant_data = reason_data.filter(like='_').to_dict() # Pega colunas com '_' (indicadores)
            relevant_data['SIGNAL'] = reason_data.get('SIGNAL', 'UNKNOWN')
            
            reason_json = json.dumps(relevant_data, cls=CustomJSONEncoder, indent=4)
        except Exception as e:
            reason_json = json.dumps({"error": f"Failed to serialize reason_data: {e}"})

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO trades (timestamp, ticket, symbol, operation, price, volume, stop_loss, take_profit, reason_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (timestamp, ticket, symbol, operation, price, volume, stop_loss, take_profit, reason_json))
                conn.commit()
            print(f"📝 Trade Logged: Ticket {ticket} para {symbol}")

        except sqlite3.Error as e:
            # Requisito: Não travar o robô. Apenas logar o erro.
            error_msg = f"Falha ao gravar trade (Ticket: {ticket}) no DB: {e}"
            print(f"❌ [TradeLogger] {error_msg}")
            # Idealmente, notificar via Telegram
            try:
                from co_piloto_quant.utils.telegram_sender import send_message
                send_message(error_msg, type='ERROR')
            except ImportError:
                pass # Ignora se o sender não estiver disponível

# Exemplo de uso
if __name__ == '__main__':
    print("--- Testando TradeLogger ---")
    
    # Cria um logger para um DB de teste em memória
    test_logger = TradeLogger(db_path=Path(":memory:"))
    
    # Cria dados de exemplo (pd.Series como o robô teria)
    dados_exemplo = pd.Series({
        'Hurst_Z': -0.4,
        'Entropy_Z': 0.8,
        'BB_Upper_200_0.45': 110000,
        'BB_Lower_200_0.45': 109000,
        'Stoch_k_20_3_3': 25.5,
        'SIGNAL': 'BUY',
        'close': 109500, # Dado não relacionado a indicador
        'open': 109400
    })

    print("\n1. Logando um trade de compra...")
    test_logger.log_trade(
        ticket=12345,
        symbol='WINZ25',
        operation='BUY',
        price=109500.0,
        volume=0.01,
        stop_loss=109000.0,
        reason_data=dados_exemplo
    )

    # Verifica se foi gravado
    with sqlite3.connect(":memory:") as conn:
       conn.row_factory = sqlite3.Row
       cursor = conn.cursor()
       cursor.execute("SELECT * FROM trades")
       row = cursor.fetchone()
       if row:
           print("\n✅ SUCESSO! Dados recuperados do banco de dados de teste:")
           print(f"   - Ticket: {row['ticket']}")
           print(f"   - Símbolo: {row['symbol']}")
           
           # Carrega e exibe o JSON de 'reason_data'
           reason_dict = json.loads(row['reason_data'])
           print(f"   - Indicadores (do JSON):")
           for key, value in reason_dict.items():
               print(f"     - {key}: {value}")
       else:
           print("\n❌ FALHA! Nenhum dado encontrado no banco de dados de teste.")

    print("\n--- Teste Concluído ---")
