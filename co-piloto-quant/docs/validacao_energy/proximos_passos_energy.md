# Próximos Passos — Evolução do Sinal de Energy

## 1. Refinamento Contínuo
- Ajustar quantis, janelas e combinações de fatores para buscar o melhor equilíbrio entre alpha_top e frequência de sinais.
- Explorar diferentes horizontes e ativos para mapear onde o energy é mais seletivo e robusto.
- Iterar com base nos dados de cada grid search, ajustando thresholds e inspirando novas versões do sinal (v0.4, v0.5, ...).

## 2. Combinação com Outros Sinais
- Integrar energy com sinais de momentum, volume, volatilidade relativa e regressões estruturais.
- Testar filtros compostos (ex: energy + momentum) para aumentar robustez e reduzir falsos positivos.
- Usar energy como feature em modelos supervisionados (classificação/regressão) junto com outros sinais.

## 3. Aprendizado Contínuo
- Documentar cada experimento, threshold e insight para construir histórico e facilitar evolução.
- Automatizar grid search, análise de resultados e geração de relatórios para acelerar o ciclo de pesquisa.

## 4. Expansão e Generalização
- Testar o sinal em outros mercados (ações, futuros, moedas) para avaliar generalização.
- Explorar thresholds adaptativos e modelos dinâmicos que ajustam parâmetros conforme o regime de mercado.

---

**Próximos experimentos práticos serão implementados para cada frente acima, com scripts e templates automatizados.**
