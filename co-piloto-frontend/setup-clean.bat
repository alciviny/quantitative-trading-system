@echo off
REM ============================================
REM Setup Limpo - Co-Piloto Frontend
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Co-Piloto Frontend - Instalacao
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

REM Limpar instalações anteriores
if exist "node_modules" (
    echo [1/3] Removendo node_modules anterior...
    rmdir /s /q node_modules
    if exist "package-lock.json" del package-lock.json
    echo [OK] Limpeza completa
    echo.
)

REM Instalar dependências
echo [2/3] Instalando dependências...
echo Isso pode demorar alguns minutos...
echo.
call npm install

if %errorlevel% neq 0 (
    echo.
    echo [ERRO] Falha na instalacao!
    pause
    exit /b 1
)

echo.
echo [OK] Dependencias instaladas com sucesso!
echo.
echo [3/3] Pronto para desenvolver!
echo.
echo Para iniciar o servidor:
echo   npm run dev
echo.
echo Frontend estara disponivel em:
echo   http://localhost:3001
echo.
pause
