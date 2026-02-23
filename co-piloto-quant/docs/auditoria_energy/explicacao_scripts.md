# Explicação Técnica dos Scripts de Energy

## 1. analyze_structural_energy.py
- **Função:** Calcula e visualiza a energia estrutural v0.1, v0.2 e v0.3 para um ativo específico.
- **Como faz:**
  - Carrega fatores estruturais suavizados.
  - Calcula compressão estrutural (inverso do desvio padrão rolling do fator de expansão).
  - Calcula instabilidade recente (média rolling das mudanças de regime).
  - Aplica z-score rolling robusto para normalização.
  - Soma componentes para obter energia estrutural.
  - Calcula entropia dos fatores e distância ao centroide do regime.
  - Plota resultados e faz diagnóstico da energia antes das transições de regime.
- **Por que assim:**
  - O método busca capturar tensões acumuladas e instabilidades que precedem mudanças de regime, inspirando-se em conceitos de física estatística.

## 2. analyze_structural_energy_batch.py
- **Função:** Executa o cálculo de energia estrutural para vários ativos em lote, salvando métricas preditivas.
- **Como faz:**
  - Percorre todos os arquivos de fatores estruturais.
  - Calcula energia estrutural v0.1, v0.2, v0.3 para cada ativo.
  - Calcula métricas preditivas: energia antes da transição, energia no dia da troca, probabilidade de troca para top 20% de energia.
  - Salva resultados para análise comparativa.
- **Por que assim:**
  - Permite análise estatística robusta e comparação entre ativos, facilitando validação da hipótese.

## 3. energy_comparative_report.py
- **Função:** Gera relatório comparativo das métricas de energia estrutural entre diferentes ativos.
- **Como faz:**
  - Carrega fatores estruturais de múltiplos ativos.
  - Calcula todas as versões de energia e métricas preditivas.
  - Gera tabelas comparativas e gráficos.
- **Por que assim:**
  - Facilita visualização e comparação dos resultados, identificando padrões e outliers.

## 4. energy_vs_alpha_batch.py
- **Função:** Calcula métricas de alpha (retorno futuro) associadas a diferentes versões de energia estrutural para vários ativos.
- **Como faz:**
  - Para cada ativo, calcula energia estrutural e associa com retornos futuros.
  - Mede alpha médio para top 20% de energia e para o universo geral.
  - Salva resultados para análise posterior.
- **Por que assim:**
  - Permite avaliar se energia estrutural tem poder preditivo sobre retornos futuros.

## 5. energy_vs_alpha_ranking.py
- **Função:** Gera ranking dos ativos com maior diferencial preditivo de alpha por versão de energia.
- **Como faz:**
  - Carrega relatório consolidado.
  - Calcula diferencial entre alpha top 20% e alpha geral.
  - Gera ranking e salva em CSV.
- **Por que assim:**
  - Identifica ativos onde a energia estrutural é mais relevante para previsão de alpha.

## 6. merge_energy_factors.py
- **Função:** Faz merge dos arquivos de energia estrutural e fatores estruturais, alinhando datas e retornos futuros.
- **Como faz:**
  - Lê arquivos de energia e fatores.
  - Faz merge por data ou índice.
  - Salva arquivo consolidado.
- **Por que assim:**
  - Garante que análises posteriores tenham datasets completos e alinhados.

## 7. plot_energy_vs_alpha.py
- **Função:** Plota gráfico de dispersão entre energia estrutural e alpha futuro para um ativo.
- **Como faz:**
  - Lê arquivo consolidado.
  - Plota scatter plot energia x retorno futuro.
- **Por que assim:**
  - Visualização rápida da relação entre energia e alpha.

## 8. test_structural_energy_predictiveness.py
- **Função:** Testa empiricamente o poder preditivo da energia estrutural para transições de regime e retornos futuros.
- **Como faz:**
  - Mede energia média no dia da troca de regime e compara com média geral.
  - Calcula probabilidade de troca futura para top 20% de energia.
- **Por que assim:**
  - Valida empiricamente as hipóteses centrais do estudo.
