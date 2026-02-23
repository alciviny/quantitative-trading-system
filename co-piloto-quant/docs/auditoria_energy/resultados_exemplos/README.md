# Exemplos de Gráficos e Relatórios

Esta pasta contém exemplos de visualizações e relatórios gerados a partir dos scripts de energy. Use estes exemplos para apresentações, validação visual e documentação dos resultados.

## 1. Dispersão: Energia Estrutural x Alpha Futuro
- **Script:** `plot_energy_vs_alpha.py`
- **Descrição:** Mostra a relação entre energia estrutural (v0.3) e o retorno futuro de 10 períodos. Útil para avaliar se altos valores de energia estão associados a maiores retornos.
- **Exemplo:** ![scatter_energy_alpha](scatter_energy_alpha.png)

## 2. Evolução Temporal da Energia Estrutural
- **Script:** `analyze_structural_energy.py`
- **Descrição:** Exibe a evolução da energia estrutural ao longo do tempo, destacando períodos de alta energia e possíveis transições de regime.
- **Exemplo:** ![evolucao_energia](evolucao_energia.png)

## 3. Histogramas: Distribuição da Energia
- **Script:** `analyze_structural_energy_batch.py`
- **Descrição:** Mostra a distribuição dos valores de energia estrutural para diferentes ativos, permitindo identificar padrões e outliers.
- **Exemplo:** ![histograma_energia](histograma_energia.png)

## 4. Relatório de Ranking: Poder Preditivo
- **Script:** `energy_vs_alpha_ranking.py`
- **Descrição:** Ranking dos ativos com maior diferencial preditivo de alpha por versão de energia.
- **Exemplo:** Veja arquivo `ranking_exemplo.csv`.

---

**Como gerar:**
- Execute os scripts correspondentes para salvar os gráficos em PNG nesta pasta.
- Inclua sempre uma breve descrição do objetivo de cada gráfico.

**Sugestão:**
- Atualize os exemplos conforme novos experimentos.
- Use estes materiais em relatórios técnicos e apresentações.
