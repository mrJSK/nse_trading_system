# scripts/run_trading_system.ps1
Write-Host "🚀 Starting NSE Trading System - All Components" -ForegroundColor Green
Write-Host "=============================================="

# Set environment variables
$env:DJANGO_SETTINGS_MODULE = "config.settings.development"
$env:PYTHONPATH = "$PWD;$env:PYTHONPATH"

function Test-Service {
    param($ProcessName, $ServiceName)
    if (Get-Process -Name $ProcessName -ErrorAction SilentlyContinue) {
        Write-Host "✓ $ServiceName is running" -ForegroundColor Green
        return $true
    } else {
        Write-Host "✗ $ServiceName is not running" -ForegroundColor Red
        return $false
    }
}

Write-Host "Step 1: Starting Infrastructure Services" -ForegroundColor Blue
Write-Host "----------------------------------------"

# Start Redis (if installed)
if (-not (Test-Service "redis-server" "Redis")) {
    Write-Host "Starting Redis..." -ForegroundColor Yellow
    Start-Process "redis-server" -ArgumentList "--port 6379" -WindowStyle Hidden
    Start-Sleep 3
}

# Start PostgreSQL
Write-Host "Ensuring PostgreSQL is running..."
Start-Service postgresql* -ErrorAction SilentlyContinue

Write-Host "Step 2: Database Setup" -ForegroundColor Blue
Write-Host "----------------------"

# Run migrations
Write-Host "Running database migrations..."
python manage.py migrate --no-input

Write-Host "Step 3: Starting All Services" -ForegroundColor Blue
Write-Host "------------------------------"

# Start Django server
Write-Host "Starting Django server..." -ForegroundColor Yellow
Start-Process python -ArgumentList "manage.py runserver 0.0.0.0:8000" -WindowStyle Normal

# Start Celery workers
Write-Host "Starting Celery workers..." -ForegroundColor Yellow
Start-Process celery -ArgumentList "-A config worker -Q data_collection -l info --concurrency=2" -WindowStyle Minimized
Start-Process celery -ArgumentList "-A config worker -Q analysis -l info --concurrency=2" -WindowStyle Minimized
Start-Process celery -ArgumentList "-A config worker -Q trading -l info --concurrency=1" -WindowStyle Minimized
Start-Process celery -ArgumentList "-A config worker -Q events -l info --concurrency=1" -WindowStyle Minimized

# Start Celery beat
Write-Host "Starting Celery beat scheduler..." -ForegroundColor Yellow
Start-Process celery -ArgumentList "-A config beat -l info" -WindowStyle Minimized

# Start Flower
Write-Host "Starting Flower monitoring..." -ForegroundColor Yellow
Start-Process celery -ArgumentList "-A config flower --port=5555" -WindowStyle Minimized

Write-Host "Waiting for services to start..." -ForegroundColor Yellow
Start-Sleep 15

Write-Host "🎉 NSE Trading System Started!" -ForegroundColor Green
Write-Host "==============================="
Write-Host ""
Write-Host "📊 Access Points:" -ForegroundColor Cyan
Write-Host "  • Web Interface: http://localhost:8000"
Write-Host "  • Admin Panel:   http://localhost:8000/admin"
Write-Host "  • Flower Monitor: http://localhost:5555"
Write-Host ""
Write-Host "Press any key to continue monitoring or Ctrl+C to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
