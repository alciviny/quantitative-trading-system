# Achados do Grid Search Refinado — Energy

## 1. Energy filtra períodos de alto retorno
- O alpha_top é sempre maior que o alpha_geral, confirmando que o sinal de energy seleciona períodos de retorno acima da média.
- Isso valida o uso do energy como filtro de alpha, mesmo quando AUC e F1 são modestos.

## 2. Trade-off seletividade vs frequência
- Quantis altos (0.9): menos sinais, alpha_top maior.
- Quantis baixos (0.7): mais sinais, alpha_top menor.
- Quantil 0.8 geralmente oferece o melhor equilíbrio entre retorno e frequência de oportunidades.

## 3. Horizonte e janela rolling
- Horizontes maiores (10–20 dias) tendem a melhorar o AUC, mostrando que o energy antecipa movimentos que se consolidam em alguns dias.
- Janelas rolling maiores (42, 63) suavizam o sinal, aumentando robustez, mas podem reduzir sensibilidade a movimentos rápidos.

## 4. Versão combinada (v0.3) é a mais robusta
- Mantém alpha_top elevado e AUC competitivo em todos os cenários, especialmente com janelas intermediárias (21, 42) e quantil 0.8.

## 5. Melhores cenários
- BPAC11.SA, v0.3, quantil 0.8, horizonte 10 ou 20, janela 21 ou 42: alpha_top elevado, AUC acima de 0.55, boa frequência de sinais.
- ELET6.SA e AXIA6.SA seguem padrão semelhante, mas com alpha_top absoluto menor (característica do ativo).

## 6. Próximos passos
- Usar o script `energy_grid_search_refinado.py` para novas explorações.
- Rodar cenários específicos com `energy_validation_metrics.py` para ajustes finos.
- Explorar visualmente os resultados com notebook Python para heatmaps e gráficos comparativos.

---

*Documento gerado automaticamente a partir do grid search refinado do sinal de energy.*
