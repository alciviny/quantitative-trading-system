# Documentação: Centralização de Parâmetros e Cálculo de Indicadores

## Visão Geral

Este documento explica o processo de centralização dos parâmetros dos indicadores técnicos no projeto Co-Piloto Quant, detalha como os cálculos são realizados e como a arquitetura garante rastreabilidade, governança e manutenção facilitada.

---

## 1. Centralização dos Parâmetros dos Indicadores

### Objetivo
Padronizar e centralizar todos os parâmetros relevantes dos indicadores técnicos em um único arquivo de configuração (`src/co_piloto_quant/config.py`). Isso garante que qualquer ajuste de janela, período, desvio ou parâmetro de cálculo seja feito em um só lugar, refletindo automaticamente em todo o pipeline.

### Como funciona
- **Arquivo central:** `src/co_piloto_quant/config.py` contém constantes como `BB_PERIOD`, `IFR_PERIOD`, `HURST_WINDOW`, `SYSTEM_DEVIATIONS`, etc.
- **Scripts de features:** Todos os scripts de cálculo de indicadores (`features_pipeline.py`, `data_pipeline.py`, etc) importam esses parâmetros diretamente do config.
- **Exemplo:**
  ```python
  from co_piloto_quant.config import BB_PERIOD, PRICE_BB_DEVIATIONS, IFR_PERIOD, ...
  engine.add_indicator('bollinger_bands', period=BB_PERIOD, std_devs=PRICE_BB_DEVIATIONS)
  ```
- **Benefícios:**
  - Alteração de parâmetros em um só lugar.
  - Rastreabilidade total dos valores usados em cada execução.
  - Padronização entre todos os scripts e etapas do pipeline.

---

## 2. Pipeline de Cálculo dos Indicadores

### Fluxo Resumido
1. **Atualização dos dados:**
   - Script: `update_market_data.py`
   - Baixa e atualiza dados brutos de mercado para todos os ativos do universo.
2. **Processamento e cálculo de features:**
   - Scripts: `data_pipeline.py`, `features_pipeline.py`
   - Carregam os dados processados e aplicam todos os indicadores técnicos, usando os parâmetros centralizados.
   - Indicadores calculados incluem: Bandas de Bollinger, IFR (RSI), WWMA, System TPM, Estocástico, Hurst, Entropia, Volatilidade, Half-life, Ehlers Hilbert, Choppiness, entre outros.
3. **Persistência:**
   - Os dados enriquecidos são salvos em Parquet na pasta `src/co_piloto_quant/data/features/`.

### Exemplo de Indicadores Calculados
| Indicador         | Parâmetro (do config.py)         |
|-------------------|----------------------------------|
| Bandas de Bollinger   | BB_PERIOD, PRICE_BB_DEVIATIONS |
| IFR (RSI)         | IFR_PERIOD                       |
| Hurst             | HURST_WINDOW                     |
| Entropia          | ENTROPY_WINDOW                   |
| System TPM        | SYSTEM_PERIOD, SYSTEM_DEVIATIONS |
| Estocástico       | STOCH_K_PERIOD, STOCH_K_SMOOTH, STOCH_D_SMOOTH |

---

## 3. Governança e Boas Práticas
- **Todos os scripts de features e processamento devem importar parâmetros do config.py.**
- **Nunca hardcode parâmetros de indicadores diretamente nos scripts.**
- **Qualquer ajuste de janela, período ou desvio deve ser feito apenas no config.py.**
- **Os outputs de features são sempre salvos em `src/co_piloto_quant/data/features/` para garantir rastreabilidade.**

---

## 4. Como alterar um parâmetro de indicador
1. Abra o arquivo `src/co_piloto_quant/config.py`.
2. Localize o parâmetro desejado (ex: `BB_PERIOD = 80`).
3. Altere o valor conforme necessário.
4. Rode o pipeline normalmente (`python scripts/full_data_refresh.py`).
5. Todos os cálculos e outputs refletirão o novo valor automaticamente.

---

## 5. Observações sobre os Cálculos
- Todos os cálculos de indicadores são feitos por funções puras, sem efeitos colaterais, garantindo reprodutibilidade.
- O padrão de nomenclatura das colunas segue o modelo `IndicatorNames` para facilitar análise e integração com modelos.
- O pipeline é modular: novos indicadores podem ser adicionados facilmente, bastando incluir o parâmetro no config e registrar a função no `IndicatorEngine`.

---

## 6. Referências
- Para detalhes do fluxo de dados, veja também: `docs/DATA_FLOW.md`
- Para lógica de scanner e score: `docs/scanner_logic.md`
- Para comandos e workflow: `docs/comandos.txt`, `docs/workflow_instrucoes.md`

---

> **Dúvidas ou sugestões?**
> Consulte este documento antes de alterar qualquer parâmetro ou lógica de cálculo. Para mudanças estruturais, alinhe com o time responsável pela arquitetura do projeto.
