# Auditoria dos Scripts de Energy

## Sumário
- Introdução
- Teoria e Fundamentação Matemática
- Objetivos e Hipóteses
- Explicação Técnica dos Scripts
- Estágio Atual e Perspectivas
- Referências

---

## Introdução
Esta auditoria tem como objetivo analisar, explicar e documentar de forma profissional todos os scripts relacionados ao conceito de "energy" desenvolvidos no projeto. O foco é garantir rastreabilidade, clareza metodológica e robustez científica, além de registrar o estágio atual da pesquisa e suas perspectivas.

## Teoria e Fundamentação Matemática
O conceito de "energia estrutural" aqui desenvolvido busca quantificar, a partir de fatores de mercado, momentos de compressão, instabilidade e dispersão estrutural em séries financeiras. A inspiração vem de analogias com física estatística e sistemas dinâmicos, onde energia pode ser associada à tensão acumulada antes de transições de regime.

### Componentes Matemáticos:
- **Compressão Estrutural:**
  - $\text{compressao}_t = \frac{1}{\sigma_{\text{expansao}, t-w:t}}$
  - Onde $\sigma$ é o desvio padrão rolling do fator de expansão em janela $w$.
- **Instabilidade Recente:**
  - $\text{instabilidade}_t = \text{média rolling das mudanças de regime}$
- **Energia Estrutural v0.1:**
  - $\text{energia}_t = z(\text{compressao}_t) + z(\text{instabilidade}_t)$
  - Onde $z(\cdot)$ é o z-score rolling robusto.
- **Entropia dos Fatores:**
  - $\text{entropy}_t = \text{média dos desvios padrão rolling dos fatores}$
- **Distância ao Centroide do Regime:**
  - $\text{energia\_v2}_t = \sqrt{\sum_{i} (f_{i,t} - \mu_{i,\text{regime}})^2}$
- **Energia Combinada v0.3:**
  - $\text{energia\_v3}_t = \text{energia}_t + \text{energia\_v2}_t + \text{entropy}_t$

A hipótese central é que altos valores dessas energias precedem ou acompanham transições de regime de mercado, podendo ter poder preditivo sobre retornos futuros (alpha) ou mudanças de regime.

## Objetivos e Hipóteses
- **Objetivo:**
  - Investigar se métricas de energia estrutural extraídas de fatores de mercado antecipam ou reagem a transições de regime e se possuem poder preditivo sobre retornos futuros.
- **Hipóteses:**
  1. Altos valores de energia precedem transições de regime.
  2. Energia estrutural tem correlação positiva com retornos futuros (alpha).
  3. Energia pode ser usada como sinal de alerta para mudanças de regime.

## Explicação Técnica dos Scripts
(Conteúdo será detalhado nos próximos arquivos)

## Estágio Atual e Perspectivas
- Scripts implementam diferentes versões de energia estrutural (v0.1, v0.2, v0.3).
- Testes mostram que, em alguns ativos, altos valores de energia estão associados a maior probabilidade de transição de regime e, em certos casos, a retornos futuros diferenciados.
- O poder preditivo é modesto, mas consistente em alguns cenários, sugerindo que a abordagem é promissora, porém ainda requer refinamento e validação mais ampla.

## Referências
- Documentação interna do projeto
- Artigos sobre física estatística aplicada a finanças
- Papers sobre regime switching e detecção de transições em séries temporais
