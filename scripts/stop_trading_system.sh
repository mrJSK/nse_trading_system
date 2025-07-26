# scripts/stop_trading_system.sh
#!/bin/bash

echo "🛑 Stopping NSE Trading System..."

# Kill Celery processes
pkill -f "celery.*worker"
pkill -f "celery.*beat"
pkill -f "celery.*flower"

# Kill Django process
pkill -f "manage.py runserver"

# Remove PID files
rm -f celery_*.pid

echo "✅ All services stopped"
