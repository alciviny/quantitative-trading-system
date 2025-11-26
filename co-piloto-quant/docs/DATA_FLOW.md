# Arquitetura e Fluxo de Dados - Co-Piloto Quant

Este documento detalha a arquitetura do fluxo de dados do sistema, desde a aquisição dos dados brutos até o seu processamento e utilização nos indicadores técnicos e estratégias de análise.

## Visão Geral

O fluxo de dados foi projetado para ser modular e desacoplado, seguindo as seguintes etapas:

1.  **Coleta**: Dados de mercado (OHLCV) são baixados de uma fonte externa (Yahoo Finance).
2.  **Armazenamento**: Os dados brutos são persistidos em um banco de dados local (SQLite) para acesso rápido e histórico, evitando downloads repetidos.
3.  **Processamento**: Os dados são carregados em memória e enriquecidos com uma bateria de indicadores técnicos.
4.  **Análise**: As estratégias e scanners utilizam os dados processados para identificar sinais e gerar alertas.

```mermaid
graph TD
    A[Fontes Externas <br> (Yahoo Finance)] -->|yfinance| B(1. Coleta <br> `data_fetching.py`);
    B -->|pandas DataFrame| C(2. Armazenamento <br> `database.py`);
    C -->|INSERT OR REPLACE| D{Banco de Dados <br> `market_data.db`};
    D -->|SELECT *| E(3. Processamento <br> `data_processing.py`);
    E -->|Aplica Indicadores| F(4. Análise <br> `analysis.py`, `run_scanner.py`);
    subgraph "Módulos de Indicadores (`/indicators`)"
        G[bollinger_bands.py]
        H[ifr_tpm.py]
        I[...]
    end
    E --> G;
    E --> H;
    E --> I;
```

---

## Etapa 1: Coleta de Dados (`data_fetching.py`)

-   **Responsabilidade**: Baixar dados históricos de mercado.
-   **Fonte**: A biblioteca `yfinance` é utilizada para se conectar à API do Yahoo Finance.
-   **Funções Chave**:
    -   `fetch_data(ticker, ...)`: Busca dados para um único ativo.
    -   `fetch_batch_data(tickers, ...)`: Otimizado para buscar dados de múltiplos ativos em paralelo.
-   **Processo**:
    1.  Recebe uma lista de tickers (ex: `['PETR4.SA', 'VALE3.SA']`).
    2.  Usa `yfinance.download()` para obter os dados de Open, High, Low, Close e Volume.
    3.  Imediatamente após o download, os dados são passados para a camada de armazenamento para serem salvos.

---

## Etapa 2: Armazenamento (`database.py`)

-   **Responsabilidade**: Persistir e fornecer acesso aos dados brutos de mercado.
-   **Tecnologia**: SQLite, um banco de dados leve e baseado em arquivo. O banco de dados fica em `src/co_piloto_quant/data/market_data.db`.
-   **Estrutura (Schema)**:
    1.  **`assets`**: Tabela que armazena informações sobre os ativos (ex: ticker, nome da empresa).
    2.  **`ohlcv`**: Tabela principal que armazena os dados de preço e volume, com uma chave composta `(asset_id, date)` para garantir que não haja entradas duplicadas.
-   **Funções Chave**:
    -   `init_db()`: Cria o arquivo de banco de dados e as tabelas, caso não existam.
    -   `save_price_data(ticker, data)`: Salva os dados de um ativo. Utiliza o comando `INSERT OR REPLACE INTO`, que atualiza um registro existente se ele já estiver no banco (baseado na chave primária), ou insere um novo caso contrário. Isso torna o processo de atualização de dados eficiente e idempotente.
    -   `load_price_data(ticker)`: Carrega todos os dados históricos de um ativo do banco de dados para um `pandas.DataFrame`.

---

## Etapa 3: Processamento e Indicadores (`data_processing.py`)

-   **Responsabilidade**: Atuar como uma "calculadora". Este módulo orquestra a aplicação de indicadores técnicos sobre os dados brutos.
-   **Processo**:
    1.  Recebe um DataFrame com dados OHLCV.
    2.  Itera sobre o dicionário `INDICATOR_MAPPING`. Este dicionário é o coração do processamento, pois mapeia um nome de indicador para a função que o calcula e seus respectivos parâmetros.
    3.  Para cada item no mapa, ele chama a função do indicador correspondente (localizada na pasta `/indicators`).
    4.  O resultado (uma `pd.Series` ou `pd.DataFrame`) é juntado ao DataFrame original.
-   **Arquitetura**: Este módulo é "puro". Ele não tem estado e não se conecta a fontes externas. Sua única função é receber dados, calcular e devolver os dados enriquecidos. Isso o torna extremamente rápido e fácil de testar.

---

## Etapa 4: Orquestração (`scripts/`)

-   **Responsabilidade**: Unir todas as camadas anteriores para executar tarefas de ponta a ponta.
-   **Exemplos**:
    -   `run_pipeline.py`: Um script simples que demonstra o fluxo completo: ele busca os dados de um ativo (`fetch_data`), o que implicitamente os salva no banco, e em seguida os processa (`process_data`) para calcular todos os indicadores mapeados.
    -   `run_scanner.py`: Carrega os dados já salvos no banco (`load_price_data`), calcula os indicadores (`process_data`) e, em seguida, aplica a lógica de `analysis.py` para encontrar ativos que correspondam a critérios específicos (sinais de compra/venda).
    -   `teste_infra.py`: Um "smoke test" que verifica se todas as peças do quebra-cabeça estão funcionando corretamente: conexão com o banco, download de dados, e cálculo de todos os indicadores.

Este design garante que cada parte do sistema tenha uma responsabilidade única, facilitando a manutenção, o teste e a adição de novas funcionalidades (como novos indicadores ou novas estratégias).
