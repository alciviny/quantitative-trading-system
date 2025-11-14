# Co-piloto Quantitativo

## 🎯 Objetivo do Projeto

Este projeto é um **Sistema de Suporte à Decisão** para traders e investidores.

é uma ferramenta para ser executada manualmente *antes* de uma operação. Ela serve como um checklist objetivo, baseado em regras de análise técnica pré-definidas, para confirmar uma tese de investimento e ajudar a remover o viés emocional do processo de tomada de decisão.

## 📂 Estrutura de Pastas

A organização do projeto foi pensada para ser escalável e fácil de manter. Usamos a analogia de uma "Caixa de Ferramentas".

-   `pyproject.toml`:
    -   **O que é:** O "RG" ou a "Etiqueta de Identificação" do projeto.
    -   **Conteúdo:** Define o nome do projeto, a versão, e, mais importante, a lista de todas as dependências (bibliotecas) que ele precisa para funcionar, como `pandas` e `yahooquery`.

-   `src/co_piloto_quant/`:
    -   **O que é:** A "Caixa de Ferramentas" em si. Contém o código-fonte principal e reutilizável.
    -   **Conteúdo:**
        -   `data.py`: A ferramenta responsável por se conectar à internet e buscar os dados dos ativos.
        -   `analysis.py`: A ferramenta que sabe como calcular indicadores (Médias Móveis, RSI) e aplicar as regras da estratégia.

-   `scripts/`:
    -   **O que é:** O "Manual de Instruções" ou o local do "Operador da Ferramenta".
    -   **Conteúdo:**
        -   `run_dashboard.py`: O script que você executa. Ele importa as ferramentas de `src/` e as utiliza para gerar o dashboard de confirmação para um ativo específico.

-   `tests/`:
    -   **O que é:** O "Departamento de Controle de Qualidade".
    -   **Conteúdo:** Aqui ficarão os testes automatizados que garantem que cada ferramenta da nossa caixa (`data.py`, `analysis.py`) funciona exatamente como esperado, evitando que futuras alterações quebrem o código.


