# 📊 Como Adicionar Novas Ações ao Sistema

## 🎯 Objetivo
Baixar dados de novas ações, calcular indicadores complexos e visualizar no frontend.

---

## 📋 Passo a Passo Completo

### **1️⃣ Escolher os Tickers**

Edite o arquivo que define quais ações usar:
```bash
co-piloto-quant/src/co_piloto_quant/universe.py
```

**Opção A - Usar lista predefinida do IBOVESPA:**
```python
# Já tem ~80 ações do IBOVESPA na função get_b3_tickers()
# Exemplo: ITUB4.SA, BBDC4.SA, MGLU3.SA, etc.
```

**Opção B - Adicionar ações específicas:**
Edite a lista manualmente para incluir/remover ações.

---

### **2️⃣ Baixar Dados Históricos**

Execute o script de download (usa yfinance):

```powershell
# Ative o ambiente virtual
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO"
& "C:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/vbt_env/Scripts/Activate.ps1"

# Baixe dados para ações específicas
cd co-piloto-quant
python scripts/build_dna_b3.py

# OU especifique tickers manualmente:
# python scripts/build_dna_b3.py --tickers ITUB4.SA BBDC4.SA MGLU3.SA
```

**O que esse script faz:**
- ✅ Baixa dados históricos do Yahoo Finance
- ✅ Salva em formato Parquet em `data/processed/`
- ✅ Calcula indicadores básicos (Hurst, Entropy, Half-Life)

---

### **3️⃣ Calcular Feature Store (Indicadores Complexos)**

Execute o pipeline de Feature Engineering:

```powershell
# No mesmo terminal (com vbt_env ativado)
python scripts/build_feature_store.py

# OU para ações específicas:
python scripts/build_feature_store.py --tickers PETR4_SA VALE3_SA ITUB4_SA

# OU com processamento paralelo (mais rápido):
python scripts/build_feature_store.py --workers 8
```

**O que esse script faz:**
- ✅ Lê arquivos `.parquet` de `data/processed/`
- ✅ Calcula +50 indicadores complexos:
  - Hurst Exponent (tendência/reversão)
  - Market Entropy (caos/ordem)
  - Fractal Dimension
  - Lempel-Ziv Complexity
  - Half-Life (mean reversion)
  - Volatilidade adaptativa
  - Regimes de mercado
  - E muito mais...
- ✅ Salva arquivos enriquecidos em `data/features/`

**⏱️ Tempo estimado:**
- 1 ação: ~30 segundos
- 10 ações: ~5 minutos
- 80 ações (IBOVESPA completo): ~30-40 minutos

---

### **4️⃣ Verificar Arquivos Gerados**

Confira se os arquivos foram criados:

```powershell
# Listar arquivos processados
ls co-piloto-quant/data/processed/

# Listar Feature Store (enriquecido)
ls co-piloto-quant/data/features/
```

**Estrutura esperada:**
```
data/
├── processed/          # Dados brutos + indicadores básicos
│   ├── PETR4_SA.parquet
│   ├── VALE3_SA.parquet
│   └── ITUB4_SA.parquet
│
└── features/           # Feature Store (completo)
    ├── PETR4_SA_enriched.parquet
    ├── VALE3_SA_enriched.parquet
    └── ITUB4_SA_enriched.parquet
```

---

### **5️⃣ Reiniciar a API**

A API precisa recarregar para detectar novos arquivos:

```powershell
# Pare a API atual (Ctrl+C no terminal onde ela está rodando)

# Ou force o encerramento:
netstat -ano | findstr :8001
taskkill /F /PID <PID_AQUI>

# Reinicie a API
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO"
& "C:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/vbt_env/Scripts/Activate.ps1"
python api_backend.py
```

**✅ Deve aparecer:**
```
INFO:CopiloAPI:✅ X ações encontradas em Feature Store
```

---

### **6️⃣ Visualizar no Frontend**

Abra o frontend:

```powershell
cd co-piloto-frontend
npm run dev
```

Acesse: **http://localhost:5173**

**Páginas disponíveis:**
- 🏠 **Dashboard**: `/` - Visão geral
- 📊 **Indicadores**: `/indicators` - Gráficos completos com Feature Store
- 📈 **Assets**: `/assets` - Lista de ativos e sinais
- 🔬 **Market**: `/market` - Regime de mercado e correlação

As novas ações aparecerão automaticamente no dropdown! 🎉

---

## 🔄 Atualizar Dados Existentes

Para atualizar dados das ações já existentes:

```powershell
# 1. Re-baixe dados atualizados
python scripts/build_dna_b3.py

# 2. Recalcule Feature Store
python scripts/build_feature_store.py

# 3. Reinicie a API
# (Ctrl+C e rode novamente: python api_backend.py)
```

---

## 🎯 Comandos Rápidos

### Download + Feature Store + API (Tudo de uma vez)

```powershell
# Ative o ambiente
cd "C:\Users\JC INFO\Desktop\SSD-SUPORTE QUANTITATIVO"
& "C:/Users/JC INFO/Desktop/SSD-SUPORTE QUANTITATIVO/co-piloto-quant/vbt_env/Scripts/Activate.ps1"

# Pipeline completo
cd co-piloto-quant
python scripts/build_dna_b3.py
python scripts/build_feature_store.py --workers 4

# Volte e reinicie API
cd ..
python api_backend.py
```

---

## 📝 Notas Importantes

### Formato dos Tickers
- **B3 (Brasil)**: Sempre adicione `.SA` no final
  - Correto: `PETR4.SA`, `VALE3.SA`, `ITUB4.SA`
  - Errado: `PETR4`, `VALE3` ❌

- **API salva sem `.SA`**: 
  - Arquivo: `PETR4_SA.parquet`
  - Frontend vê: `PETR4_SA`

### Feature Store vs Processed
- `data/processed/`: Dados básicos (recomendado para ML)
- `data/features/`: Dados com TODOS os indicadores (para frontend)
- **API prioriza Feature Store** se disponível

### Performance
- Mais ações = Mais tempo de processamento
- Use `--workers 8` para paralelizar
- Recomendado: Comece com 5-10 ações para testar

---

## 🐛 Troubleshooting

### ❌ "Erro ao baixar ticker X"
- Verifique se o ticker existe no Yahoo Finance
- Formato correto: `TICKER.SA` (B3) ou `TICKER` (US)

### ❌ "Ação não aparece no frontend"
- Certifique-se de que o arquivo está em `data/features/` ou `data/processed/`
- Reinicie a API (ela lê os arquivos no startup)
- Verifique o log da API: `✅ X ações encontradas`

### ❌ "Erro 500 ao carregar indicadores"
- Recalcule o Feature Store: `python scripts/build_feature_store.py`
- Arquivo pode estar corrompido ou incompleto

---

## 🚀 Automatização Futura

Você pode criar um script batch para automatizar:

```batch
@echo off
echo ============================================
echo   Co-Piloto Quant - Pipeline Completo
echo ============================================
echo.

cd co-piloto-quant
call ..\co-piloto-quant\vbt_env\Scripts\activate.bat

echo [1/3] Baixando dados...
python scripts\build_dna_b3.py

echo [2/3] Calculando Feature Store...
python scripts\build_feature_store.py --workers 4

echo [3/3] Iniciando API...
cd ..
start python api_backend.py

echo.
echo ✅ Pipeline concluído!
pause
```

Salve como `update_data.bat` na raiz do projeto.

---

**✨ Pronto! Agora você pode adicionar quantas ações quiser ao sistema!**
