# Boas Práticas — Energy Engine

## Estrutura Modular

- **features/**: Coloque aqui funções e módulos para criação de novas features (variáveis, indicadores, transformações).
- **filters/**: Filtros, seletores ou funções para filtrar dados, regimes ou sinais.
- **models/**: Modelos de machine learning, estatísticos ou regras customizadas.
- **pipeline/**: Scripts principais de execução, orquestração e integração dos módulos. Use esta pasta para pipelines completos, experimentos e análises.
- **utils/**: Funções utilitárias, helpers, normalização, manipulação de dados, etc.
- **tests/**: Testes unitários e de integração para cada módulo.

## Recomendações

- Cada módulo deve ser pequeno, focado e reutilizável.
- Use imports relativos para facilitar manutenção.
- Documente funções e classes com docstrings.
- Prefira notebooks ou scripts na pasta pipeline para experimentos e análises finais.
- Sempre que criar um novo script, explique no início o objetivo e dependências.
- Testes devem ficar em `tests/` e cobrir o máximo possível dos módulos.
- Se criar um novo tipo de objeto (feature, filtro, modelo), crie um arquivo separado para ele.

## Fluxo Sugerido

1. Crie/adicione novas features em `features/`.
2. Implemente filtros em `filters/`.
3. Modele e treine modelos em `models/`.
4. Orquestre tudo em scripts de `pipeline/`.
5. Use utilitários de `utils/` para tarefas comuns.
6. Teste tudo em `tests/`.

---

> Este documento serve como referência para você e para o próprio Copilot no futuro. Siga este padrão para manter o projeto organizado, escalável e fácil de entender!
