#!/bin/bash
# scripts/start_trading_system.sh

echo "🚀 Starting NSE Trading System..."

# Start Redis
redis-server --daemonize yes

# Start PostgreSQL (if not using Docker)
sudo systemctl start postgresql

# Migrate database
python manage.py migrate

# Create periodic tasks in database
python manage.py shell -c "
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
import json

# Create schedules
interval_5min, _ = IntervalSchedule.objects.get_or_create(every=5, period=IntervalSchedule.MINUTES)
interval_15min, _ = IntervalSchedule.objects.get_or_create(every=15, period=IntervalSchedule.MINUTES)

# Create master orchestrator task
PeriodicTask.objects.get_or_create(
    name='Master Trading Orchestrator',
    task='core.master_trading_orchestrator',
    interval=interval_5min,
    enabled=True
)

print('✅ Periodic tasks created')
"

# Start Celery Worker
celery -A config worker -l info --detach --pidfile=celery_worker.pid

# Start Celery Beat
celery -A config beat -l info --detach --pidfile=celery_beat.pid

# Start Django
python manage.py runserver 0.0.0.0:8000

echo "✅ Trading system is running 24x7!"
echo "📊 Web interface: http://localhost:8000"
echo "🌺 Flower monitoring: http://localhost:5555"
echo "📋 Logs: tail -f celery.log"
