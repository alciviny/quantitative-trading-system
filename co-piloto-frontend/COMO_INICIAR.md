# Co-Piloto Quant Frontend - Guia de Inicialização

## 📋 Pré-requisitos

- Node.js 18+ (https://nodejs.org/)
- npm 9+ (incluso no Node.js)

## 🚀 Instalação e Execução

### 1. Navegar para a pasta do frontend

```bash
cd co-piloto-frontend
```

### 2. Instalar dependências

```bash
npm install
```

**Nota**: A instalação pode demorar alguns minutos na primeira vez.

### 3. Executar o servidor de desenvolvimento

```bash
npm run dev
```

O frontend estará disponível em: **http://localhost:3001**

## 🎯 O que você vai ver

### ✅ Dashboard (Página Inicial)
- **Regime de Mercado** com indicador visual (Bull/Bear/Lateral/Volátil)
- **Matriz de Correlação** entre ativos em heatmap
- **Cards de Alertas**: Ativos em zona de compra, volatilidade explosiva, tendências fortes

### ✅ Scanner/Screener
- Tabela com **20 ativos B3** (dados mockados)
- **Colunas profissionais**: 
  - Ticker, Nome, Preço, Variação%
  - Hurst Exponent (tendência vs reversão)
  - Fractal Dimension, Entropia, RSI
  - Status da Estratégia (BUY/SELL/NEUTRAL)
  - Probabilidade ML (0-100%)
- **Filtros avançados** e busca em tempo real
- **Ordenação** por qualquer coluna

## 🔧 Conectar com API Python Real

Por padrão, o frontend usa **dados mockados**. Para conectar com sua API Python:

1. Certifique-se que `api_backend.py` está rodando na porta 8000
2. Abra `src/services/api.ts`
3. Mude a linha:
   ```typescript
   const USE_MOCKS = false // Era true
   ```
4. Salve e o frontend reconectará automaticamente

## 🎨 Tema e Design

- **Dark Mode** obrigatório (padrão financeiro)
- **Cores semânticas**:
  - Verde (#10b981) = Bull/Alta/Positivo
  - Vermelho (#ef4444) = Bear/Baixa/Negativo
  - Cinza = Neutral/Lateral
- **Densidade alta** - Máximo de dados organizados
- **Fonte mono** para números financeiros

## 📊 Estrutura do Projeto

```
co-piloto-frontend/
├── src/
│   ├── components/
│   │   ├── ui/           # Componentes base (Button, Card, Table, Badge)
│   │   ├── dashboard/    # Dashboard (Regime, Heatmap, Alertas)
│   │   └── scanner/      # Scanner (Tabela de ativos)
│   ├── pages/            # Páginas (Dashboard, Scanner)
│   ├── hooks/            # React Query hooks personalizados
│   ├── services/         # API e dados mockados
│   ├── types/            # TypeScript types
│   └── lib/              # Utilitários (formatação, etc)
├── index.html
├── vite.config.ts
├── tailwind.config.js
└── package.json
```

## 🔥 Próximas Features (Em desenvolvimento)

- **Lab de Backtest**: Curva de equity, métricas (Sharpe, Sortino), underwater plot
- **Deep Dive do Ativo**: Gráfico candlestick com Kalman Bands e indicadores
- **Monitor de Saúde**: Status MT5, latência, CPU, memória, ordens

## 🐛 Solução de Problemas

### Erro ao executar `npm run dev`
- Execute `npm install` novamente
- Verifique se a porta 3001 está livre
- Tente rodar `npm cache clean --force` e instalar novamente

### Frontend não mostra dados reais
- Verifique se `USE_MOCKS = false` em `src/services/api.ts`
- Confirme que `api_backend.py` está rodando (http://localhost:8000)
- Abra DevTools (F12) e veja erros de rede

### Tabela vazia no Scanner
- Se `USE_MOCKS = true`, deve mostrar 20 ativos automaticamente
- Se `USE_MOCKS = false`, precisa da API rodando

## 🎓 Scripts Disponíveis

- `npm run dev` - Inicia servidor de desenvolvimento
- `npm run build` - Compila para produção
- `npm run preview` - Preview da build de produção
- `npm run lint` - Verifica código TypeScript

---

**Qualquer dúvida, abra o README.md principal!**
