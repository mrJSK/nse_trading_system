# scripts/run_trading_system.sh
#!/bin/bash

echo "🚀 Starting NSE Trading System - All Components"
echo "=============================================="

# Set environment variables
export DJANGO_SETTINGS_MODULE=config.settings.development
export PYTHONPATH=$PWD:$PYTHONPATH

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if service is running
check_service() {
    if pgrep -f "$1" > /dev/null; then
        echo -e "${GREEN}✓ $2 is running${NC}"
        return 0
    else
        echo -e "${RED}✗ $2 is not running${NC}"
        return 1
    fi
}

# Function to start service with retry
start_service() {
    echo -e "${YELLOW}Starting $2...${NC}"
    $1 &
    sleep 3
    if check_service "$3" "$2"; then
        echo -e "${GREEN}✓ $2 started successfully${NC}"
    else
        echo -e "${RED}✗ Failed to start $2${NC}"
        exit 1
    fi
}

echo -e "${BLUE}Step 1: Starting Infrastructure Services${NC}"
echo "----------------------------------------"

# Start Redis (if not running)
if ! pgrep redis-server > /dev/null; then
    echo "Starting Redis..."
    redis-server --daemonize yes --port 6379
    sleep 2
fi
check_service "redis-server" "Redis Server"

# Start PostgreSQL (if not running)
if ! pgrep postgres > /dev/null; then
    echo "Starting PostgreSQL..."
    # Windows: net start postgresql-x64-15
    # Linux: sudo systemctl start postgresql
    pg_ctl -D "C:\Program Files\PostgreSQL\15\data" -l logfile start 2>/dev/null || echo "PostgreSQL may already be running"
    sleep 3
fi

echo -e "${BLUE}Step 2: Database Migration & Setup${NC}"
echo "-----------------------------------"

# Run migrations
echo "Running database migrations..."
python manage.py migrate --no-input

# Create superuser if needed (skip if exists)
echo "Checking superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@trading.com', 'admin123')
    print('Superuser created')
else:
    print('Superuser already exists')
" 2>/dev/null

echo -e "${BLUE}Step 3: Starting Core Trading System${NC}"
echo "------------------------------------"

# Start Django development server
start_service "python manage.py runserver 0.0.0.0:8000" "Django Web Server" "runserver"

# Start Celery Worker (Data Collection Queue)
start_service "celery -A config worker -Q data_collection -l info --concurrency=2 --detach --pidfile=celery_data.pid" "Celery Data Worker" "celery.*data_collection"

# Start Celery Worker (Analysis Queue)
start_service "celery -A config worker -Q analysis -l info --concurrency=2 --detach --pidfile=celery_analysis.pid" "Celery Analysis Worker" "celery.*analysis"

# Start Celery Worker (Trading Queue)
start_service "celery -A config worker -Q trading -l info --concurrency=1 --detach --pidfile=celery_trading.pid" "Celery Trading Worker" "celery.*trading"

# Start Celery Worker (Events Queue)
start_service "celery -A config worker -Q events -l info --concurrency=1 --detach --pidfile=celery_events.pid" "Celery Events Worker" "celery.*events"

# Start Celery Beat (Scheduler)
start_service "celery -A config beat -l info --detach --pidfile=celery_beat.pid" "Celery Beat Scheduler" "celery.*beat"

# Start Celery Flower (Monitoring)
start_service "celery -A config flower --port=5555 --detach" "Celery Flower Monitor" "flower"

echo -e "${BLUE}Step 4: System Health Check${NC}"
echo "----------------------------"

# Wait for services to fully start
sleep 10

# Health check
echo "Performing system health check..."
python manage.py shell -c "
import requests
import time
from apps.core.tasks import master_trading_orchestrator

print('Testing Django server...')
try:
    response = requests.get('http://localhost:8000', timeout=5)
    print('✓ Django server responding')
except:
    print('✗ Django server not responding')

print('Testing Celery workers...')
try:
    result = master_trading_orchestrator.delay()
    print('✓ Celery workers responding')
except Exception as e:
    print(f'✗ Celery workers error: {e}')

print('Testing Flower monitoring...')
try:
    response = requests.get('http://localhost:5555', timeout=5)
    print('✓ Flower monitoring available')
except:
    print('✗ Flower monitoring not available')
"

echo -e "${GREEN}=============================================="
echo "🎉 NSE Trading System Started Successfully!"
echo "=============================================="
echo ""
echo "📊 Access Points:"
echo "  • Web Interface: http://localhost:8000"
echo "  • Admin Panel:   http://localhost:8000/admin"
echo "  • Flower Monitor: http://localhost:5555"
echo "  • API Docs:      http://localhost:8000/api/docs/"
echo ""
echo "📋 Service Status:"
check_service "runserver" "Django Web Server"
check_service "celery.*worker" "Celery Workers"
check_service "celery.*beat" "Celery Beat"
check_service "flower" "Celery Flower"
check_service "redis-server" "Redis"
echo ""
echo "📝 Logs:"
echo "  • Django: Terminal output"
echo "  • Celery: celery.log"
echo "  • System: logs/trading_system.log"
echo ""
echo "⏹️ To stop all services: ./scripts/stop_trading_system.sh"
echo -e "${NC}"

# Keep script running to monitor
echo "Press Ctrl+C to stop monitoring (services will continue running)"
while true; do
    sleep 60
    echo -e "${BLUE}[$(date)] System Status Check...${NC}"
    if ! check_service "runserver" "Django" >/dev/null 2>&1; then
        echo -e "${RED}Django server stopped! Restarting...${NC}"
        python manage.py runserver 0.0.0.0:8000 &
    fi
done
