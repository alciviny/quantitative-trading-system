# Teoria, Hipóteses e Estágio Atual

## Fundamentação Teórica
A abordagem de energia estrutural parte da premissa de que mercados financeiros podem ser modelados como sistemas dinâmicos sujeitos a transições de regime (mudanças abruptas de comportamento). Inspirada em física estatística, a energia estrutural é uma métrica composta que busca capturar:
- Compressão (baixa variabilidade, possível acúmulo de tensão)
- Instabilidade (frequência de mudanças de regime)
- Dispersão/entropia dos fatores (diversidade de comportamentos simultâneos)
- Distância ao centroide do regime (quanto o sistema está "fora do equilíbrio")

A soma ponderada dessas componentes resulta em diferentes versões da métrica de energia (v0.1, v0.2, v0.3), cada uma testando hipóteses específicas sobre o comportamento do mercado.

## Hipóteses Centrais
1. Altos valores de energia estrutural precedem ou acompanham transições de regime de mercado.
2. Energia estrutural elevada está associada a maior probabilidade de retornos futuros diferenciados (alpha).
3. Energia pode ser usada como sinal de alerta para mudanças de regime.

## Detalhes Matemáticos
- Rolling z-score é utilizado para normalizar componentes e evitar viés de escala.
- Entropia é calculada como média dos desvios padrão rolling dos fatores principais.
- Distância ao centroide do regime é uma métrica euclidiana multivariada.
- Métricas preditivas são extraídas por análise de top quantis (ex: top 20% de energia) e comparação com médias gerais.

## Estágio Atual da Pesquisa
- Scripts implementam todas as etapas: cálculo, batch, merge, análise preditiva e visualização.
- Resultados mostram que, para alguns ativos, altos valores de energia estão associados a maior probabilidade de transição de regime e, em certos casos, a retornos futuros diferenciados.
- O poder preditivo é modesto, mas consistente em alguns cenários.
- A abordagem é promissora, mas ainda requer:
  - Testes em mais ativos e períodos
  - Ajuste fino dos parâmetros
  - Validação cruzada e robustez estatística

## Perspectiva Profissional
O framework desenvolvido é inovador e bem fundamentado, com potencial para aplicações em alerta de risco, detecção de regimes e apoio à decisão quantitativa. Recomenda-se continuidade dos testes, documentação rigorosa dos experimentos e publicação dos resultados mais robustos.
