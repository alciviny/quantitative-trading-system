# Arquitetura e Fluxo de Dados - Co-Piloto Quant

Este documento detalha a arquitetura do fluxo de dados do sistema, desde a aquisição dos dados brutos até a sua visualização interativa.

## Visão Geral

O fluxo de dados foi projetado para ser modular e desacoplado, seguindo as seguintes etapas:

1.  **Coleta**: Dados de mercado (OHLCV) são baixados de uma fonte externa (Yahoo Finance).
2.  **Armazenamento**: Os dados brutos são persistidos em um banco de dados local (SQLite) para acesso rápido e histórico.
3.  **Processamento**: Os dados são carregados, e os indicadores técnicos são calculados.
4.  **Análise (Scanner)**: As regras são aplicadas, e um `score` é gerado para cada ativo.
5.  **Visualização**: Um dashboard interativo (Streamlit) apresenta os resultados para análise.

```mermaid
graph TD
    subgraph "Setup & Execução"
        A[Fontes Externas <br> (Yahoo Finance)] -->|yfinance| B(1. Coleta <br> `data_fetching.py`);
        B -->|pandas DataFrame| C(2. Armazenamento <br> `database.py`);
        C -->|INSERT OR REPLACE| D{Banco de Dados <br> `market_data.db`};
    end

    subgraph "Análise Diária"
        E(run_scanner.py) -->|Carrega dados| D;
        E -->|Calcula indicadores| F(3. Processamento <br> `data_processing.py`);
        F -->|Aplica regras| G(4. Análise <br> `analysis.py`);
        G -->|Gera score| H[scanner_results.csv];
    end
    
    subgraph "Visualização Interativa"
        I(run_streamlit.py) -->|Lê resultados| H;
        I -->|Exibe dashboard| J((Dashboard Web));
    end

    subgraph "Módulos de Indicadores (`/indicators`)"
        K[bollinger_bands.py]
        L[ifr_tpm.py]
        M[...]
    end

    F --> K;
    F --> L;
    F --> M;
```

---

## Etapa 1: Coleta de Dados (`data_fetching.py`)

-   **Responsabilidade**: Baixar dados históricos de mercado.
-   **Fonte**: Biblioteca `yfinance` para se conectar ao Yahoo Finance.
-   **Processo**: O script `run_scanner.py` utiliza `data_fetching.py` para buscar dados de todos os ativos listados no `config.py` e os salva no banco de dados.

---

## Etapa 2: Armazenamento (`database.py`)

-   **Responsabilidade**: Persistir e fornecer acesso aos dados brutos de mercado.
-   **Tecnologia**: SQLite (`market_data.db`).
-   **Funções Chave**:
    -   `save_price_data`: Usa `INSERT OR REPLACE` para salvar ou atualizar os dados de um ativo de forma eficiente.
    -   `load_price_data`: Carrega os dados de um ativo do banco para a memória.

---

## Etapa 3: Processamento e Indicadores (`data_processing.py`)

-   **Responsabilidade**: "Calculadora" de indicadores técnicos.
-   **Processo**: Recebe um DataFrame com dados OHLCV e aplica uma série de funções de indicadores (localizadas na pasta `/indicators`) para enriquecer os dados. É um módulo puro, sem conexões externas.

---

## Etapa 4: Análise e Orquestração (`run_scanner.py`)

-   **Responsabilidade**: Unir todas as camadas para executar a análise de mercado.
-   **Processo**:
    1.  Orquestra a coleta de dados para todos os ativos.
    2.  Para cada ativo, carrega os dados do banco.
    3.  Usa `data_processing.py` para calcular os indicadores.
    4.  Usa `analysis.py` para aplicar as regras de negócio e calcular o `score`.
    5.  Salva uma tabela resumo dos resultados no arquivo `scanner_results.csv`.

---

## Etapa 5: Visualização Interativa (`run_streamlit.py`)

-   **Responsabilidade**: Fornecer uma interface de usuário rica e interativa para a análise dos resultados.
-   **Tecnologia**: Streamlit.
-   **Processo**:
    1.  Iniciado com o comando `streamlit run run_streamlit.py`.
    2.  Lê o arquivo `scanner_results.csv` para exibir a tabela de classificação dos ativos.
    3.  Permite que o usuário filtre os ativos (por `score`, `Tendencia Macro`, etc.).
    4.  Ao selecionar um ativo, o script carrega os dados completos do banco de dados, recalcula os indicadores em tempo real e exibe gráficos detalhados para uma análise visual aprofundada.

Este design garante um fluxo de trabalho claro: `run_scanner.py` faz o trabalho pesado de processamento em lote, e o dashboard Streamlit foca em fornecer uma experiência de análise de dados rápida e interativa.