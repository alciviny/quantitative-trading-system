# 🎨 FRONTEND EM REACT - Arquitetura e Implementação

## 📋 Comparação: Streamlit vs React

| Aspecto | Streamlit | React |
|--------|-----------|-------|
| **Velocidade de Dev** | ⚡ Rápido (Python) | 🐢 Médio (JS/TS) |
| **Performance** | ⚠️ Lenta (re-renders) | ⚡ Rápida (otimizada) |
| **Customização UI** | 🟡 Limitada | 🟢 Ilimitada |
| **Gráficos** | 🟡 Plotly OK | 🟢 ECharts/D3/Recharts |
| **Responsiveness** | 🟡 Mobile ruim | 🟢 Mobile first |
| **Dados em Tempo Real** | 🟡 WebSocket complicado | 🟢 WebSocket nativo |
| **Deploy** | 🟢 Streamlit Cloud fácil | 🟡 Requer setup |
| **Produção** | ⚠️ Não recomendado | ✅ Padrão da indústria |

**Conclusão**: React é **melhor para longo prazo**, especialmente com dados financeiros.

---

## 🏗️ ARQUITETURA PROPOSTA

```
co-piloto-quant-web/
├── backend/
│   ├── app.py                    # FastAPI
│   ├── routes/
│   │   ├── indicators.py         # GET /api/indicators/:ticker
│   │   ├── backtests.py          # POST /api/backtests
│   │   └── market_data.py        # GET /api/prices/:ticker
│   ├── models/
│   │   ├── schemas.py            # Pydantic models
│   │   └── database.py           # SQLAlchemy
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.tsx     # Layout principal
│   │   │   ├── Chart.tsx         # Gráficos interativos
│   │   │   ├── MetricsPanel.tsx  # Métricas em cards
│   │   │   ├── RegimeStatus.tsx  # Status de regime
│   │   │   └── TradeTable.tsx    # Histórico de trades
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── AnalysisPage.tsx
│   │   │   └── BacktestPage.tsx
│   │   ├── services/
│   │   │   └── api.ts            # Chamadas HTTP
│   │   ├── hooks/
│   │   │   ├── useIndicators.ts
│   │   │   └── useMarketData.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
│
└── docker-compose.yml            # Orquestração
```

---

## 🚀 STACK RECOMENDADO

### Frontend

```json
{
  "dependencies": {
    "react": "^18.x",
    "react-router-dom": "^6.x",
    "axios": "^1.x",
    "zustand": "^4.x",
    "date-fns": "^2.x"
  },
  "devDependencies": {
    "typescript": "^5.x",
    "vite": "^4.x",
    "@vitejs/plugin-react": "^4.x",
    "tailwindcss": "^3.x",
    "postcss": "^8.x"
  },
  "charting": {
    "recharts": "^2.x OR tradingview/lightweight-charts"
  }
}
```

**Por que cada um**:
- **React 18**: Concurrent rendering, melhora performance
- **Zustand**: State management leve (melhor que Redux)
- **Vite**: Build rápido (200ms vs 10s do Create React App)
- **Tailwind**: Utility CSS, prototipagem rápida
- **Recharts ou TradingView Charts**: Gráficos financeiros nativos

### Backend

```
Python 3.11+
FastAPI            # API moderna e rápida
SQLAlchemy         # ORM robusto
Pydantic           # Validação de dados
PyArrow            # Processamento rápido de dados
Redis              # Cache (opcional)
```

---

## 🔌 API REST - Endpoints Necessários

### **1. Market Data**

```
GET /api/market-data/{ticker}
Query: ?start=2024-01-01&end=2024-12-31&interval=1d

Response:
{
  "ticker": "PETR4.SA",
  "data": [
    {
      "date": "2024-01-01",
      "open": 25.5,
      "high": 26.1,
      "low": 25.3,
      "close": 26.0,
      "volume": 1000000
    }
  ]
}
```

### **2. Indicadores**

```
GET /api/indicators/{ticker}
Query: ?date=2024-01-15&lookback=90

Response:
{
  "ticker": "PETR4.SA",
  "date": "2024-01-15",
  "indicators": {
    "price": 26.0,
    "hurst_72": 0.65,
    "entropy_20": 2.3,
    "vol_20": 0.018,
    "vol_of_vol_20": 0.005,
    "bollinger_upper": 27.5,
    "bollinger_middle": 26.0,
    "bollinger_lower": 24.5,
    "rsi_14": 65,
    "vwap_z_score": 0.5,
    "regime_score": 75,
    "regime_state": "TREND"
  }
}
```

### **3. Histórico de Indicadores**

```
GET /api/indicators/{ticker}/history
Query: ?start=2024-01-01&end=2024-12-31

Response:
{
  "ticker": "PETR4.SA",
  "data": [
    {"date": "2024-01-01", "hurst_72": 0.60, "entropy_20": 2.1, ...},
    {"date": "2024-01-02", "hurst_72": 0.62, "entropy_20": 2.2, ...},
    ...
  ]
}
```

