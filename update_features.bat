@echo off
REM ================================================================
REM Feature Store Updater - Co-Piloto Quant
REM ================================================================
REM Atualiza o Feature Store com indicadores complexos
REM Execute diariamente (cron job ou Task Scheduler)
REM ================================================================

echo.
echo ========================================
echo  Feature Store Updater v1.0
echo  Co-Piloto Quant
echo ========================================
echo.

REM Ativa ambiente virtual
echo [1/3] Ativando ambiente virtual...
call "%~dp0co-piloto-quant\vbt_env\Scripts\activate.bat"

if %errorlevel% neq 0 (
    echo ERRO: Nao foi possivel ativar o ambiente virtual
    echo Verifique se o venv existe em: co-piloto-quant\vbt_env\
    pause
    exit /b 1
)

REM Navega para o diretório correto
cd /d "%~dp0co-piloto-quant"

echo [2/3] Construindo Feature Store...
echo Calculando indicadores complexos para todas as acoes...
echo.

REM Executa o script de build
python scripts\build_feature_store.py --workers 4

if %errorlevel% neq 0 (
    echo.
    echo ERRO: Falha ao construir Feature Store
    echo Verifique os logs em: co-piloto-quant\logs\feature_store.log
    pause
    exit /b 1
)

echo.
echo [3/3] Feature Store atualizado com sucesso!
echo.
echo ========================================
echo  Proximos passos:
echo ========================================
echo  1. Inicie a API: python ..\api_backend.py
echo  2. Acesse: http://localhost:8001/api/health
echo  3. Verifique "feature_store.enabled = true"
echo ========================================
echo.

pause
