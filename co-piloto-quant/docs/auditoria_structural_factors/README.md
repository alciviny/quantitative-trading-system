# Auditoria Profissional: Script analyze_structural_factors.py

## Sumário
- Introdução
- Teoria e Fundamentação Matemática
- Objetivos e Hipóteses
- Explicação Técnica do Script
- Estágio Atual e Perspectivas
- Referências

---

## Introdução
Este documento audita e explica detalhadamente o script `analyze_structural_factors.py`, responsável pela extração, suavização e classificação de fatores estruturais de ativos financeiros. O objetivo é garantir rastreabilidade, clareza metodológica e robustez científica.

## Teoria e Fundamentação Matemática
O script parte do princípio de que o comportamento de ativos pode ser decomposto em fatores latentes (persistência, estrutura, expansão, liquidez), que juntos descrevem regimes de mercado. Utiliza técnicas de normalização, PCA (Análise de Componentes Principais) e GMM (Gaussian Mixture Model) para identificar e classificar regimes.

### Componentes Matemáticos:
- **Persistência:**
  - Calculada via PCA sobre Hurst e Half-life normalizados.
- **Estrutura:**
  - Média dos z-scores de entropia e choppiness (ambos invertidos para alinhar direção).
- **Expansão:**
  - PCA sobre volatilidade, amplitude relativa e volatilidade da volatilidade.
- **Liquidez:**
  - Z-score do proxy de Amihud (impacto de preço sobre volume).
- **Campo Estrutural:**
  - Vetor dos fatores suavizados, magnitude (norma euclidiana), direção (PCA), velocidade e aceleração.
- **Classificação de Regimes:**
  - Pipeline rolling: scaler → PCA → GMM, com filtros de persistência para suavizar labels.

## Objetivos e Hipóteses
- **Objetivo:**
  - Extrair fatores estruturais robustos e identificar regimes de mercado de forma não supervisionada.
- **Hipóteses:**
  1. Os fatores extraídos capturam propriedades latentes relevantes do ativo.
  2. Os regimes classificados apresentam diferenças estatísticas em retorno, volatilidade e assinatura dos fatores.
  3. Mudanças de regime podem ser detectadas antecipadamente via dinâmica dos fatores.

## Explicação Técnica do Script
- Carrega features do ativo.
- Normaliza e transforma variáveis para obter fatores latentes.
- Suaviza fatores com média móvel longa.
- Aplica pipeline rolling (Scaler → PCA → GMM) para classificar regimes ao longo do tempo.
- Aplica filtros de persistência para evitar ruído em labels.
- Salva fatores e regimes suavizados para uso posterior.
- Realiza validação estatística dos regimes (retorno, volatilidade, duração, skew, kurtosis, assinatura média, matriz de transição).
- Plota fatores suavizados ao longo do tempo.

## Estágio Atual e Perspectivas
- O script está maduro, com pipeline robusto e validação estatística embutida.
- Resultados mostram regimes estatisticamente distintos, com diferenças claras em retorno, volatilidade e assinatura dos fatores.
- Perspectiva: expandir para múltiplos ativos, ajustar parâmetros e integrar com métricas de energy para análises preditivas.

## Referências
- Documentação interna do projeto
- Artigos sobre PCA, GMM e regime switching
- Papers sobre fatores latentes em finanças quantitativas
