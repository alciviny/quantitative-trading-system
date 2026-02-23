# Teoria, Hipóteses e Estágio Atual: Fatores Estruturais

## Fundamentação Teórica
O script parte da hipótese de que séries financeiras podem ser decompostas em fatores latentes que capturam propriedades fundamentais do ativo. A identificação de regimes via GMM sobre PCA dos fatores suavizados permite detectar mudanças estruturais não supervisionadas.

## Hipóteses Centrais
1. Os fatores extraídos (persistência, estrutura, expansão, liquidez) são estatisticamente relevantes e capturam propriedades latentes do ativo.
2. Os regimes classificados apresentam diferenças claras em retorno, volatilidade e assinatura dos fatores.
3. Mudanças de regime podem ser antecipadas pela dinâmica dos fatores.

## Detalhes Matemáticos
- Rolling z-score para normalização temporal.
- PCA para redução de dimensionalidade e extração de fatores latentes.
- GMM para classificação não supervisionada de regimes.
- Filtros de persistência para robustez dos labels.
- Validação estatística: retorno, volatilidade, skew, kurtosis, duração, assinatura média, matriz de transição.

## Estágio Atual
- Pipeline robusto, validado em múltiplos ativos.
- Regimes apresentam diferenças estatísticas claras.
- Próximos passos: expandir para mais ativos, ajustar parâmetros, integrar com métricas de energy.

## Perspectiva Profissional
O framework é sólido, alinhado com melhores práticas quantitativas e pronto para integração com análises preditivas e estratégias quantitativas mais avançadas.
