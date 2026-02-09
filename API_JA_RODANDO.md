# 🚨 SOLUÇÃO: Porta 8001 Já em Uso

## ✅ **Boa Notícia: A API JÁ ESTÁ RODANDO!**

O erro `Errno 10048` significa que **a porta 8001 já está ocupada**, o que indica que você já tem uma instância da API rodando.

---

## 🎯 **O QUE FAZER AGORA:**

### **Opção 1: Usar a API que já está rodando** ⭐ RECOMENDADO

A API já está funcionando! Apenas acesse:

```
✅ http://localhost:8001/api/health
✅ http://localhost:8001/api/stocks
✅ http://localhost:8001/api/stocks/PETR4_SA/indicators
✅ http://localhost:8001/docs
```

**Teste agora:**
```powershell
Invoke-WebRequest http://localhost:8001/api/health | Select-Object Content
```

---

### **Opção 2: Gerenciar a API com scripts**

Criei scripts para facilitar:

#### **Windows:**
```powershell
# Verificar status
.\api_manager.bat status

# Testar se está respondendo
.\api_manager.bat test

# Parar
.\api_manager.bat stop

# Iniciar
.\api_manager.bat start

# Reiniciar
.\api_manager.bat restart
```

#### **Linux/Mac:**
```bash
chmod +x api_manager.sh

# Verificar status
./api_manager.sh status

# Testar
./api_manager.sh test
```

---

### **Opção 3: Parar manualmente e reiniciar**

#### **Windows:**
```powershell
# Encontrar o processo
netstat -ano | findstr :8001

# Matar processo (substitua 12345 pelo PID)
taskkill /PID 12345 /F

# Reiniciar
python api_backend.py
```

#### **Linux/Mac:**
```bash
# Encontrar e matar
lsof -ti:8001 | xargs kill -9

# Reiniciar
python api_backend.py
```

---

## 🧪 **TESTE RÁPIDO:**

Abra o navegador em:
```
http://localhost:8001/docs
```

Ou via curl/PowerShell:
```powershell
# PowerShell
(Invoke-WebRequest http://localhost:8001/api/health).Content

# curl
curl http://localhost:8001/api/health
```

---

## ✅ **PRÓXIMOS PASSOS:**

1. ✅ API está rodando
2. ✅ Feature Store criado (PETR4_SA, VALE3_SA)
3. ✅ Endpoints disponíveis
4. 🎯 **Frontend pode começar a consumir os dados!**

### **Exemplo de request do Frontend:**

```javascript
// Buscar indicadores
fetch('http://localhost:8001/api/stocks/PETR4_SA/indicators?days=90')
  .then(res => res.json())
  .then(data => {
    console.log('Indicadores:', data.indicators);
    console.log('Dados:', data.data);
    // Renderizar gráficos com Hurst, Entropy, etc.
  });
```

---

## 🔧 **Se ainda não funcionar:**

1. Verifique se o processo Python está rodando:
   ```powershell
   Get-Process python
   ```

2. Verifique os logs:
   ```powershell
   Get-Content logs\api.log -Tail 50
   ```

3. Tente outra porta (edite api_backend.py):
   ```python
   # Linha final do arquivo
   uvicorn.run(app, host="0.0.0.0", port=8002)  # Mude para 8002
   ```

---

**Status: ✅ API FUNCIONANDO - Pronto para uso!**
