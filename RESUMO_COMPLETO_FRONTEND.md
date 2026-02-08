# 🚀 Co-Piloto Quant - Sistema Completo

Sistema de Trading Quantitativo profissional com backend Python e frontend React moderno.

---

## 📁 Estrutura do Projeto

```
SSD-SUPORTE QUANTITATIVO/
│
├── co-piloto-quant/              # Backend Python (já existente)
│   ├── data/
│   │   ├── processed/            # *.parquet (OHLCV + indicadores)
│   │   └── results/              # *.csv (backtest results)
│   ├── models/                   # *.joblib (Random Forest)
│   ├── scripts/                  # Scripts de análise
│   └── src/co_piloto_quant/      # Código principal
│
├── co-piloto-frontend/           # Frontend React (NOVO)
│   ├── src/
│   │   ├── components/           # Componentes React
│   │   ├── pages/                # Páginas (Dashboard, Scanner)
│   │   ├── hooks/                # React Query hooks
│   │   ├── services/             # API + Mock data
│   │   └── types/                # TypeScript types
│   ├── package.json
│   ├── setup.bat                 # Instalação automática
│   └── start.bat                 # Iniciar frontend
│
├── api_backend.py                # API FastAPI (já existente)
├── start-all.bat                 # Inicia backend + frontend React antigo
└── ARQUITETURA_FRONTEND.md       # Documentação completa (NOVO)
```

---

## 🎯 O que foi entregue

### ✅ COMPLETO: Frontend React Profissional

#### 1. **Dashboard de Regime de Mercado**
- 🌡️ **Clima do Mercado**: Bull/Bear/Lateral/Volátil
  - Confiança (0-100%)
  - Volatilidade
  - Força da tendência
  - Hurst médio
- 🔥 **Heatmap de Correlação**: Matriz visual entre 10 ativos
- 🚨 **Cards de Alertas**:
  - Ativos em zona de compra
  - Volatilidade explosiva
  - Tendências fortes (Hurst > 0.6)

#### 2. **Scanner/Screener Profissional**
- 📊 **Tabela Densa** com TanStack Table
  - 20 ativos B3 (mockados)
  - **Colunas críticas**:
    - Ticker, Nome, Preço, Variação%
    - Hurst Exponent
    - Fractal Dimension
    - Entropia (Shannon)
    - RSI
    - Status da Estratégia (BUY/SELL/NEUTRAL)
    - Probabilidade ML (0-100%)
- 🔍 **Filtros Avançados**:
  - Busca por ticker
  - Filtro por status (apenas BUY)
  - Ordenação por qualquer coluna
  - Virtual scrolling (performance)

#### 3. **Infraestrutura Técnica**
- ⚡ **Vite + React 18 + TypeScript**
- 🎨 **Tailwind CSS** com tema dark financeiro
- 📦 **Shadcn/UI** (Button, Card, Table, Badge, Input)
- 🔄 **TanStack Query** (cache e refetch automático)
- 📋 **TanStack Table** (filtros, ordenação, virtual scroll)
- 📊 **Recharts** para gráficos futuros
- 🎨 **Lucide React** para ícones

---

## 🏃 Como Executar

### Opção 1: Frontend Novo (Recomendado)

```bash
# 1. Navegar para o frontend
cd co-piloto-frontend

# 2. Instalar dependências
.\setup.bat
# OU manualmente: npm install

# 3. Iniciar
.\start.bat
# OU manualmente: npm run dev

# Acesse: http://localhost:3001
```

### Opção 2: Sistema Completo (Backend + Frontend)

```bash
# Na raiz do projeto
.\start-all.bat

# Isso inicia:
# - Backend API (Python): http://localhost:8000
# - Frontend Antigo (React): http://localhost:3000
```

---

## 🔌 Conectar Frontend Novo com API Python

Por padrão, o frontend usa **dados mockados**. Para usar dados reais:

1. **Certifique que a API está rodando**:
   ```bash
   python api_backend.py
   ```

2. **Ative a API real no frontend**:
   - Abra: `co-piloto-frontend/src/services/api.ts`
   - Mude: `const USE_MOCKS = false`
   - Salve (hot reload automático)

3. **Teste**:
   - Dashboard deve mostrar regime real
   - Scanner deve listar seus 70+ ativos B3

---

## 📊 Funcionalidades por Página

| Página | URL | Status | Descrição |
|--------|-----|--------|-----------|
| **Dashboard** | `/` | ✅ COMPLETO | Regime de mercado, heatmap, alertas |
| **Scanner** | `/scanner` | ✅ COMPLETO | Tabela densa com filtros e ordenação |
| **Backtest** | `/backtest` | 🚧 EM BREVE | Equity curve, métricas, underwater plot |
| **Deep Dive** | `/asset/:id` | 🚧 EM BREVE | TradingView charts + Kalman Bands |
| **Saúde** | `/health` | 🚧 EM BREVE | Status MT5, CPU, memória, ordens |

---

## 🎨 Design System

