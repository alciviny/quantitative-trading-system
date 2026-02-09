#!/bin/bash
# ================================================================
# API Manager - Co-Piloto Quant
# Gerencia a API (start/stop/status/restart)
# ================================================================

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

API_PORT=8001
API_LOG="logs/api.log"

show_help() {
    echo ""
    echo "========================================"
    echo " API Manager - Co-Piloto Quant"
    echo "========================================"
    echo ""
    echo "Uso: ./api_manager.sh [comando]"
    echo ""
    echo "Comandos:"
    echo "  status   - Verifica se a API está rodando"
    echo "  start    - Inicia a API"
    echo "  stop     - Para a API"
    echo "  restart  - Reinicia a API"
    echo "  test     - Testa a API (health check)"
    echo "  help     - Mostra esta ajuda"
    echo ""
}

check_status() {
    echo ""
    echo "Verificando status da API..."
    echo ""
    
    PID=$(lsof -ti:$API_PORT 2>/dev/null)
    
    if [ -n "$PID" ]; then
        echo "✅ API está RODANDO"
        echo ""
        echo "   PID: $PID"
        ps -p $PID -o pid,comm,%cpu,%mem,etime 2>/dev/null
        echo ""
        echo "Para parar: ./api_manager.sh stop"
        echo "Para testar: ./api_manager.sh test"
    else
        echo "❌ API NÃO está rodando"
        echo ""
        echo "Para iniciar: ./api_manager.sh start"
    fi
    echo ""
}

start_api() {
    echo ""
    echo "Iniciando API..."
    echo ""
    
    PID=$(lsof -ti:$API_PORT 2>/dev/null)
    
    if [ -n "$PID" ]; then
        echo "⚠️  API já está rodando (PID: $PID)"
        echo "Use './api_manager.sh restart' para reiniciar"
        echo ""
        return
    fi
    
    # Cria diretório de logs
    mkdir -p logs
    
    # Ativa ambiente virtual e inicia API
    source co-piloto-quant/vbt_env/bin/activate
    
    echo "Iniciando em background..."
    nohup python api_backend.py > "$API_LOG" 2>&1 &
    
    # Aguarda 3 segundos
    sleep 3
    
    # Verifica se iniciou
    PID=$(lsof -ti:$API_PORT 2>/dev/null)
    
    if [ -n "$PID" ]; then
        echo ""
        echo "✅ API iniciada com sucesso!"
        echo ""
        echo "🌐 URL: http://localhost:$API_PORT"
        echo "📖 Docs: http://localhost:$API_PORT/docs"
        echo "📝 Logs: $API_LOG"
        echo "   PID: $PID"
        echo ""
        echo "Para parar: ./api_manager.sh stop"
    else
        echo ""
        echo "❌ Falha ao iniciar API"
        echo "Verifique $API_LOG para detalhes"
        echo ""
    fi
}

stop_api() {
    echo ""
    echo "Parando API..."
    echo ""
    
    PID=$(lsof -ti:$API_PORT 2>/dev/null)
    
    if [ -n "$PID" ]; then
        echo "Parando processo $PID..."
        kill -15 $PID 2>/dev/null
        sleep 2
        
        # Força se ainda estiver rodando
        if kill -0 $PID 2>/dev/null; then
            echo "Forçando parada..."
            kill -9 $PID 2>/dev/null
        fi
        
        echo ""
        echo "✅ API parada com sucesso!"
    else
        echo ""
        echo "⚠️  Nenhuma API rodando na porta $API_PORT"
    fi
    echo ""
}

restart_api() {
    echo ""
    echo "Reiniciando API..."
    stop_api
    sleep 2
    start_api
}

test_api() {
    echo ""
    echo "Testando API..."
    echo ""
    
    PID=$(lsof -ti:$API_PORT 2>/dev/null)
    
    if [ -z "$PID" ]; then
        echo "❌ API não está rodando"
        echo ""
        echo "Para iniciar: ./api_manager.sh start"
        return
    fi
    
    echo "📡 GET http://localhost:$API_PORT/api/health"
    echo ""
    
    response=$(curl -s http://localhost:$API_PORT/api/health 2>/dev/null)
    
    if [ $? -eq 0 ]; then
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        echo ""
        echo "✅ API respondendo corretamente!"
    else
        echo "⚠️  API não respondeu"
    fi
    echo ""
}

# Main
case "$1" in
    status)
        check_status
        ;;
    start)
        start_api
        ;;
    stop)
        stop_api
        ;;
    restart)
        restart_api
        ;;
    test)
        test_api
        ;;
    help|"")
        show_help
        ;;
    *)
        echo "Comando inválido: $1"
        show_help
        exit 1
        ;;
esac
