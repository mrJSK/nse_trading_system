import os
import logging
from time import timezone
from celery import Celery
from celery.schedules import crontab  # ✅ Fixed: Import first
from celery.signals import after_setup_logger, worker_ready, worker_shutdown
from django.conf import settings

# Configure logging
logger = logging.getLogger('celery')

# Set the default Django settings module for the 'celery' program
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app with enhanced configuration
app = Celery('nse_trading_system')

# Load configuration from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks from all registered Django apps
app.autodiscover_tasks()

# ✅ Enhanced Celery Configuration
app.conf.update(
    # Task routing and queues
    task_routes={
        'core.master_trading_orchestrator': {'queue': 'trading'},
        'core.fetch_live_market_data': {'queue': 'data_collection'},
        'core.update_company_fundamentals': {'queue': 'data_collection'},
        'core.monitor_market_events': {'queue': 'events'},
        'core.run_comprehensive_analysis': {'queue': 'analysis'},
        'core.generate_trading_signals': {'queue': 'analysis'},
        'core.execute_trading_decisions': {'queue': 'trading'},
        'core.cleanup_old_data': {'queue': 'maintenance'},
    },
    
    # Task execution settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    task_track_started=True,
    task_time_limit=1800,  # 30 minutes
    task_soft_time_limit=1500,  # 25 minutes
    worker_prefetch_multiplier=1,  # Only fetch one task per worker
    
    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour
    result_backend_transport_options={
        'visibility_timeout': 3600,
        'fanout_prefix': True,
        'fanout_patterns': True
    },
    
    # Error handling
    task_reject_on_worker_lost=True,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # Timezone
    timezone='Asia/Kolkata',
    enable_utc=True,
)

# ✅ Dynamic Beat Schedule Based on Market Conditions
def get_dynamic_beat_schedule():
    """Get beat schedule that adapts to market conditions"""
    from datetime import datetime, time
    import pytz
    
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    
    # Base schedule
    schedule = {
        # Master orchestrator - adaptive frequency
        'master-trading-orchestrator': {
            'task': 'core.master_trading_orchestrator',
            'schedule': 180.0 if 9 <= now.hour <= 15 else 600.0,  # 3min during trading, 10min otherwise
            'options': {'queue': 'trading', 'priority': 9}
        },
        
        # Event monitoring - continuous but intelligent
        'monitor-market-events': {
            'task': 'core.monitor_market_events',
            'schedule': 600.0,  # Every 10 minutes
            'options': {'queue': 'events', 'priority': 7}
        },
        
        # Live data - only during trading hours + pre/post market
        'fetch-live-data': {
            'task': 'core.fetch_live_market_data',
            'schedule': 60.0,  # Every minute
            'options': {'queue': 'data_collection', 'priority': 8}
        },
        
        # Fundamental data updates - optimized timing
        'update-fundamentals-morning': {
            'task': 'core.update_company_fundamentals',
            'schedule': crontab(hour=7, minute=30),  # 7:30 AM IST - before market
            'options': {'queue': 'data_collection', 'priority': 6}
        },
        'update-fundamentals-evening': {
            'task': 'core.update_company_fundamentals',
            'schedule': crontab(hour=19, minute=0),  # 7:00 PM IST - after market
            'options': {'queue': 'data_collection', 'priority': 6}
        },
        
        # Analysis tasks - market hours focused
        'comprehensive-analysis': {
            'task': 'core.run_comprehensive_analysis',
            'schedule': crontab(minute='*/15'),  # Every 15 minutes
            'options': {'queue': 'analysis', 'priority': 7}
        },
        
        # Signal generation - frequent during market hours
        'generate-signals': {
            'task': 'core.generate_trading_signals',
            'schedule': 300.0,  # Every 5 minutes
            'options': {'queue': 'analysis', 'priority': 8}
        },
        
        # Risk management - continuous monitoring
        'risk-monitoring': {
            'task': 'core.monitor_portfolio_risk',
            'schedule': 120.0,  # Every 2 minutes
            'options': {'queue': 'trading', 'priority': 9}
        },
        
        # System health checks
        'system-health-check': {
            'task': 'core.system_health_check',
            'schedule': 1800.0,  # Every 30 minutes
            'options': {'queue': 'maintenance', 'priority': 4}
        },
        
        # Daily maintenance
        'daily-cleanup': {
            'task': 'core.cleanup_old_data',
            'schedule': crontab(hour=1, minute=0),  # 1:00 AM IST
            'options': {'queue': 'maintenance', 'priority': 3}
        },
        
        # Weekly deep analysis
        'weekly-portfolio-analysis': {
            'task': 'core.weekly_portfolio_analysis',
            'schedule': crontab(hour=20, minute=0, day_of_week=0),  # Sunday 8 PM
            'options': {'queue': 'analysis', 'priority': 5}
        },
    }
    
    # Disable some tasks during market holidays
    # This would integrate with NSE holiday calendar
    
    return schedule

# Set the dynamic schedule
app.conf.beat_schedule = get_dynamic_beat_schedule()

# ✅ Enhanced Error Handling and Monitoring
@after_setup_logger.connect
def setup_loggers(logger, *args, **kwargs):
    """Setup enhanced logging for better monitoring"""
    import structlog
    
    # Configure structured logging
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

@worker_ready.connect
def worker_ready_handler(sender, **kwargs):
    """Handle worker startup"""
    logger.info("🚀 NSE Trading System Worker Ready", extra={
        'worker_id': sender.hostname,
        'timestamp': timezone.now().isoformat()
    })

@worker_shutdown.connect
def worker_shutdown_handler(sender, **kwargs):
    """Handle worker shutdown"""
    logger.info("🛑 NSE Trading System Worker Shutdown", extra={
        'worker_id': sender.hostname,
        'timestamp': timezone.now().isoformat()
    })

# ✅ Task Retry Configuration
class BaseTaskWithRetry:
    """Base task class with intelligent retry logic"""
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_jitter = True

# Debug task for testing
@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
    return {'status': 'debug_completed', 'worker': self.request.hostname}
