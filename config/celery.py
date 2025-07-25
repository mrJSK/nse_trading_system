# config/celery.py
import os
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('nse_trading_system')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Celery Beat Schedule for 24x7 operation
app.conf.beat_schedule = {
    # Master orchestrator - runs every 5 minutes during trading hours
    'master-trading-orchestrator': {
        'task': 'core.master_trading_orchestrator',
        'schedule': 300.0,  # Every 5 minutes
    },
    
    # Event monitoring - runs every 15 minutes (24x7)
    'monitor-market-events': {
        'task': 'core.monitor_market_events',
        'schedule': 900.0,  # Every 15 minutes
    },
    
    # Fundamental data update - runs twice daily
    'update-fundamentals-morning': {
        'task': 'core.update_company_fundamentals',
        'schedule': crontab(hour=8, minute=0),  # 8:00 AM IST
    },
    'update-fundamentals-evening': {
        'task': 'core.update_company_fundamentals',
        'schedule': crontab(hour=18, minute=0),  # 6:00 PM IST
    },
    
    # Live data fetching - every 2 minutes during trading hours
    'fetch-live-data': {
        'task': 'core.fetch_live_market_data',
        'schedule': 120.0,  # Every 2 minutes
    },
    
    # Daily cleanup - runs at midnight
    'daily-cleanup': {
        'task': 'core.cleanup_old_data',
        'schedule': crontab(hour=0, minute=0),  # Midnight
    },
}

app.conf.timezone = 'Asia/Kolkata'

from celery.schedules import crontab
