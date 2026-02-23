# Análise dos Resultados do Grid Search — Sinal de Energy

## 1. Energy realmente filtra períodos de alto retorno

Os resultados mostram que o alpha_top (retorno médio futuro nos períodos de energy elevado) é sempre maior que o alpha_geral (retorno médio em todos os períodos), independentemente do ativo, versão, quantil ou horizonte. Isso comprova que o sinal de energy não é ruído: mesmo que as métricas de classificação (AUC, F1) sejam modestas, o energy funciona como um filtro eficiente para selecionar períodos de maior potencial de alpha.

---

## 2. Trade-off entre seletividade e frequência

- **Quantis altos (0.9):** O filtro é mais seletivo, gerando menos sinais, mas o alpha_top é maior. Ideal para estratégias que buscam retornos mais altos por operação, mesmo que menos frequentes.
- **Quantis baixos (0.7):** O filtro é menos seletivo, gerando mais sinais, mas o alpha_top diminui. Útil para estratégias mais ativas, aceitando retornos menores por evento.
- **Quantil 0.8:** Apresenta o melhor equilíbrio entre retorno e frequência de sinais, sendo uma escolha robusta para a maioria dos cenários.

Esse comportamento é clássico em filtros quantitativos: quanto mais seletivo, maior o retorno esperado por evento, mas menor a frequência de oportunidades.

---

## 3. Horizonte importa pouco, mas AUC melhora com horizonte maior

O AUC (poder discriminativo para prever trocas de regime) melhora levemente para horizontes mais longos (10–20 dias), especialmente para BPAC11.SA e para a versão combinada (v0.3). Isso indica que o energy antecipa movimentos que levam alguns dias para se consolidar, funcionando melhor como filtro de tendência do que como trigger de regime diário.

---

## 4. Versão combinada (v0.3) é mais robusta

A versão combinada (v0.3) mantém o alpha_top elevado e o AUC estável em diferentes horizontes e ativos. Isso mostra que combinar múltiplos fatores estruturais na construção do energy traz estabilidade e robustez ao sinal, tornando-o mais confiável para uso prático.

---

## 5. Conclusão Estratégica

- **Energy é um filtro de alpha robusto:** Seleciona períodos de maior retorno, mesmo sem ser um previsor perfeito de regime.
- **Ajuste de quantil/horizonte permite calibrar o trade-off entre retorno e frequência de sinais.**
- **A versão combinada (v0.3) deve ser priorizada em estratégias reais.**

Esses aprendizados orientam o uso do energy como filtro de oportunidade e sugerem próximos passos para backtests e integração em estratégias quantitativas.

---

*Documento gerado automaticamente a partir do grid search de parâmetros do sinal de energy.*
