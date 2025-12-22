# Workflow de Atualização e Validação

Esta é a sequência de comandos para atualizar os dados de mercado, preparar os datasets e executar a validação walk-forward.

1.  **Atualizar dados de mercado:**
    ```shell
    python scripts/update_market_data.py
    ```
    *(Este comando baixa os dados mais recentes do mercado.)*

2.  **Preparar dados para Machine Learning:**
    ```shell
    python scripts/build_ml_dataset.py
    ```
    *(Este comando processa os dados brutos e cria o dataset para os testes e modelos.)*

3.  **Executar a Validação Walk-Forward:**
    ```shell
    python scripts/walk_forward_validation.py
    ```
    *(Este comando executa o backtest da estratégia usando a metodologia walk-forward, agora com as correções de alinhamento e colunas duplicadas.)*
