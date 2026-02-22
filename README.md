
# Quantitative Trading System

Sistema completo de análise quantitativa para o mercado financeiro, com backend Python (FastAPI) e frontend React.

---

## 🚀 Início Rápido

### Backend (API)
```bash
cd co-piloto-quant
# Ative o ambiente virtual, se necessário
# Exemplo para Windows:
vbt_env\Scripts\Activate.ps1
python api_backend.py
```
Acesse: [http://localhost:8001](http://localhost:8001)

### Frontend
```bash
cd co-piloto-frontend
npm install
npm run dev
```
Acesse: [http://localhost:3001](http://localhost:3001)

---

## 📁 Estrutura do Projeto

```
quantitative-trading-system/
├── co-piloto-quant/      # Backend Python (scripts, src/, models/)
├── co-piloto-frontend/   # Frontend React (src/, configs)
├── docs/                 # Documentação detalhada
├── README.md             # Este arquivo
└── .gitignore
```

---

## 📚 Documentação

- [Fluxo de Dados e Diretórios](docs/DATA_FLOW.md)
- [Arquitetura do Sistema](docs/ARQUITETURA_SISTEMA.md)
- [Guia do Pipeline](docs/README_PIPELINE.md)
- [Frontend: Como Iniciar](co-piloto-frontend/COMO_INICIAR.md)
- [Resolução de Problemas](co-piloto-frontend/PROBLEMAS_RESOLVIDOS.md)

---

## 📊 Funcionalidades

- Análise quantitativa de ativos B3
- Indicadores técnicos e físicos
- Dashboard interativo (React)
- API REST (FastAPI)
- Backtesting e análise de estratégias

---

## 🔧 Tecnologias

**Backend:** Python 3.9+, FastAPI, Pandas, PyArrow, vectorbt  
**Frontend:** React 18, TypeScript, Vite, Tailwind CSS, TanStack Query

---

## ⚠️ Nota sobre Dados

Arquivos de dados (`.parquet`, `.csv`, `.db`) e modelos (`.joblib`) **não são versionados**. Eles são gerados localmente pelos scripts em `co-piloto-quant/scripts/`.  
Todos os dados devem ser salvos apenas em `src/co_piloto_quant/data/` conforme o padrão documentado.

---

## 📄 Licença

Projeto pessoal para fins de estudo e pesquisa em trading quantitativo.

---

## 📝 Documentação

Para documentação detalhada, consulte:
- [Arquitetura do Sistema](ARQUITETURA_SISTEMA.md) (se existir)
- [Backend README](co-piloto-quant/README.md)
- [Frontend README](co-piloto-frontend/README.md)

## ⚠️ Nota sobre Dados

Os arquivos de dados (`.parquet`, `.csv`, `.db`) e modelos (`.joblib`) não são versionados no Git devido ao tamanho. Eles são gerados localmente através dos scripts em `co-piloto-quant/scripts/`.

## 📄 Licença

Este é um projeto pessoal para análise quantitativa.
