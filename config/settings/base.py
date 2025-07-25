# config/settings/base.py (additions)

# Fyers API Configuration
FYERS_APP_ID = os.getenv('FYERS_APP_ID')
FYERS_SECRET_KEY = os.getenv('FYERS_SECRET_KEY')
FYERS_REDIRECT_URI = os.getenv('FYERS_REDIRECT_URI', 'http://127.0.0.1:5000/fyers/callback')

# Celery Beat Schedule for Market Data
CELERY_BEAT_SCHEDULE.update({
    'intelligent-market-analysis': {
        'task': 'execute_intelligent_market_analysis',
        'schedule': crontab(hour=10, minute=0),  # 10 AM daily
    },
    'market-data-refresh': {
        'task': 'refresh_priority_companies_data',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes during market hours
    },
})
