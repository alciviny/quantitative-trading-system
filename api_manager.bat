@echo off
REM ================================================================
REM API Manager - Co-Piloto Quant
REM Gerencia a API (start/stop/status/restart)
REM ================================================================

setlocal enabledelayedexpansion

if "%1"=="" goto show_help
if "%1"=="help" goto show_help
if "%1"=="status" goto check_status
if "%1"=="start" goto start_api
if "%1"=="stop" goto stop_api
if "%1"=="restart" goto restart_api
if "%1"=="test" goto test_api

:show_help
echo.
echo ========================================
echo  API Manager - Co-Piloto Quant
echo ========================================
echo.
echo Uso: api_manager.bat [comando]
echo.
echo Comandos:
echo   status   - Verifica se a API esta rodando
echo   start    - Inicia a API
echo   stop     - Para a API
echo   restart  - Reinicia a API
echo   test     - Testa a API (health check)
echo   help     - Mostra esta ajuda
echo.
goto end

:check_status
echo.
echo Verificando status da API...
echo.

REM Verifica se a porta 8001 esta em uso
netstat -ano | findstr ":8001" >nul 2>&1
if %errorlevel% equ 0 (
    echo ✅ API esta RODANDO
    echo.
    echo Processos na porta 8001:
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001"') do (
        set PID=%%a
        echo    PID: !PID!
        tasklist /FI "PID eq !PID!" /FO TABLE /NH 2>nul
    )
    echo.
    echo Para parar: api_manager.bat stop
    echo Para testar: api_manager.bat test
) else (
    echo ❌ API NAO esta rodando
    echo.
    echo Para iniciar: api_manager.bat start
)
echo.
goto end

:start_api
echo.
echo Iniciando API...
echo.

REM Verifica se ja esta rodando
netstat -ano | findstr ":8001" >nul 2>&1
if %errorlevel% equ 0 (
    echo ⚠️  API ja esta rodando!
    echo Use 'api_manager.bat restart' para reiniciar
    echo.
    goto end
)

REM Ativa ambiente virtual e inicia API
cd /d "%~dp0"
call "co-piloto-quant\vbt_env\Scripts\activate.bat"

echo Iniciando em background...
start /B python api_backend.py > logs\api.log 2>&1

REM Aguarda 3 segundos
timeout /t 3 /nobreak >nul

REM Verifica se iniciou
netstat -ano | findstr ":8001" >nul 2>&1
if %errorlevel% equ 0 (
    echo.
    echo ✅ API iniciada com sucesso!
    echo.
    echo 🌐 URL: http://localhost:8001
    echo 📖 Docs: http://localhost:8001/docs
    echo 📝 Logs: logs\api.log
    echo.
    echo Para parar: api_manager.bat stop
) else (
    echo.
    echo ❌ Falha ao iniciar API
    echo Verifique logs\api.log para detalhes
    echo.
)
goto end

:stop_api
echo.
echo Parando API...
echo.

REM Encontra e mata processos na porta 8001
set FOUND=0
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001"') do (
    set PID=%%a
    echo Parando processo !PID!...
    taskkill /PID !PID! /F >nul 2>&1
    set FOUND=1
)

if !FOUND! equ 1 (
    echo.
    echo ✅ API parada com sucesso!
) else (
    echo.
    echo ⚠️  Nenhuma API rodando na porta 8001
)
echo.
goto end

:restart_api
echo.
echo Reiniciando API...
call :stop_api
timeout /t 2 /nobreak >nul
call :start_api
goto end

:test_api
echo.
echo Testando API...
echo.

REM Verifica se esta rodando
netstat -ano | findstr ":8001" >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ API nao esta rodando
    echo.
    echo Para iniciar: api_manager.bat start
    goto end
)

REM Testa health check
echo 📡 GET http://localhost:8001/api/health
echo.

curl -s http://localhost:8001/api/health 2>nul | python -m json.tool 2>nul

if %errorlevel% equ 0 (
    echo.
    echo ✅ API respondendo corretamente!
) else (
    echo ⚠️  API nao respondeu ou erro no formato
)
echo.

goto end

:end
endlocal
