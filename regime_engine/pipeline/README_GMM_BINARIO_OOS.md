# Pipeline GMM Binário OOS

Este pipeline executa a validação out-of-sample (OOS) dos regimes binários usando o modelo GMM, aproveitando o engine robusto do projeto.

## Arquivos principais
- `run_gmm_binario_oos.py`: Executa o GMM binário em dados OOS, gera estatísticas por regime e exporta resultados.
- `main.py`: Pipeline walk-forward completo, pode ser adaptado para diferentes cenários.
- `gmm.py`: Implementação do modelo RegimeGMM.

## Como usar
1. Ajuste o caminho do arquivo de dados no script `run_gmm_binario_oos.py` conforme necessário.
2. Execute o script para gerar estatísticas e exportar os resultados OOS.
3. Os resultados OOS serão salvos em `resultados_regimes_binario_oos.csv` na pasta pipeline.

## Observações
- O script está organizado para facilitar reuso e adaptação.
- Parâmetros do GMM, janela de treino/teste e fatores podem ser ajustados conforme o contexto.
- O pipeline pode ser expandido para outros tipos de regime ou validações.

---
Organização feita para centralizar e simplificar a validação dos regimes binários OOS dentro do regime_engine/pipeline.
