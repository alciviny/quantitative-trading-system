# Documentação da Lógica do Scanner: Tendência Macro e Score

Este documento detalha dois conceitos fundamentais gerados pelo script `run_scanner.py`: a **Tendência Macro** e o **Score**. O objetivo é clarificar como cada um é calculado e qual o seu propósito dentro da estratégia de análise de mercado.

---

## 1. A Tendência Macro

### O Que é?

A "Tendência Macro" é um filtro de alto nível, o primeiro e mais importante critério da nossa análise. Ele nos dá uma resposta binária (sim ou não) para a pergunta: "Este ativo está em uma tendência de longo prazo de alta ou de baixa?".

Operar a favor da tendência macro é um dos princípios mais consagrados do trading. Este filtro nos ajuda a evitar entrar em operações de compra (`long`) quando o "vento" principal do mercado está soprando contra nós.

### Como é Calculada?

A lógica é direta e baseada em um indicador clássico de análise técnica.

1.  **Indicador Utilizado:** Usamos a **Média Móvel de Wilder de 200 períodos (WWMA 200)**. Esta média é calculada na função `calculate_indicators` do arquivo `analysis.py`.

    ```python
    # src/co_piloto_quant/analysis.py
    df['WWMA_200'] = ww_moving_average(df, period=200, column='close')
    ```

2.  **A Regra de Decisão:** A verificação é feita na função `check_rules` (`analysis.py`), que compara o preço de fechamento mais recente (`latest_data['close']`) com o valor atual da `WWMA_200`.

    ```python
    # src/co_piloto_quant/analysis.py
    rules = {
        'Tendencia Macro': latest_data['close'] > latest_data['WWMA_200'],
        # ... outras regras
    }
    ```

    -   Se o **preço de fechamento for MAIOR** que a `WWMA_200`, a regra `Tendencia Macro` retorna `True`, e o scanner a classifica como **"Alta"**.
    -   Se o **preço de fechamento for MENOR ou IGUAL** à `WWMA_200`, a regra retorna `False`, e o scanner a classifica como **"Baixa"**.

### Por que a Média de 200 Períodos?

A média móvel de 200 dias é um padrão da indústria financeira para avaliar a tendência de longo prazo de um ativo. Ela funciona como um forte suporte (se o preço está acima) ou resistência (se o preço está abaixo). É uma forma robusta e confiável de ter um panorama geral da saúde do ativo.

---

## 2. O Score

### O Que é?

O "Score" é uma pontuação quantitativa que mede o quão alinhado um ativo está com a **sua estratégia específica** no exato momento da análise. Ele responde à pergunta: "De todas as minhas regras de trading, quantas estão sendo satisfeitas AGORA?".

É a ferramenta que permite ranquear e comparar diferentes ativos de forma objetiva. Um ativo com Score 5 é, teoricamente, um candidato mais forte para uma operação do que um ativo com Score 2.

### Como é Calculado?

O cálculo é uma soma simples, mas poderosa.

1.  **Verificação das Regras:** A função `check_rules` em `analysis.py` retorna um dicionário Python. As chaves são os nomes das regras e os valores são booleanos: `True` se a regra foi satisfeita, `False` caso contrário.

    Um exemplo de retorno dessa função para um ativo seria:
    ```python
    {
        'Tendencia Macro': True,       # Passou!
        'Sinal Estocastico': True,     # Passou!
        'OBTR - Tendencia': False,     # Falhou.
        'OBTR - Consolidacao': True,   # Passou!
        'WAD - Tendencia': True,       # Passou!
        'WAD - Consolidacao': True     # Passou!
    }
    ```

2.  **A Soma dos "True":** Em Python, o valor booleano `True` se comporta como o número `1` e o `False` como o número `0` em operações matemáticas. O script `run_scanner.py` se aproveita disso para calcular o Score de forma elegante, simplesmente somando os valores do dicionário.

    ```python
    # scripts/run_scanner.py
    rules_check = check_rules(latest_data)
    score = sum(rules_check.values()) 
    # Exemplo: True + True + False + True + True + True = 1 + 1 + 0 + 1 + 1 + 1 = 5
    ```
    No exemplo acima, o `Score` para o ativo seria **5**.

### Como Interpretar o Score?

O Score **não é um sinal de "Comprar" ou "Vender"**. Ele é uma **ferramenta de triagem e priorização**.

-   **Score Alto (ex: 4, 5, 6):** Indica que o ativo está passando na maioria (ou em todos) os seus filtros. Estes são os "candidatos quentes" que merecem sua atenção para uma análise mais detalhada e manual.
-   **Score Baixo (ex: 0, 1, 2):** Indica que o ativo não está alinhado com sua estratégia no momento. Você pode simplesmente ignorá-los e focar nos candidatos de Score alto.

O objetivo do scanner e do Score é filtrar um universo de dezenas ou centenas de ativos para uma pequena lista de 5 a 15 ativos que realmente importam, economizando seu tempo e direcionando seu foco para as oportunidades mais promissoras.
