#!/bin/bash

# ============================================
# Script de Inicialização Completa
# Backend API + Frontend React
# ============================================

echo ""
echo "========================================"
echo "  CO-PILOTO QUANT - SISTEMA COMPLETO"
echo "========================================"
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null
then
    echo "[ERRO] Python não encontrado!"
    echo "Instale Python 3.9+ de: https://python.org/"
    exit 1
fi
echo "[OK] Python encontrado"

# Verificar npm
if ! command -v npm &> /dev/null
then
    echo "[ERRO] npm não encontrado!"
    echo "Instale Node.js de: https://nodejs.org/"
    exit 1
fi
echo "[OK] npm encontrado"

echo ""
echo "========================================"
echo "  PASSO 1: Instalar dependências Python"
echo "========================================"
echo ""

pip install fastapi uvicorn pyarrow --quiet 2>/dev/null || pip3 install fastapi uvicorn pyarrow --quiet

echo ""
echo "========================================"
echo "  PASSO 2: Instalar dependências React"
echo "========================================"
echo ""

cd frontend-react
if [ ! -d "node_modules" ]; then
    echo "Instalando dependências do React (primeira vez)..."
    npm install
else
    echo "[OK] Dependências React já instaladas"
fi
cd ..

echo ""
echo "========================================"
echo "  PASSO 3: Iniciar Backend API"
echo "========================================"
echo ""

# Iniciar API em background
if command -v python3 &> /dev/null; then
    python3 api_backend.py > api.log 2>&1 &
else
    python api_backend.py > api.log 2>&1 &
fi

API_PID=$!
echo "[OK] API iniciada (PID: $API_PID)"

# Aguardar API iniciar
sleep 5

echo ""
echo "========================================"
echo "  PASSO 4: Iniciar Frontend React"
echo "========================================"
echo ""

cd frontend-react
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "========================================"
echo "  SISTEMA INICIALIZADO!"
echo "========================================"
echo ""
echo "[1] Backend API: http://localhost:8000"
echo "    Docs API:    http://localhost:8000/docs"
echo ""
echo "[2] Frontend:    http://localhost:3000"
echo ""
echo "========================================"
echo ""
echo "PIDs dos processos:"
echo "  API:      $API_PID"
echo "  Frontend: $FRONTEND_PID"
echo ""
echo "Para parar o sistema:"
echo "  kill $API_PID $FRONTEND_PID"
echo ""
echo "Ou pressione Ctrl+C"
echo ""

# Aguardar
wait
