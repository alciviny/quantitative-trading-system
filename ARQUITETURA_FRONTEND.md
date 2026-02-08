# 🏗️ Arquitetura do Sistema - Co-Piloto Quant

## 📊 Visão Geral

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)                  │
│                     Port: 3001                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  Dashboard   │  │   Scanner    │  │  Backtest    │    │
│  │   (Regime)   │  │   (Tabela)   │  │   (Equity)   │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌─────────────────────────────────────────────────┐      │
│  │           TanStack Query (Cache)                │      │
│  └─────────────────────────────────────────────────┘      │
│                        ↓                                    │
│  ┌─────────────────────────────────────────────────┐      │
│  │          API Service (axios)                    │      │
│  │   USE_MOCKS = true/false                        │      │
│  └─────────────────────────────────────────────────┘      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
                        ↓ HTTP
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (FastAPI + Python)                     │
│                     Port: 8000                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Endpoints:                                                 │
│  • GET /api/market/regime       → MarketRegimeData        │
│  • GET /api/assets              → Asset[]                  │
│  • GET /api/assets/:id/ohlcv    → BandData[]              │
│  • GET /api/backtest/results    → BacktestResult          │
│  • GET /api/system/health       → SystemHealth             │
│  • GET /api/market/correlation  → CorrelationMatrix        │
│                                                             │
│  ┌─────────────────────────────────────────────────┐      │
│  │      Processamento (Python)                     │      │
│  │   • vectorbt (backtesting)                      │      │
│  │   • Random Forest (ML)                          │      │
│  │   • Kalman Filter                               │      │
│  │   • Hurst, Entropy, Fractal                     │      │
│  └─────────────────────────────────────────────────┘      │
│                        ↓                                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│                    DADOS                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  • data/processed/*.parquet  (OHLCV + Indicadores)         │
│  • data/results/*.csv        (Backtest Results)            │
│  • database.db               (SQLite - Sinais)             │
│  • models/*.joblib           (Random Forest Models)        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 🔄 Fluxo de Dados

### 1️⃣ Dashboard (Regime de Mercado)

```
Frontend                  Backend                    Data
   │                        │                         │
   ├─ useMarketRegime()     │                         │
   │  GET /api/market/regime│                         │
   │──────────────────────→ │                         │
   │                        ├─ risk_regime.py         │
   │                        ├─ calcula Hurst avg     │
   │                        ├─ calcula volatilidade  │
   │                        │ ←───────────────────── ├─ database.db
   │ ←──────────────────────┤ MarketRegimeData       │
   │                        │                         │
   └─ Renderiza Card       │                         │
```

### 2️⃣ Scanner (Tabela de Ativos)

```
Frontend                  Backend                    Data
   │                        │                         │
   ├─ useAssets()           │                         │
   │  GET /api/assets       │                         │
   │──────────────────────→ │                         │
   │                        ├─ lê todos .parquet     │
   │                        │ ←───────────────────── ├─ data/processed/
   │                        ├─ extrai última linha   │
   │                        ├─ calcula indicadores   │
   │ ←──────────────────────┤ Asset[]                │
   │                        │                         │
   └─ TanStack Table       │                         │
      - Filtros             │                         │
      - Ordenação           │                         │
      - Busca               │                         │
```

### 3️⃣ Backtest (Lab)

```
Frontend                  Backend                    Data
   │                        │                         │
   ├─ useBacktestResult()   │                         │
   │  GET /api/backtest/results                      │
   │──────────────────────→ │                         │
   │                        ├─ lê metrics CSV        │
   │                        │ ←───────────────────── ├─ data/results/
   │                        ├─ lê equity curve       │
   │                        ├─ processa trades       │
   │ ←──────────────────────┤ BacktestResult         │
   │                        │                         │
   └─ Recharts             │                         │
      - Equity Curve        │                         │
      - Underwater Plot     │                         │
      - Métricas Cards      │                         │
```

## 🎨 Design System

### Cores (Tailwind)

```typescript
// Financial-specific colors
bull: {
  DEFAULT: "#10b981",  // Verde para alta
  light: "#34d399",
  dark: "#059669",
  glow: "rgba(16, 185, 129, 0.15)",
}
bear: {
  DEFAULT: "#ef4444",  // Vermelho para baixa
  light: "#f87171",
  dark: "#dc2626",
  glow: "rgba(239, 68, 68, 0.15)",
}
neutral: "#6b7280"     // Cinza para lateral
```

### Componentes UI

```
Button → Ações (filtros, submits)
Card   → Containers de conteúdo
Badge  → Status (BUY/SELL/NEUTRAL)
Table  → Scanner denso
Input  → Busca e filtros
```

## 📦 Estrutura de Componentes

```
src/
├── components/
│   ├── ui/                    # Componentes base (Shadcn/UI)
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── table.tsx
│   │   ├── badge.tsx
│   │   └── input.tsx
│   │
│   ├── dashboard/             # Dashboard widgets
│   │   ├── MarketRegimeCard.tsx     # Clima do mercado
│   │   ├── CorrelationHeatmap.tsx   # Matriz de correlação
│   │   └── AlertCards.tsx           # 3 cards de alertas
│   │
│   └── scanner/               # Scanner/Screener
│       └── AssetTable.tsx           # Tabela densa com TanStack
│
├── pages/                     # Páginas completas
│   ├── DashboardPage.tsx
│   └── ScannerPage.tsx
│
├── hooks/                     # React Query hooks
│   └── useQueries.ts
│
├── services/                  # API e dados
│   ├── api.ts                       # axios + endpoints
│   └── mockData.ts                  # dados simulados
│
├── types/                     # TypeScript types
│   └── trading.ts
│
└── lib/                       # Utilitários
    └── utils.ts                     # formatação, cn()
```

## 🔧 Configuração de Desenvolvimento

### Modo Mock (Desenvolvimento Isolado)

```typescript
// src/services/api.ts
const USE_MOCKS = true  // Dados simulados

// Frontend roda independente do backend
// Ideal para desenvolvimento de UI
```

### Modo Produção (API Real)

```typescript
// src/services/api.ts
const USE_MOCKS = false  // API Python real

// Requer backend rodando em localhost:8000
// Dados vêm dos arquivos .parquet e .csv
```

## 🚀 Deploy

### Frontend (Vite Build)

```bash
npm run build
# Gera: dist/ com HTML/CSS/JS otimizados
# Deploy: Vercel, Netlify, AWS S3, etc
```

### Backend (FastAPI + Uvicorn)

```bash
uvicorn api_backend:app --host 0.0.0.0 --port 8000
# Ou via Docker
```

## 📊 Performance

### Frontend
- **Virtual Scrolling**: TanStack Table lida com 1000+ linhas
- **React Query Cache**: Reduz requests repetidos
- **Code Splitting**: Lazy loading de rotas

### Backend
- **Parquet**: Leitura rápida de colunas específicas
- **Pandas**: Processamento vetorizado
- **FastAPI**: Async endpoints

---

**Sistema projetado para alta performance e escalabilidade**
