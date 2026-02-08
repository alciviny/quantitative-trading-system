#!/bin/bash
set -e

echo "=========================================="
echo "  Co-Piloto Frontend - Instalação"
echo "=========================================="
echo ""

# Limpar instalações anteriores
if [ -d "node_modules" ]; then
  echo "[1/3] Removendo node_modules anterior..."
  rm -rf node_modules
  rm -f package-lock.json
  echo "[OK] Limpeza completa"
  echo ""
fi

# Instalar dependências
echo "[2/3] Instalando dependências..."
npm install
echo "[OK] Dependências instaladas"
echo ""

# Configurar Vite
echo "[3/3] Pronto para desenvolver!"
echo ""
echo "Para iniciar o servidor:"
echo "  npm run dev"
echo ""
echo "Frontend estará disponível em:"
echo "  http://localhost:3001"
echo ""
