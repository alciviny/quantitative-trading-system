# Energy Engine

Este módulo é dedicado a estudos, features e pipelines relacionados a energy.

Estrutura modular inspirada no regime_engine para facilitar expansão e manutenção.

## Exemplo de execução

Execute um pipeline diretamente pelo terminal:

```bash
python -m energy_engine.pipeline.analyze_structural_energy --ticker PETR4.SA
```

Ou rode o batch para múltiplos ativos:

```bash
python -m energy_engine.pipeline.analyze_structural_energy_batch --factors_dir <diretorio_fatores> --results_dir <diretorio_resultados>
```

Todos os scripts da pasta `pipeline/` aceitam argumentos de linha de comando e usam funções modulares de `features/` e `utils/`.