### **4. Backtests**

```
POST /api/backtests

Request:
{
  "ticker": "PETR4.SA",
  "strategy": "hurst_regime",
  "params": {
    "hurst_threshold": 0.6,
    "entropy_max": 3.0
  },
  "start_date": "2023-01-01",
  "end_date": "2024-12-31"
}

Response:
{
  "backtest_id": "bt_abc123",
  "status": "completed",
  "results": {
    "total_return": 0.35,
    "sharpe": 1.2,
    "max_drawdown": -0.15,
    "win_rate": 0.55,
    "trades": 45
  }
}
```

### **5. Tickers Disponíveis**

```
GET /api/tickers

Response:
{
  "universes": {
    "b3": ["PETR4.SA", "VALE3.SA", ...],
    "us_tech": ["AAPL", "MSFT", ...],
    "forex": ["EURUSD", "GBPUSD", ...]
  }
}
```

---

## 🎨 COMPONENTES REACT - Exemplo Prático

### **1. Dashboard Principal**

```typescript
// src/components/Dashboard.tsx
import { useState, useEffect } from 'react';
import Chart from './Chart';
import MetricsPanel from './MetricsPanel';
import RegimeStatus from './RegimeStatus';
import { useIndicators } from '../hooks/useIndicators';

export default function Dashboard() {
  const [ticker, setTicker] = useState('PETR4.SA');
  const { indicators, loading, error } = useIndicators(ticker);

  return (
    <div className="p-6 bg-dark-900">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Co-Piloto Quant</h1>
        <input
          type="text"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          placeholder="TICKER (ex: PETR4.SA)"
          className="px-4 py-2 bg-dark-800 border border-green-500"
        />
      </div>

      {/* Grid Principal */}
      <div className="grid grid-cols-12 gap-4">
        
        {/* Gráfico - 8 colunas */}
        <div className="col-span-8">
          <Chart ticker={ticker} />
        </div>

        {/* Painel Direito - 4 colunas */}
        <div className="col-span-4 space-y-4">
          <RegimeStatus regime={indicators?.regime_state} score={indicators?.regime_score} />
          <MetricsPanel indicators={indicators} />
        </div>

      </div>
    </div>
  );
}
```

### **2. Componente de Gráfico com Indicadores**

```typescript
// src/components/Chart.tsx
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useMarketData } from '../hooks/useMarketData';

export default function Chart({ ticker }: { ticker: string }) {
  const { data, loading } = useMarketData(ticker);

  if (loading) return <div>Carregando...</div>;

  return (
    <div className="bg-dark-800 p-4 rounded-lg">
      <ResponsiveContainer width="100%" height={400}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" />
          <YAxis />
          <Tooltip />
          <Legend />
          
          {/* Preço */}
          <Line type="monotone" dataKey="close" stroke="#00ff00" name="Preço" />
          
          {/* Bollinger Bands */}
          <Line type="monotone" dataKey="bollinger_upper" stroke="#ff0000" strokeDasharray="5 5" name="BB Upper" />
          <Line type="monotone" dataKey="bollinger_lower" stroke="#ff0000" strokeDasharray="5 5" name="BB Lower" />
          
          {/* EMA */}
          <Line type="monotone" dataKey="ema_50" stroke="#ffa500" name="EMA 50" />
          <Line type="monotone" dataKey="ema_200" stroke="#00aaff" name="EMA 200" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
```

### **3. Painel de Métricas**

```typescript
// src/components/MetricsPanel.tsx
export default function MetricsPanel({ indicators }) {
  const renderIndicator = (name: string, value: any, color: string = 'text-blue-400') => (
    <div className="bg-dark-700 p-3 rounded">
      <p className="text-sm text-gray-400">{name}</p>
      <p className={`text-xl font-bold ${color}`}>
        {typeof value === 'number' ? value.toFixed(3) : value || '-'}
      </p>
    </div>
  );

  return (
    <div className="space-y-2">
      {renderIndicator('Hurst (72d)', indicators?.hurst_72, 'text-purple-400')}
      {renderIndicator('Entropia (20d)', indicators?.entropy_20, 'text-pink-400')}
      {renderIndicator('Vol (20d)', indicators?.vol_20, 'text-yellow-400')}
      {renderIndicator('Vol-of-Vol', indicators?.vol_of_vol_20, 'text-red-400')}
      {renderIndicator('Z-Score Hurst', indicators?.hurst_z_score, 'text-cyan-400')}
      {renderIndicator('VWAP Z-Score', indicators?.vwap_z_score, 'text-green-400')}
    </div>
  );
}
```

### **4. Status de Regime (Colorido!)**

