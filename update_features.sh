#!/bin/bash
# ================================================================
# Feature Store Updater - Co-Piloto Quant
# ================================================================
# Atualiza o Feature Store com indicadores complexos
# Execute diariamente (cron job)
# ================================================================

set -e  # Exit on error

echo ""
echo "========================================"
echo " Feature Store Updater v1.0"
echo " Co-Piloto Quant"
echo "========================================"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/co-piloto-quant"

# Activate virtual environment
echo "[1/3] Ativando ambiente virtual..."
source vbt_env/bin/activate || {
    echo "ERRO: Não foi possível ativar o ambiente virtual"
    echo "Verifique se o venv existe em: co-piloto-quant/vbt_env/"
    exit 1
}

echo "[2/3] Construindo Feature Store..."
echo "Calculando indicadores complexos para todas as ações..."
echo ""

# Execute build script
python scripts/build_feature_store.py --workers 4 || {
    echo ""
    echo "ERRO: Falha ao construir Feature Store"
    echo "Verifique os logs em: co-piloto-quant/logs/feature_store.log"
    exit 1
}

echo ""
echo "[3/3] Feature Store atualizado com sucesso!"
echo ""
echo "========================================"
echo " Próximos passos:"
echo "========================================"
echo " 1. Inicie a API: python ../api_backend.py"
echo " 2. Acesse: http://localhost:8001/api/health"
echo " 3. Verifique \"feature_store.enabled = true\""
echo "========================================"
echo ""
