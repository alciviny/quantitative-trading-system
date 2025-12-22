Write-Host "🚀 Iniciando testes locais..." -ForegroundColor Cyan

Write-Host "`n📋 1. Executando Linting (ruff)..." -ForegroundColor Yellow
ruff check src/ tests/ scripts/
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Aviso: Ruff encontrou problemas" -ForegroundColor Yellow
}

Write-Host "`n🧪 2. Executando Testes (pytest)..." -ForegroundColor Yellow
python -m pytest tests/ -v --tb=short
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Testes falharam!" -ForegroundColor Red
    exit 1
}

Write-Host "`n✅ Todos os testes passaram!" -ForegroundColor Green
Write-Host "🟢 Sistema pronto para commit!" -ForegroundColor Green
