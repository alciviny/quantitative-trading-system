# Documentação Profissional — Energy Engine

## 1. Visão Geral
O Energy Engine é um pipeline modular para análise quantitativa de regimes de mercado, focado em indicadores de energia e suas variações. Ele permite calcular múltiplas versões de energia, gerar relatórios comparativos, gráficos e métricas preditivas para diversos ativos.

## 2. Estrutura de Dados e Outputs
- **Arquivos CSV:** Para cada ativo, é gerado um arquivo `structural_factors_<ATIVO>.csv` contendo todas as features calculadas.
- **Gráficos Comparativos:** São salvos gráficos (PNG) mostrando as curvas das energias v0.1 a v0.4 para cada ativo.
- **Relatórios de Métricas:** Scripts como `energy_validation_metrics.py` e `energy_comparative_report.py` produzem métricas preditivas e comparações quantitativas entre as versões.
- **Logs Detalhados:** O pipeline imprime logs sobre preenchimento de NaNs, cálculo das energias e métricas preditivas.

## 3. Features Calculadas
- `energia_estrutural`: Combinação de compressão e instabilidade do mercado.
- `energia_v2`: Distância euclidiana dos fatores para o centróide do regime.
- `energia_v3`: Soma das energias anteriores e entropia dos fatores.
- `energia_v4`: Combinação robusta e não-linear dos z-scores das energias e entropia.
- `fatores_entropy`: Entropia dos fatores principais.
- Outras: compressão, instabilidade, regime, mudança de regime, etc.

## 4. Parâmetros Utilizados
- `window_zscore_robusto`: 60
- `window_v4`: 21
- Outras janelas: 21 (compressão, instabilidade, entropia, v2, v3)
- Proteção contra explosão de z-score: MAD mínimo de 1e-3

## 5. Fluxo do Pipeline
1. Leitura dos fatores estruturais de cada ativo.
2. Cálculo das features e energias (v0.1 a v0.4).
3. Preenchimento automático de NaNs nos insumos.
4. Proteção contra explosão de valores nos z-scores.
5. Geração de gráficos comparativos e relatórios de métricas.
6. Exportação dos resultados para CSV e PNG.

## 6. Interpretação dos Outputs
- **Gráficos:** Cada linha representa uma versão de energia. Oscilações maiores no v0.4 indicam sensibilidade a variações não-lineares e robustas.
- **Métricas preditivas:** Permitem comparar o poder de antecipação de cada versão de energia em relação a mudanças de regime.
- **Logs:** Facilitam o diagnóstico de problemas com dados faltantes ou insumos inadequados.

## 7. Limitações e Cuidados
- O pipeline depende da qualidade dos insumos (fatores, regimes, etc).
- Em trechos constantes, o v0.4 é neutro, evitando sinais falsos.
- Recomenda-se revisar os outputs antes de usar para previsões reais.

## 8. Como Rodar o Pipeline
```bash
python -m energy_engine.main --step batch --factors_dir <dir_fatores> --output_dir <dir_resultados>
```
- Os resultados serão salvos nas pastas especificadas.

## 9. Como Expandir
- Para adicionar novos ativos, basta incluir o CSV correspondente na pasta de fatores.
- Novas versões de energia podem ser implementadas em `features/energy.py`.
- Novas métricas podem ser adicionadas nos scripts de relatório.

## 10. Referências e Contato
- Para dúvidas, sugestões ou colaboração, consulte o README principal ou entre em contato com o responsável pelo projeto.

---

**Este documento deve ser atualizado a cada nova versão ou experimento relevante.**