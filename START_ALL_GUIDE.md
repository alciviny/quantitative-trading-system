# 🚀 START-ALL: Inicialização Completa do Sistema

## ⚡ Uso Rápido

### Windows
```bash
start-all.bat
```

### macOS/Linux
```bash
chmod +x start-all.sh
./start-all.sh
```

---

## 📋 O que o script faz

1. ✅ Verifica se Python e Node.js estão instalados
2. 📦 Instala dependências Python (fastapi, uvicorn, pyarrow)
3. 📦 Instala dependências React (se necessário)
4. 🚀 Inicia Backend API na porta 8000
5. 🚀 Inicia Frontend React na porta 3000
6. 🌐 Abre navegador automaticamente

---

## 🔗 URLs Disponíveis

Após iniciar o sistema:

- **Frontend Dashboard**: http://localhost:3000
- **API Backend**: http://localhost:8000
- **Documentação API**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health

---

## 📊 Dados Utilizados

O backend lê automaticamente:

### Arquivos Parquet (Preços)
```
co-piloto-quant/data/processed/
  ├── ABEV3_SA.parquet
  ├── PETR4_SA.parquet
  ├── VALE3_SA.parquet
  └── ... (70+ ações)
```

### Arquivos CSV (Métricas)
```
co-piloto-quant/data/results/
  ├── {STOCK}_metrics_{5d|10d|20d|40d}.csv
  ├── {STOCK}_vwap_lab_{global|yearly}.csv
  └── {STOCK}_fwd_ret_{5d|10d|20d|40d}.csv
```

---

## ⚙️ Requisitos

### Python 3.9+
```bash
python --version
```

Se não tiver: https://python.org/

### Node.js 16+
```bash
node --version
npm --version
```

Se não tiver: https://nodejs.org/

---

## 🐛 Troubleshooting

### Problema: API não inicia

**Erro:** `ModuleNotFoundError: No module named 'fastapi'`

**Solução:**
```bash
pip install fastapi uvicorn pyarrow
```

---

### Problema: Frontend não conecta à API

**Erro:** `Failed to fetch http://localhost:8000/api/stocks`

**Solução:**
1. Verifique se a API está rodando:
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Verifique se o arquivo `.env` existe em `frontend-react/`:
   ```bash
   cd frontend-react
   cp .env.example .env
   ```

---

### Problema: Porta já em uso

**Erro:** `Error: listen EADDRINUSE: address already in use :::3000`

**Solução (Frontend):**
```bash
# Windows
set PORT=3001 && npm start

# macOS/Linux
PORT=3001 npm start
```

**Solução (API):**
Edite `api_backend.py`, última linha:
```python
uvicorn.run(app, host="0.0.0.0", port=8001)  # Mudou de 8000 para 8001
```

---

### Problema: Dados não aparecem

**Erro:** `404 Not Found: {STOCK}_metrics_5d.csv`

**Causa:** Métricas ainda não foram calculadas

**Solução:**
```bash
cd co-piloto-quant
python scripts/lab_vwap_stress.py
# Ou outro script que gera as métricas
```

---

### Problema: Permission denied (Linux/Mac)

**Erro:** `Permission denied: './start-all.sh'`

**Solução:**
```bash
chmod +x start-all.sh
./start-all.sh
```

---

## 🛑 Como Parar o Sistema

### Windows
- Feche as janelas de terminal que foram abertas
- Ou pressione `Ctrl+C` em cada uma

### macOS/Linux
```bash
# Se iniciou com ./start-all.sh
Ctrl+C

# Ou encontre e mate os processos
ps aux | grep "api_backend\|npm start"
kill <PID_DA_API> <PID_DO_FRONTEND>
```

---

## 🔄 Reiniciar Apenas um Componente

### Reiniciar só a API
```bash
# Windows
python api_backend.py

# macOS/Linux
python3 api_backend.py
```

### Reiniciar só o Frontend
```bash
cd frontend-react
npm start
```

---

## 📊 Logs e Debugging

### Ver logs da API
```bash
# Se você rodou start-all.sh (Linux/Mac)
tail -f api.log
```

### Ver logs do Frontend
Os logs aparecem no terminal onde o `npm start` foi executado

### Verificar se a API está respondendo
```bash
curl http://localhost:8000/api/health
```

Resposta esperada:
```json
{
  "status": "ok",
  "service": "Co-Piloto Quant API",
  "version": "2.0"
}
```

---

## 🎯 Próximos Passos Após Iniciar

1. ✅ Acesse http://localhost:3000
2. ✅ Selecione uma ação no dropdown
3. ✅ Explore as 3 abas:
   - 📈 Preço
   - 📊 Métricas VWAP
   - 💰 Retornos
4. ✅ Teste com diferentes ações
5. ✅ Veja os dados em tempo real

---

## 🔧 Configuração Avançada

### Alterar porta da API
Edite `api_backend.py`, linha final:
```python
uvicorn.run(app, host="0.0.0.0", port=8080)  # Porta customizada
```

Depois atualize o frontend em `frontend-react/.env`:
```
REACT_APP_API_URL=http://localhost:8080/api
```

### Adicionar mais ações
As ações são detectadas automaticamente dos arquivos `.parquet` em:
```
co-piloto-quant/data/processed/
```

Basta adicionar novos arquivos `{TICKER}_SA.parquet` nessa pasta.

---

## 📚 Documentação Completa

- **Frontend**: `frontend-react/README.md`
- **API**: `api_backend.py` (código comentado)
- **Integração**: `COMO_USAR_TUDO_JUNTO.md`

---

## ✅ Checklist de Funcionamento

- [ ] Python instalado (`python --version`)
- [ ] Node.js instalado (`node --version`)
- [ ] Dependências Python instaladas (`pip list | grep fastapi`)
- [ ] Dependências React instaladas (`ls frontend-react/node_modules`)
- [ ] Arquivos parquet existem (`ls co-piloto-quant/data/processed/*.parquet`)
- [ ] API responde (`curl http://localhost:8000/api/health`)
- [ ] Frontend abre no navegador (`http://localhost:3000`)
- [ ] Dados aparecem no dashboard

---

**Pronto! Sistema funcionando! 🎉**

Se tiver problemas, consulte o troubleshooting acima ou abra o `api.log`.
