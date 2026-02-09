# 🚀 Como Ver os Indicadores no Frontend React

## ✅ TUDO PRONTO! Agora é só iniciar!

---

## 📋 **PASSO A PASSO:**

### **1. Iniciar a API (Backend)**

Em um terminal:

```powershell
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO"

# Ativar ambiente virtual
& ".\co-piloto-quant\vbt_env\Scripts\Activate.ps1"

# Iniciar API
python api_backend.py
```

**Você verá:**
```
🚀 Co-Piloto Quant API v3.0
📊 Feature Store: ENABLED
🌐 URL: http://localhost:8001
```

---

### **2. Iniciar o Frontend (React)**

Em OUTRO terminal:

```powershell
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO\co-piloto-frontend"

# Instalar dependências (se necessário)
npm install

# Iniciar frontend
npm run dev
```

**Você verá:**
```
VITE v5.x ready in XXX ms
➜  Local:   http://localhost:3000
```

---

### **3. Acessar no Navegador**

Abra: **http://localhost:3000**

**No menu lateral, clique em:**
```
🔬 Indicadores
```

---

## 🎨 **O QUE VOCÊ VAI VER:**

### **1. Seletor de Ação e Período**
- Dropdown com todas as ações disponíveis (PETR4_SA, VALE3_SA, etc.)
- Período: 30, 60, 90, 180 dias ou 1 ano

### **2. Cards de Métricas**
```
┌──────────────┬─────────────┬────────────────┐
│ 💰 Preço     │ 🎯 Regime   │ 📊 Indicadores │
│ R$ 38.80     │ TRENDING    │ Hurst: 0.548   │
│ +2.5%        │ HIGH_VOL    │ Entropy: 2.1   │
│ Vol: 18%     │             │ Fractal: 1.52  │
└──────────────┴─────────────┴────────────────┘
```

### **3. Gráficos Interativos**
- 📈 **Preço + SMAs** (20, 50, 200)
- 🔬 **Indicadores Complexos** (Hurst, Entropy, Fractal)
- 📊 **Interpretação automática**

### **4. Badges de Regime**
- 🟢 **TRENDING** - Mercado em tendência
- 🔵 **MEAN-REVERTING** - Reversão à média
- ⚪ **RANDOM** - Random walk
- 🔴 **HIGH_VOL** - Alta volatilidade

---

## 🔧 **ALTERAÇÕES FEITAS:**

### **1. Atualizado: `api.ts`**
```typescript
✅ baseURL: 'http://localhost:8001/api'
✅ Novo: getStocks()
✅ Novo: getStockIndicators() // 50+ indicadores
✅ Novo: getAPIHealth()
```

### **2. Criado: `IndicatorsPage.tsx`**
```typescript
✅ Página completa de indicadores
✅ Gráficos interativos (Recharts)
✅ Cards de métricas
✅ Interpretação automática
```

### **3. Atualizado: `App.tsx`**
```typescript
✅ Nova rota: /indicators
✅ Novo item no menu: "Indicadores"
```

---

## 📊 **INDICADORES DISPONÍVEIS NO FRONTEND:**

### **Básicos:**
- ✅ Retornos (returns, log_returns)
- ✅ Volatilidade (volatility_20, volatility_60)
- ✅ Volume (volume_ma_20, volume_ratio)
- ✅ ATR (Average True Range)
- ✅ ROC (Rate of Change)
- ✅ SMAs (20, 50, 200)

### **Avançados (Feature Store):**
- ✅ **Hurst Exponent** - Persistência vs Mean Reversion
- ✅ **Market Entropy** - Caos/Ordem
- ✅ **Fractal Dimension** - Complexidade
- ✅ **Lempel-Ziv** - Complexidade algorítmica
- ✅ **Half-Life** - Velocidade de reversão
- ✅ **Regime Detection** - Trending/Mean-Reverting

---

## 🐛 **TROUBLESHOOTING:**

### **"API não conecta"**
```powershell
# Verifique se a API está rodando
curl http://localhost:8001/api/health

# Ou no PowerShell
Invoke-WebRequest http://localhost:8001/api/health
```

### **"CORS error"**
✅ Já está configurado no api_backend.py:
```python
allow_origins=["http://localhost:3000", "http://localhost:3001"]
```

### **"Indicadores retornam vazio"**
```powershell
# Execute o Feature Store builder
cd co-piloto-quant
python scripts/build_feature_store.py
```

---

## 🎯 **PRÓXIMOS PASSOS:**

1. ✅ Abra http://localhost:3000
2. ✅ Clique em "Indicadores" no menu
3. ✅ Selecione PETR4_SA
4. ✅ Veja os 50+ indicadores em tempo real!

---

## 📸 **PREVIEW:**

```
┌─────────────────────────────────────┐
│ 🔬 Indicadores Complexos            │
│ Feature Store • Análise Quantitativa│
│                                     │
│ ✅ API v3.0    📁 2 arquivos        │
└─────────────────────────────────────┘

┌────────────────────────────────────┐
│ Ação: [PETR4_SA ▼]  Período: [90▼]│
└────────────────────────────────────┘

[GRÁFICOS INTERATIVOS AQUI]
```

---

**Status: ✅ TUDO INTEGRADO!**

Seu frontend React agora consome os indicadores do Feature Store! 🎉
