import pandas as pd
import pytest
from unittest.mock import MagicMock

# Importar as funções que vamos testar
from co_piloto_quant.data import fetch_data
from co_piloto_quant.analysis import calculate_indicators, check_rules

# --- Fixtures (Dados de Teste) ---

@pytest.fixture
def sample_dataframe():
    """Cria um DataFrame do Pandas de exemplo para os testes de análise."""
    data = {
        'timestamp': pd.to_datetime(['2023-01-01', '2023-01-02', '2023-01-03']),
        'open': [98, 100, 102],
        'high': [101, 103, 105],
        'low': [97, 99, 101],
        'close': [100, 102, 104],
        'volume': [1000, 1100, 1200]
    }
    return pd.DataFrame(data)

@pytest.fixture
def mock_yq_ticker(mocker):
    """Cria um mock para a classe yahooquery.Ticker."""
    # Cria um mock da classe Ticker
    mock_ticker_class = MagicMock()

    # Configura o mock para retornar um DataFrame quando o método history() for chamado
    mock_instance = mock_ticker_class.return_value
    
    # Dados de exemplo que o mock vai retornar
    sample_data = {
        'date': pd.to_datetime(['2023-01-01']),
        'open': [100],
        'close': [102]
    }
    mock_df = pd.DataFrame(sample_data).set_index('date')
    mock_instance.history.return_value = mock_df
    
    # Substitui o yq.Ticker real pelo nosso mock
    mocker.patch('co_piloto_quant.data.yq.Ticker', mock_ticker_class)
    
    return mock_ticker_class

@pytest.fixture
def mock_yq_ticker_empty(mocker):
    """Cria um mock para o Ticker que retorna um DataFrame vazio."""
    mock_ticker_class = MagicMock()
    mock_instance = mock_ticker_class.return_value
    mock_instance.history.return_value = pd.DataFrame() # Retorno vazio
    mocker.patch('co_piloto_quant.data.yq.Ticker', mock_ticker_class)
    return mock_ticker_class

# --- Testes para data.py ---

def test_fetch_data_success(mock_yq_ticker):
    """Testa se fetch_data processa um retorno bem-sucedido da API."""
    dados = fetch_data("PETR4.SA")
    
    # Verifica se o Ticker foi chamado com o ativo correto
    mock_yq_ticker.assert_called_once_with("PETR4.SA")
    
    # Verifica se o DataFrame não está vazio
    assert not dados.empty
    # Verifica se a coluna de data foi renomeada corretamente
    assert 'timestamp' in dados.columns
    assert 'date' not in dados.columns
    # Verifica se o conteúdo está correto
    assert dados['open'].iloc[0] == 100

def test_fetch_data_no_data(mock_yq_ticker_empty):
    """Testa se fetch_data lida com um retorno de dados vazio."""
    dados = fetch_data("ATIVO_QUALQUER")
    assert dados.empty

def test_fetch_data_exception(mocker):
    """Testa o tratamento de exceção em fetch_data."""
    # Configura o mock para levantar uma exceção
    mocker.patch('co_piloto_quant.data.yq.Ticker', side_effect=Exception("Erro de API"))
    
    dados = fetch_data("ATIVO_COM_ERRO")
    assert dados.empty

# --- Testes para analysis.py ---

def test_calculate_indicators(sample_dataframe):
    """Testa se os indicadores são adicionados ao DataFrame."""
    df_com_indicadores = calculate_indicators(sample_dataframe)
    
    # Verifica se as colunas dos indicadores foram adicionadas
    assert 'EMA_20' in df_com_indicadores.columns
    assert 'EMA_50' in df_com_indicadores.columns
    assert 'RSI_14' in df_com_indicadores.columns

def test_check_rules():
    """Testa a lógica da função check_rules com dados de exemplo."""
    # Cenário 1: Todas as regras são verdadeiras
    latest_data_true = pd.Series({
        'close': 110,
        'open': 108,
        'EMA_20': 105,
        'EMA_50': 100,
        'RSI_14': 60
    })
    regras_true = check_rules(latest_data_true)
    assert regras_true["Preço > MME 20"] is True
    assert regras_true["MME 20 > MME 50"] is True
    assert regras_true["RSI > 50"] is True
    assert regras_true["Candle Positivo"] is True

    # Cenário 2: Todas as regras são falsas
    latest_data_false = pd.Series({
        'close': 95,
        'open': 97,
        'EMA_20': 100,
        'EMA_50': 105,
        'RSI_14': 40
    })
    regras_false = check_rules(latest_data_false)
    assert regras_false["Preço > MME 20"] is False
    assert regras_false["MME 20 > MME 50"] is False
    assert regras_false["RSI > 50"] is False
    assert regras_false["Candle Positivo"] is False
