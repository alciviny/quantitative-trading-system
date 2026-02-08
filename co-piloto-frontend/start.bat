@echo off
REM ============================================
REM Inicia Frontend em Modo Desenvolvimento
REM ============================================

echo.
echo ========================================
echo   Iniciando Co-Piloto Frontend...
echo ========================================
echo.

if not exist node_modules (
    echo [AVISO] Dependencias nao instaladas!
    echo Execute primeiro: setup.bat
    echo.
    pause
    exit /b 1
)

echo [OK] Iniciando servidor...
echo.
echo Acessivel em: http://localhost:3001
echo Pressione Ctrl+C para parar
echo.

npm run dev
