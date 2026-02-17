# Pipeline Quantitativo Escalável

## Estrutura
- `src/`: código principal do pacote (etl, features, regimes, validação)
- `data/`: dados (raw, processed, features, results)
- `scripts/`: scripts de orquestração e automação
- `requirements.txt` e `pyproject.toml`: dependências
- `.dvcignore`: arquivos ignorados pelo DVC

## Recomendações
- Use DVC para versionar dados e resultados
- Use pytest para testes
- Use Snakemake/Airflow para orquestração
- Use logging estruturado

## Exemplo de uso
```python
from src.etl import load_parquet
from src.features import add_features
from src.regimes import detect_regimes
from src.validation import validate_regimes

df = load_parquet('data/processed/ITUB4_SA.parquet')
df = add_features(df)
df = detect_regimes(df, features=[...], n_states=2)
metrics = validate_regimes(df, stress_periods=[...])
print(metrics)
```
