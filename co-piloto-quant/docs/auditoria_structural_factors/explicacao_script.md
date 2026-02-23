# Explicação Técnica: analyze_structural_factors.py

## 1. Carregamento e Pré-processamento
- **Função:** Carrega features do ativo e prepara variáveis auxiliares.
- **Como faz:** Lê arquivo Parquet, calcula rolling z-score para normalização.
- **Por que assim:** Normalização rolling evita lookahead bias e garante robustez temporal.

## 2. Fatores Estruturais
- **Persistência:** PCA sobre Hurst e Half-life normalizados.
- **Estrutura:** Média dos z-scores invertidos de entropia e choppiness.
- **Expansão:** PCA sobre volatilidade, amplitude relativa e vol of vol.
- **Liquidez:** Z-score do proxy de Amihud.

## 3. Campo Estrutural Contínuo
- **Função:** Calcula magnitude, direção, velocidade e aceleração do vetor de fatores.
- **Como faz:** Rolling z-score, PCA e derivadas.
- **Por que assim:** Permite análise dinâmica e identificação de mudanças abruptas.

## 4. Pipeline Rolling (Scaler → PCA → GMM)
- **Função:** Classifica regimes de mercado ao longo do tempo.
- **Como faz:** Para cada janela, aplica scaler, PCA e GMM, atribuindo labels de regime.
- **Por que assim:** Rolling window garante adaptação a mudanças estruturais e evita overfitting.

## 5. Filtros de Persistência
- **Função:** Suaviza labels de regime para evitar ruído.
- **Como faz:** Majority filter e filtro de persistência mínima.
- **Por que assim:** Garante que regimes tenham duração mínima e reduz falsos positivos.

## 6. Validação Estatística
- **Função:** Valida se regimes são estatisticamente distintos.
- **Como faz:** Calcula retorno, volatilidade, duração, skew, kurtosis, assinatura média e matriz de transição por regime.
- **Por que assim:** Confirma se a classificação tem significado econômico e estatístico.

## 7. Visualização
- **Função:** Plota fatores suavizados ao longo do tempo.
- **Como faz:** Gráficos de linha para cada fator.
- **Por que assim:** Permite inspeção visual da dinâmica dos fatores e regimes.
