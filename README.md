# Co-Piloto Quantitativo

Sistema de análise quantitativa para mercado financeiro com backend Python e frontend React.

## 🚀 Quick Start

### Backend (API)
```bash
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO"
& "co-piloto-quant\vbt_env\Scripts\Activate.ps1"
python api_backend.py
```

Acesse: http://localhost:8001

### Frontend
```bash
cd co-piloto-frontend
npm install
npm run dev
```

Acesse: http://localhost:3001

## 📁 Estrutura

```
├── api_backend.py          # API FastAPI principal
├── api_example.py          # API de exemplo
├── co-piloto-quant/        # Backend Python
│   ├── scripts/            # Scripts de análise
│   ├── src/                # Código fonte
│   ├── data/               # Dados (não versionado)
│   └── models/             # Modelos ML (não versionado)
└── co-piloto-frontend/     # Frontend React
    ├── src/
    └── package.json
```

## 📊 Features

- ✅ Análise quantitativa de ativos B3
- ✅ Indicadores técnicos e físicos de mercado
- ✅ Dashboard interativo React
- ✅ API REST com FastAPI
- ✅ Backtesting e análise de estratégias

## 🔧 Tecnologias

**Backend:**
- Python 3.9+
- FastAPI
- Pandas + PyArrow
- vectorbt

**Frontend:**
- React 18 + TypeScript
- Vite
- Tailwind CSS
- TanStack Query

## 📝 Documentação

Para documentação detalhada, consulte:
- [Arquitetura do Sistema](ARQUITETURA_SISTEMA.md) (se existir)
- [Backend README](co-piloto-quant/README.md)
- [Frontend README](co-piloto-frontend/README.md)

## ⚠️ Nota sobre Dados

Os arquivos de dados (`.parquet`, `.csv`, `.db`) e modelos (`.joblib`) não são versionados no Git devido ao tamanho. Eles são gerados localmente através dos scripts em `co-piloto-quant/scripts/`.

## 📄 Licença

Este é um projeto pessoal para análise quantitativa.
