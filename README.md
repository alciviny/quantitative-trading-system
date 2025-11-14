# quantitative-trading-system
# quantitative-trading-system 📈
 
## 🎯 Objetivo do Projeto
![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-yellow.svg)
 
Este projeto é um **Sistema de Suporte à Decisão** para traders e investidores.
Um sistema de suporte à decisão para traders e investidores, projetado para fornecer uma análise técnica objetiva e baseada em regras.
 
é uma ferramenta para ser executada manualmente *antes* de uma operação. Ela serve como um checklist objetivo, baseado em regras de análise técnica pré-definidas, para confirmar uma tese de investimento e ajudar a remover o viés emocional do processo de tomada de decisão.
## 🎯 Objetivo
 
## 📂 Estrutura de Pastas
Este projeto serve como um **checklist objetivo** para ser executado manualmente *antes* de uma operação. O objetivo é confirmar uma tese de investimento através de regras de análise técnica pré-definidas, ajudando a remover o viés emocional do processo de tomada de decisão.
 
A organização do projeto foi pensada para ser escalável e fácil de manter. Usamos a analogia de uma "Caixa de Ferramentas".
## ✨ Features
 
   `pyproject.toml`:
    -   **O que é:** O "RG" ou a "Etiqueta de Identificação" do projeto.
    -   **Conteúdo:** Define o nome do projeto, a versão, e, mais importante, a lista de todas as dependências (bibliotecas) que ele precisa para funcionar, como `pandas` e `yahooquery`.
- **Busca de Dados Históricos**: Coleta dados de mercado (OHLCV) para qualquer ativo listado no Yahoo Finance.
- **Cálculo de Indicadores**: Calcula automaticamente indicadores técnicos essenciais, como Médias Móveis e IFR (RSI).
- **Análise de Regras**: Executa um conjunto de regras de trading configuráveis sobre o último candle.
- **Dashboard Simples**: Apresenta um resumo claro e direto no terminal, indicando quais regras foram ativadas.
 
   `src/co_piloto_quant/`:
    -   **O que é:** A "Caixa de Ferramentas" em si. Contém o código-fonte principal e reutilizável.
    -   **Conteúdo:**
        -   `data.py`: A ferramenta responsável por se conectar à internet e buscar os dados dos ativos.
        -   `analysis.py`: A ferramenta que sabe como calcular indicadores (Médias Móveis, RSI) e aplicar as regras da estratégia.
## 🚀 Getting Started
 
   `scripts/`:
    -   **O que é:** O "Manual de Instruções" ou o local do "Operador da Ferramenta".
    -   **Conteúdo:**
        -   `run_dashboard.py`: O script que você executa. Ele importa as ferramentas de `src/` e as utiliza para gerar o dashboard de confirmação para um ativo específico.
Siga estas instruções para obter uma cópia local do projeto e executá-la.
 
   `tests/`:
    -   **O que é:** O "Departamento de Controle de Qualidade".
    -   **Conteúdo:** Aqui ficarão os testes automatizados que garantem que cada ferramenta da nossa caixa (`data.py`, `analysis.py`) funciona exatamente como esperado, evitando que futuras alterações quebrem o código.
### Pré-requisitos
 
- [Python 3.10+](https://www.python.org/downloads/)
- [Git](https://git-scm.com/downloads/)
 
### Instalação

1.  **Clone o repositório:**
    ```sh
    git clone https://github.com/alciviny/quantitative-trading-system.git
    cd quantitative-trading-system
    ```

2.  **Crie um ambiente virtual e ative-o:**
    ```sh
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Instale as dependências do projeto:**
    O arquivo `pyproject.toml` gerencia as dependências. Instale-as com o pip:
    ```sh
    pip install .
    ```

## Usage

Para executar a análise para o ativo padrão, execute o script principal a partir do diretório raiz do projeto:

```sh
python -m scripts.run_dashboard
```

O resultado será um dashboard exibido no seu terminal:

```
========================================
--- Dashboard de Confirmação: PETR4.SA (1d) ---
========================================
[ ] Preço > MM21      : SIM [✓]
[ ] MM21 > MM50       : NÃO [X]
[ ] MM50 > MM200      : NÃO [X]
[ ] IFR > 50          : SIM [✓]
------------------------------------------
RESUMO: 2 de 4 regras ativas.
------------------------------------------
```

### Configuração

Para analisar outros ativos ou timeframes, edite as constantes no topo do arquivo `scripts/run_dashboard.py`:

```python
# scripts/run_dashboard.py

ATIVO = "VALE3.SA"  # Mude o ticker do ativo aqui
TIMEFRAME = "1wk"   # Mude o timeframe (1d, 1wk, 1mo)
```

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.

