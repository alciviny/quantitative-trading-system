# Roadmap de Melhoria do Sinal de Energy

## 1. Ajuste de Parâmetros
- Testar diferentes quantis (ex: top 10%, 30%, 50%) para o filtro de energy.
- Avaliar diferentes horizontes de retorno futuro (ex: 5, 10, 20 dias).
- Explorar thresholds dinâmicos (z-score, média móvel).

## 2. Engenharia de Features
- Criar novas combinações não-lineares dos fatores (multiplicações, interações, PCA).
- Incluir volatilidade, volume e fatores de mercado amplos como features auxiliares.
- Testar sinais derivados: derivadas, aceleração, reversão do energy.

## 3. Validação Cruzada e Robustez
- Separar períodos para treino/teste (walk-forward, cross-validation temporal).
- Testar o sinal em outros ativos e setores.
- Avaliar o comportamento do sinal em diferentes regimes de mercado (bull, bear, lateral).

## 4. Modelos Supervisionados
- Usar regressão logística, decision tree ou random forest combinando energy com outros sinais para prever regime ou alpha futuro.
- Avaliar a importância relativa do energy como feature.

## 5. Backtest Estratégico
- Simular estratégias reais usando energy como filtro para entradas/saídas.
- Ponderar exposição ao risco conforme o nível de energy.
- Medir métricas de portfólio: Sharpe, drawdown, turnover, etc.

## 6. Análise de Erros
- Investigar casos de falso positivo/negativo do sinal.
- Visualizar exemplos de acertos/erros junto com preço e regime.

## 7. Explicabilidade e Interpretação
- Analisar feature importance em modelos supervisionados.
- Usar SHAP/LIME para explicações locais das decisões do modelo.

---

**Próximos Passos:**
1. Rodar o pipeline variando quantil e horizonte (automatizar grid search).
2. Testar energy como feature em modelos supervisionados simples.
3. Fazer backtest de estratégias usando energy como filtro.
4. Documentar aprendizados e ajustar o pipeline conforme os resultados.

---

Este roadmap deve ser revisitado e atualizado conforme avançarmos nos experimentos e aprendizados.
