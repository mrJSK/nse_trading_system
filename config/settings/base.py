# config/settings/base.py
import os
from pathlib import Path
import sys
from celery.schedules import crontab

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-22jiry@^0vuaqhqo%2r5ki=*i_+p4v&czh!&*74ge$5^j!5y_v')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'corsheaders',
    'celery',
    'django_celery_beat',
    'django_celery_results',

    # Your apps
    'apps.core',
    'apps.market_data_service',
    'apps.fundamental_analysis',
    'apps.technical_analysis',
    'apps.trading_engine',
    'apps.event_monitoring',
    'apps.dashboard',
    'apps.portfolio',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'nse_trading_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',},
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# Static files configuration
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',  # Global static files
]

# Make sure you have the correct directory structure
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ✅ Fyers API Configuration
FYERS_APP_ID = os.getenv('FYERS_APP_ID')
FYERS_SECRET_KEY = os.getenv('FYERS_SECRET_KEY')
FYERS_REDIRECT_URI = os.getenv('FYERS_REDIRECT_URI', 'http://127.0.0.1:5000/fyers/callback')

# ✅ Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Asia/Kolkata'
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# ✅ Celery Task Routing
CELERY_TASK_ROUTES = {
    'apps.market_data_service.tasks.*': {'queue': 'data_collection'},
    'apps.technical_analysis.tasks.*': {'queue': 'analysis'},
    'apps.trading_engine.tasks.*': {'queue': 'trading'},
    'apps.event_monitoring.tasks.*': {'queue': 'events'},
}

# ✅ Celery Beat Schedule for NSE Trading System
CELERY_BEAT_SCHEDULE = {
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
    
    # ✅ Your new intelligent market analysis task
    'intelligent-market-analysis': {
        'task': 'execute_intelligent_market_analysis',
        'schedule': crontab(hour=10, minute=0),  # 10 AM daily
    },
    
    # ✅ Your new market data refresh task
    'market-data-refresh': {
        'task': 'refresh_priority_companies_data',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes during market hours
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

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "https://your-trading-dashboard.com",
    "http://localhost:3000",  # For development frontend
]

# REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100,
}

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'trading_system.log',
            'formatter': 'verbose',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
    'loggers': {
        'apps': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
