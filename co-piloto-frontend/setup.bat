@echo off
REM ============================================
REM Script de Setup - Co-Piloto Frontend
REM ============================================

echo.
echo ========================================
echo   CO-PILOTO QUANT - FRONTEND SETUP
echo ========================================
echo.

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
echo   Instalando dependencias...
echo ========================================
echo.

call npm install

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha na instalacao!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Instalacao concluida!
echo ========================================
echo.
echo Para executar o frontend:
echo   npm run dev
echo.
echo O frontend estara disponivel em:
echo   http://localhost:3001
echo.
pause
