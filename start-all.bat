@echo off
REM ============================================
REM Script de Inicialização Completa
REM Backend API + Frontend React
REM ============================================

echo.
echo ========================================
echo   CO-PILOTO QUANT - SISTEMA COMPLETO
echo ========================================
echo.

REM Verificar Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Python nao encontrado!
    echo Instale Python 3.9+ de: https://python.org/
    pause
    exit /b 1
)
echo [OK] Python encontrado

REM Verificar npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] npm nao encontrado!
    echo Instale Node.js de: https://nodejs.org/
    pause
    exit /b 1
)
echo [OK] npm encontrado

echo.
echo ========================================
echo   PASSO 1: Ativar ambiente virtual Python
echo ========================================
echo.

REM Verificar se ambiente virtual existe
if exist "co-piloto-quant\vbt_env\Scripts\activate.bat" (
    echo [OK] Ambiente virtual encontrado
    call co-piloto-quant\vbt_env\Scripts\activate.bat
) else (
    echo [AVISO] Ambiente virtual nao encontrado
)

echo.
echo ========================================
echo   PASSO 2: Instalar dependencias Python
echo ========================================
echo.

pip install fastapi uvicorn pyarrow pandas --quiet
if %errorlevel% neq 0 (
    echo [AVISO] Erro ao instalar pacotes Python
)

echo.
echo ========================================
echo   PASSO 3: Instalar dependencias React
echo ========================================
echo.

cd frontend-react
if not exist node_modules (
    echo Instalando dependencias do React - primeira vez...
    call npm install
) else (
    echo [OK] Dependencias React ja instaladas
)
cd ..

echo.
echo ========================================
echo   PASSO 4: Iniciar Backend API
echo ========================================
echo.

start "Co-Piloto API Backend" cmd /k "cd /d "%~dp0" & call co-piloto-quant\vbt_env\Scripts\activate.bat & echo Iniciando API Backend... & python api_backend.py"

REM Aguardar API iniciar
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   PASSO 5: Iniciar Frontend React
echo ========================================
echo.

cd frontend-react
start "Co-Piloto React Frontend" cmd /k "echo Iniciando Frontend React... & npm start"
cd ..

echo.
echo ========================================
echo   SISTEMA INICIALIZADO!
echo ========================================
echo.
echo [1] Backend API: http://localhost:8000
echo     Docs API:    http://localhost:8000/docs
echo.
echo [2] Frontend:    http://localhost:3000
echo.
echo ========================================
echo.
echo Pressione qualquer tecla para abrir o navegador...
pause >nul

REM Abrir navegador automaticamente
start http://localhost:3000

echo.
echo Sistema rodando!
echo Para parar, feche as janelas de terminal abertas.
echo.
pause
