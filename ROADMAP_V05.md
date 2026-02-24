# Roadmap para Evolução do Sinal de Energia — v0.5

## Objetivo Geral
Desenvolver uma versão v0.5 do sinal de energia com maior poder preditivo para trocas de regime e geração de alpha, utilizando novas features, abordagens não-lineares e validação robusta.

---

## Tarefas e Etapas

### 1. Exploração e Engenharia de Features
- [ ] Adicionar fatores de preço: momentum, volatilidade, drawdown, reversão, volume.
- [ ] Incluir indicadores de fluxo, ordem ou dados alternativos (se disponíveis).
- [ ] Testar features de janela adaptativa (rolling window dinâmica baseada em volatilidade).

### 2. Abordagens Não-Lineares e Machine Learning
- [ ] Montar dataset tabular com energias (v0.1–v0.4), fatores originais e novas features.
- [ ] Treinar modelos ML simples (Random Forest, Gradient Boosting, SVM) para prever trocas de regime ou retornos extremos.
- [ ] Testar combinações não-lineares entre fatores e energias (produto, razão, log, exponencial).
- [ ] Usar seleção automática de features (feature importance, SHAP, etc).

### 3. Target Alternativo
- [ ] Testar targets alternativos: grandes movimentos, drawdowns, clusters de volatilidade, retornos extremos.

### 4. Validação Cruzada e Tuning
- [ ] Implementar validação cruzada temporal.
- [ ] Ajustar quantis, horizontes e parâmetros de rolling para cada ativo.

### 5. Análise Qualitativa
- [ ] Gerar gráficos dos sinais versus regimes e retornos.
- [ ] Investigar casos de acerto/erro para entender limitações do modelo atual.

### 6. Comparação e Relatórios
- [ ] Comparar desempenho do modelo ML com as energias puras.
- [ ] Analisar feature importance para descobrir o que realmente agrega valor.
- [ ] Documentar aprendizados e próximos passos.

---

## Observações
- O pipeline atual já está pronto para ingestão de novas features e validação rápida.
- Cada etapa pode ser implementada incrementalmente e validada com o script de métricas já existente.

---

**Próximo passo sugerido:**
Escolher uma ou mais tarefas acima para iniciar a implementação e validação.