### Tema Dark Financeiro
- **Background**: `#0f172a` (Slate 900)
- **Cards**: `#1e293b` (Slate 800)
- **Border**: `#334155` (Slate 700)

### Cores Semânticas
- 🟢 **Bull (Alta)**: `#10b981` (Emerald 500)
- 🔴 **Bear (Baixa)**: `#ef4444` (Red 500)
- ⚪ **Neutral (Lateral)**: `#6b7280` (Gray 500)
- 🟡 **Alert (Volátil)**: `#eab308` (Yellow 500)

### Tipografia
- **Sans**: Inter (UI geral)
- **Mono**: Fira Code (números financeiros)

---

## 🔧 Tecnologias Utilizadas

### Frontend
| Categoria | Tecnologia | Versão |
|-----------|-----------|--------|
| **Core** | React | 18.2.0 |
| **Build** | Vite | 5.0.8 |
| **Linguagem** | TypeScript | 5.2.2 |
| **Estilo** | Tailwind CSS | 3.4.0 |
| **Componentes** | Shadcn/UI | - |
| **State** | TanStack Query | 5.17.0 |
| **Tabelas** | TanStack Table | 8.11.0 |
| **Gráficos** | Recharts | 2.10.3 |
| **Ícones** | Lucide React | 0.294.0 |
| **Router** | React Router | 6.20.0 |

### Backend (já existente)
- Python 3.9+
- FastAPI
- Pandas + Pyarrow
- vectorbt
- Random Forest (scikit-learn)

---

## 📚 Documentação Adicional

- **ARQUITETURA_FRONTEND.md**: Diagrama completo do fluxo de dados
- **co-piloto-frontend/README.md**: Documentação técnica do frontend
- **co-piloto-frontend/COMO_INICIAR.md**: Guia passo a passo para iniciantes

---

## 🚧 Próximos Passos (Roadmap)

### Fase 2: Lab de Backtest
- [ ] Gráfico de Equity Curve (Recharts)
- [ ] Cards de métricas (Sharpe, Sortino, Max DD)
- [ ] Underwater Plot (drawdown visual)
- [ ] Tabela de trades com filtros

### Fase 3: Deep Dive do Ativo
- [ ] TradingView Lightweight Charts (candlestick)
- [ ] Overlay de Kalman Bands
- [ ] Overlay de VWAP Bands
- [ ] Indicadores técnicos (RSI, Hurst, Entropy)
- [ ] Painel de ML Probability

### Fase 4: Sistema Health
- [ ] Status da conexão MT5
- [ ] Monitor de CPU/Memória (Docker)
- [ ] Log de ordens (pending/executed)
- [ ] Latência da API

### Fase 5: Integrações
- [ ] WebSocket para updates em tempo real
- [ ] Alertas sonoros para sinais críticos
- [ ] Export de relatórios (PDF/Excel)
- [ ] Configurações persistentes

---

## 🎓 Para Desenvolvedores

### Adicionar novo endpoint na API

1. **Backend** (`api_backend.py`):
```python
@app.get("/api/novo-endpoint")
async def novo_endpoint():
    return {"data": "exemplo"}
```

2. **Frontend** (`src/services/api.ts`):
```typescript
novoEndpoint: async () => {
  const { data } = await api.get('/novo-endpoint')
  return data
}
```

3. **Hook** (`src/hooks/useQueries.ts`):
```typescript
export const useNovoEndpoint = () => {
  return useQuery({
    queryKey: ['novoEndpoint'],
    queryFn: () => apiService.novoEndpoint(),
  })
}
```

### Adicionar nova página

1. Criar `src/pages/NovaPagina.tsx`
2. Adicionar rota em `src/App.tsx`
3. Adicionar item no menu de navegação

---

## 🐛 Troubleshooting

### Frontend não inicia
```bash
# Limpar cache e reinstalar
cd co-piloto-frontend
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### API não conecta
- Verifique se `api_backend.py` está rodando
- Teste diretamente: http://localhost:8000/docs
- Confirme `USE_MOCKS = false` em `api.ts`

### Tabela vazia no Scanner
- Se `USE_MOCKS = true`: deve mostrar 20 ativos sempre
- Se `USE_MOCKS = false`: precisa da API com dados reais

---

## 📞 Suporte

- **Documentação Completa**: Veja `ARQUITETURA_FRONTEND.md`
- **Guia de Início**: Veja `co-piloto-frontend/COMO_INICIAR.md`
- **Código Exemplo**: Todos os componentes possuem comentários

---

## ✨ Diferenciais

✅ **Design Profissional**: Tema dark financeiro, densidade alta, UX otimizada  
✅ **Performance**: Virtual scrolling, cache inteligente, code splitting  
✅ **Type-Safe**: 100% TypeScript com tipos rigorosos  
✅ **Escalável**: Arquitetura modular, separação de responsabilidades  
✅ **Testável**: Hooks isolados, componentes puros, mock data  
✅ **Documentado**: README, guias, comentários inline  

---

**🚀 Pronto para Trading de Alta Performance!**
