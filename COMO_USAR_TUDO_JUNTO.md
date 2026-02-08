# 🎯 Guia Completo: Frontend + Backend

## 📋 Índice
1. [Setup Rápido](#setup-rápido)
2. [Com Backend Python](#com-backend-python)
3. [Estrutura Completa](#estrutura-completa)
4. [Troubleshooting](#troubleshooting)

---

## 🚀 Setup Rápido

### Opção 1: Frontend Apenas (com dados simulados)

```bash
# Windows
cd frontend-react
npm install
npm start

# macOS/Linux
cd frontend-react
npm install
npm start
```

O dashboard abrirá em `http://localhost:3000` com dados de exemplo.

---

## 🔧 Com Backend Python

### Passo 1: Instalar FastAPI

```bash
pip install fastapi uvicorn python-multipart aiofiles
```

### Passo 2: Iniciar API

```bash
# Dentro da pasta do projeto
python api_example.py

# Ou com uvicorn diretamente
uvicorn api_example:app --reload --port 8000
```

A API estará disponível em `http://localhost:8000`

### Passo 3: Configurar Frontend

Crie arquivo `.env` em `frontend-react/`:

```
REACT_APP_API_URL=http://localhost:8000/api
```

### Passo 4: Iniciar Frontend

```bash
cd frontend-react
npm install
npm start
```

Agora o frontend conectará com a API do Python!

---

## 📂 Estrutura Completa

```
SSD-SUPORTE QUANTITATIVO/
├── co-piloto-quant/              # Backend quantitativo
│   ├── data/
│   │   └── results/              # CSVs com dados de preços
│   ├── src/                       # Código principal
│   ├── scripts/                   # Scripts de análise
│   └── README.md
│
├── frontend-react/               # Frontend React
│   ├── public/
│   ├── src/
│   │   ├── components/           # Componentes React
│   │   ├── services/             # API e data loaders
│   │   └── App.js                # Componente principal
│   ├── package.json
│   ├── setup.bat/sh              # Scripts de inicialização
│   └── README.md
│
├── api_example.py                # API FastAPI exemplo
├── FRONTEND_INSTALACAO.md        # Guia de instalação
└── COMO_USAR_TUDO_JUNTO.md       # Este arquivo
```

---

## 🎯 Fluxo de Dados Completo

```
┌─────────────────────────────────────────────────────┐
│ Frontend React (http://localhost:3000)              │
│                                                     │
│  ┌───────────────────────────────────────────────┐  │
│  │ App.js                                        │  │
│  │ ├─ StockSelector (escolher ação)             │  │
│  │ ├─ Dashboard                                 │  │
│  │ │  ├─ KPICards (métricas)                   │  │
│  │ │  ├─ PriceChart (gráfico)                  │  │
│  │ │  ├─ MetricsChart (métricas)               │  │
│  │ │  └─ ReturnsAnalysis (retornos)            │  │
│  │ └─ services/api.js (chama API)              │  │
│  └───────────────────────────────────────────────┘  │
└──────────────────┬──────────────────────────────────┘
                   │ HTTP requests
                   ▼
┌─────────────────────────────────────────────────────┐
│ Backend FastAPI (http://localhost:8000)             │
│                                                     │
│  /api/stocks          (lista ações)                │
│  /api/stocks/{}/metrics        (métricas)         │
│  /api/stocks/{}/vwap           (VWAP)             │
│  /api/stocks/{}/returns        (retornos)         │
│  /api/stocks/{}/price-history  (histórico)        │
│  /api/health          (verificação)                │
└──────────────────┬──────────────────────────────────┘
                   │ Read CSV files
                   ▼
┌─────────────────────────────────────────────────────┐
│ Arquivos de Dados (co-piloto-quant/data/results)  │
│                                                     │
│  ABEV3_SA_metrics_5d.csv                          │
│  ABEV3_SA_vwap_lab_global.csv                     │
│  ABEV3_SA_fwd_ret_5d.csv                          │
│  ... (múltiplas ações e horizontes)               │
└─────────────────────────────────────────────────────┘
```

---

## 🎨 Abas Disponíveis no Dashboard

### 📈 Aba Preço
- Gráfico de área com preços dos últimos 30 dias
- Mín/Máx/Preço atual
- Gráfico de volume de negociação

### 📊 Aba Métricas VWAP
- Retorno médio por faixa de preço (Z-score)
- Taxa de acerto por faixa
- Scatter plot: Volatilidade vs Taxa de Acerto
- Resumo estatístico

### 💰 Aba Retornos
- Gráfico combinado: Retorno Médio + Retorno Mediano + Índice Sharpe
- Tabela detalhada por faixa de preço
- Melhor/Pior retorno
- Total de observações

---

## ⚙️ Configuração Avançada

### Usar Mais Ações

Edite `api_example.py`:

```python
STOCKS = [
    'ABEV3_SA', 'ALOS3_SA', 'ASAI3_SA', 'AURE3_SA', 'AZUL4_SA',
    'B3SA3_SA', 'BBAS3_SA', 'BBDC3_SA', 'BBDC4_SA', 'BBSE3_SA',
    'PETR3_SA', 'PETR4_SA', 'VALE3_SA', 'WEGE3_SA',
    # Adicione mais aqui
]
```

### Conectar com Banco de Dados Real

Substitua em `api_example.py`:

```python
@app.get("/api/stocks/{stock}/price-history")
async def get_price_history(stock: str, days: int = 365):
    # Em vez de usar yfinance, consulte seu banco
    from seu_modulo import database
    return database.get_price_history(stock, days)
```

### Cache para Performance

```python
from functools import lru_cache
import pandas as pd

@lru_cache(maxsize=32)
def load_csv(filename: str):
    return pd.read_csv(filename)
```

---

## 🐛 Troubleshooting

### 1. Frontend não consegue conectar à API

**Erro:** `Failed to fetch http://localhost:8000/api/stocks`

**Solução:**
```bash
# 1. Verifique se a API está rodando
curl http://localhost:8000/api/health

# 2. Verifique se CORS está configurado
# No api_example.py, confira CORSMiddleware

# 3. Atualize .env no frontend
REACT_APP_API_URL=http://localhost:8000/api
```

### 2. Arquivos CSV não encontrados

**Erro:** `404 Not Found: ABEV3_SA_metrics_5d.csv`

**Solução:**
```bash
# Verifique se os arquivos existem
ls co-piloto-quant/data/results/

# Atualize o caminho em api_example.py
DATA_PATH = "caminho/completo/para/data/results"
```

### 3. Erro de porta já em uso

```bash
# Frontend (use outra porta)
npm start -- --port 3001

# API (use outra porta)
uvicorn api_example:app --port 8001
```

### 4. npm não encontrado

```bash
# Instale Node.js
# Windows: https://nodejs.org/
# macOS: brew install node
# Linux: sudo apt install nodejs npm
```

### 5. Python packages não instalados

```bash
pip install fastapi uvicorn python-multipart aiofiles yfinance
```

---

## 📊 Integrando Seus Dados

### Usando CSVs Locais

```bash
# 1. Coloque seus CSVs em:
frontend-react/public/data/results/

# 2. Use o dataLoader.js
import { loadMetricsFromCSV } from './services/dataLoader';

const data = await loadMetricsFromCSV('STOCK_NAME_metrics_5d');
```

### Usando Banco de Dados SQLite

```python
# Em api_example.py
import sqlite3

@app.get("/api/stocks/{stock}/price-history")
async def get_price_history(stock: str):
    conn = sqlite3.connect('market_data.db')
    query = f"SELECT * FROM {stock} ORDER BY date DESC LIMIT 365"
    df = pd.read_sql(query, conn)
    return df.to_dict(orient='records')
```

---

## 🚀 Deploy para Produção

### Frontend (Vercel, Netlify, GitHub Pages)

```bash
# Build otimizado
npm run build

# Teste localmente
npm install -g serve
serve -s build
```

### Backend (Heroku, AWS, DigitalOcean)

```bash
# Instale Gunicorn
pip install gunicorn

# Execute
gunicorn api_example:app
```

---

## 📞 Próximos Passos

1. ✅ Setup completo (Frontend + Backend)
2. ⬜ Adicionar mais ações
3. ⬜ Conectar com banco de dados real
4. ⬜ Adicionar autenticação
5. ⬜ Deploy em produção
6. ⬜ Adicionar WebSocket para dados em tempo real

---

## 📚 Referências

- [React Docs](https://react.dev)
- [Recharts](https://recharts.org)
- [FastAPI](https://fastapi.tiangolo.com)
- [Pandas](https://pandas.pydata.org)

---

**Pronto para começar?** 🚀

1. Execute `setup.bat` (Windows) ou `./setup.sh` (Mac/Linux)
2. Em outro terminal, execute `python api_example.py`
3. Acesse http://localhost:3000

Aproveite seu dashboard! 📊
