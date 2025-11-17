# Sistema TPM (Trading Process Model)

Este documento descreve a arquitetura e os componentes do "Sistema TPM", um modelo de análise técnica baseado em Bandas de Bollinger múltiplas e uma média móvel específica para identificar condições de mercado.

## Componentes Principais

### 1. Média Móvel Central (A "Referência")

- **Tipo:** Média Móvel Welles Wilder (WWMA)
- **Período:** 200 dias
- **Objetivo:** Servir como a linha central de referência para todas as bandas e como um indicador da tendência principal do ativo. É a nossa "gravidade" ou o "valor justo" de longo prazo.

### 2. Bandas de Bollinger Múltiplas (As "Zonas de Operação")

As bandas são calculadas a partir da Média Móvel de 200 períodos, cada uma com um desvio padrão diferente para criar "zonas" de probabilidade em torno da média central.

- **Banda 1 (Zona de Ruído):**
  - **Desvio Padrão:** 0.45
  - **Objetivo:** Delimitar a flutuação de preço mais comum e de curto prazo. Movimentos dentro desta banda são considerados "ruído" normal do mercado.

- **Banda 2 (Zona de Alerta):**
  - **Desvio Padrão:** 1.00
  - **Objetivo:** Sinalizar um afastamento inicial e relevante da média. Atingir esta banda pode ser o primeiro sinal de uma oportunidade.

- **Banda 3 (Zona de Confirmação):**
  - **Desvio Padrão:** 1.50
  - **Objetivo:** Indicar que o movimento de preço está ganhando força e se estendendo para além do comportamento normal.

- **Banda 4 (Zona de Exaustão/Extremo):**
  - **Desvio Padrão:** 2.00
  - **Objetivo:** Marcar níveis de sobrecompra ou sobrevenda extremos. Preços que tocam ou ultrapassam esta banda têm alta probabilidade de reversão à média.

## Próximos Passos da Implementação

1.  **Criar a Função da Média Móvel:** Desenvolver uma função reutilizável para calcular a Média Móvel Welles Wilder (WWMA).
2.  **Criar a Função das Bandas Múltiplas:** Desenvolver uma função que receba uma série de dados (como o IFR, Williams %R, etc.), o período da média e a lista de desvios padrão, e retorne a média central e todas as bandas calculadas.
3.  **Integrar com Indicadores:** Aplicar a função das bandas múltiplas sobre os indicadores `On Balance True Range` e `Williams %R`.
4.  **Visualização:** Levar os resultados para o `visualize_indicator.py` para plotar os gráficos e analisar o comportamento.
