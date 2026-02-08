# Co-Piloto Quant - Frontend

Sistema de Trading Quantitativo de alta performance com frontend React profissional.

## 🚀 Stack Tecnológica

- **React 18** + **Vite** + **TypeScript**
- **Tailwind CSS** + **Shadcn/UI**
- **TanStack Query** (React Query) - Estado e cache
- **TanStack Table** - Tabelas avançadas
- **Recharts** - Gráficos
- **Lucide React** - Ícones

## 📦 Instalação

```bash
cd co-piloto-frontend
npm install
```

## 🏃 Executar

```bash
npm run dev
```

Acesse: http://localhost:3001

## 🎨 Funcionalidades

### ✅ Dashboard (Regime de Mercado)
- **Clima do Mercado**: Bull/Bear/Lateral/Volátil
- **Heatmap de Correlação**: Matriz visual entre ativos
- **Cards de Alerta**: Zona de compra, volatilidade, tendências

### ✅ Scanner/Screener
- Tabela densa com **todos os ativos B3**
- Colunas: Preço, Variação, Hurst, Fractal, Entropy, RSI, Status, ML Probability
- **Filtros avançados** e ordenação
- **Busca em tempo real**
- Virtual scrolling para performance

### 🚧 Em Desenvolvimento
- Lab de Backtest (Equity Curve, Métricas, Underwater Plot)
- Deep Dive do Ativo (TradingView Charts + Kalman Bands)
- Monitor de Saúde (MT5, Ordens, Recursos)

## 🎯 Configuração

### Conectar API Real

Em `src/services/api.ts`, troque:
```typescript
const USE_MOCKS = false // Ativar API real
```

### Cores Customizadas (Tailwind)

O `tailwind.config.js` possui cores específicas para trading:
- `bull`: Verde (#10b981) - Alta
- `bear`: Vermelho (#ef4444) - Baixa
- `neutral`: Cinza - Lateral
- `chart.up/down/volume`: Cores dos gráficos

## 📊 Estrutura de Pastas

```
src/
├── components/
│   ├── ui/           # Componentes Shadcn/UI
│   ├── dashboard/    # Dashboard widgets
│   └── scanner/      # Scanner table
├── pages/            # Páginas principais
├── hooks/            # React Query hooks
├── services/         # API + Mock data
├── types/            # TypeScript types
└── lib/              # Utilitários
```

## 🔥 Próximos Passos

1. **Backtest Viewer**: Visualizar resultados dos .parquet
2. **TradingView Charts**: Gráficos candlestick com indicadores
3. **Sistema Health**: Monitor MT5 e Docker
4. **Alertas em Tempo Real**: WebSocket integration

---

**Desenvolvido com ❤️ para Trading Quantitativo**