```typescript
// src/components/RegimeStatus.tsx
export default function RegimeStatus({ regime, score }: { regime: string; score: number }) {
  const colorMap = {
    'TOXIC': 'bg-red-900',
    'CHOP': 'bg-orange-900',
    'NEUTRAL': 'bg-gray-900',
    'TREND': 'bg-blue-900',
    'CLEAN_TREND': 'bg-green-900'
  };

  const textMap = {
    'TOXIC': 'text-red-200',
    'CHOP': 'text-orange-200',
    'NEUTRAL': 'text-gray-200',
    'TREND': 'text-blue-200',
    'CLEAN_TREND': 'text-green-200'
  };

  return (
    <div className={`p-6 rounded-lg ${colorMap[regime] || 'bg-gray-900'}`}>
      <p className="text-sm text-gray-400">Estado do Mercado</p>
      <p className={`text-3xl font-bold ${textMap[regime]}`}>{regime}</p>
      <div className="mt-2 bg-black/30 rounded h-2">
        <div 
          className={`h-2 rounded ${colorMap[regime]}`}
          style={{ width: `${score}%` }}
        ></div>
      </div>
      <p className="text-xs text-gray-400 mt-1">Score: {score.toFixed(1)}/100</p>
    </div>
  );
}
```

---

## 🔄 Hook para Dados - State Management com Zustand

```typescript
// src/store/marketStore.ts
import { create } from 'zustand';

interface IndicatorState {
  indicators: any | null;
  loading: boolean;
  error: string | null;
  fetchIndicators: (ticker: string) => Promise<void>;
}

export const useIndicatorStore = create<IndicatorState>((set) => ({
  indicators: null,
  loading: false,
  error: null,
  
  fetchIndicators: async (ticker: string) => {
    set({ loading: true });
    try {
      const response = await fetch(`/api/indicators/${ticker}`);
      const data = await response.json();
      set({ indicators: data, error: null });
    } catch (err) {
      set({ error: err.message });
    } finally {
      set({ loading: false });
    }
  }
}));
```

---

## 🚀 SETUP INICIAL - Passo a Passo

### **1. Criar Backend (FastAPI)**

```bash
# criar pasta
mkdir co-piloto-web-backend
cd co-piloto-web-backend

# criar venv
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows

# instalar deps
pip install fastapi uvicorn sqlalchemy pydantic pandas
pip install python-multipart
```

**app.py básico**:
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Enable CORS para o frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/indicators/{ticker}")
async def get_indicators(ticker: str):
    # Import seu feature_factory
    from src.co_piloto_quant.data.data_manager import data_manager
    
    df = data_manager.get_data(ticker)
    latest = df.iloc[-1].to_dict()
    return latest

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### **2. Criar Frontend (React + Vite)**

```bash
# criar projeto
npm create vite@latest co-piloto-web-frontend -- --template react-ts

cd co-piloto-web-frontend

# instalar dependências
npm install
npm install axios zustand recharts date-fns
npm install -D tailwindcss postcss autoprefixer

# setup tailwind
npx tailwindcss init -p
```

**vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})
```

### **3. Docker Compose**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./market_data.db
    volumes:
      - ./backend/src:/app/src

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  market_data:
```

---

## 📊 RECOMENDAÇÕES DE BIBLIOTECAS DE GRÁFICOS

### **Option 1: Recharts** ✅ Recomendado
```
Vantagens:
- Composable React
- Fácil de customizar
- Ótimo para múltiplas linhas
- Bom para iniciantes

Desvantagem:
- Menos otimizado para grande volume de dados
```

### **Option 2: TradingView Lightweight Charts** 🏆 MELHOR para Financeiro
```
Vantagens:
- Extremamente otimizado
- Padrão da indústria (TradingView)
- Velas (candlestick) nativas
- Performance excelente

Desvantagem:
- Curva de aprendizado maior
```

### **Option 3: ECharts**
```
Vantagens:
- Muitas opções de customização
- Performance boa
- Suporte a muitos tipos de gráfico

Desvantagem:
- Bundle size maior
```

**Minha recomendação para seu caso**: 
**TradingView Lightweight Charts + Recharts** (use TradingView para preços, Recharts para indicadores)

---

## 🎯 ROADMAP DE IMPLEMENTAÇÃO

### **Phase 1: MVP (2-3 semanas)**
- [ ] Backend FastAPI básico
- [ ] Endpoint /api/indicators/{ticker}
- [ ] Frontend com gráfico Recharts
- [ ] Seletor de ticker
- [ ] Deploy local com Docker

### **Phase 2: Melhorias (1-2 semanas)**
- [ ] Histórico de indicadores com range picker
- [ ] Backtests visuais
- [ ] Comparação entre tickers
- [ ] Dark mode (já tem UI ready)

### **Phase 3: Avançado (2-3 semanas)**
- [ ] WebSocket para dados em tempo real
- [ ] Alertas customizáveis
- [ ] Export de relatórios (PDF)
- [ ] Portfolio dashboard

---

## 📞 PRÓXIMOS PASSOS

Você quer que eu:
1. ✅ Crie o backend FastAPI completo?
2. ✅ Crie o projeto React base com componentes?
3. ✅ Integre tudo com Docker?
4. ✅ Outra coisa?

---

**Data**: 8 de fevereiro de 2026  
**Recomendação**: Comece com a Phase 1, será rápido!
