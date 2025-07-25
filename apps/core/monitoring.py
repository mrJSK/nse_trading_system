# apps/core/monitoring.py
from time import timezone
from celery import shared_task
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

@shared_task(name='core.system_health_check')
def system_health_check():
    """Monitor system health and send alerts"""
    
    from apps.market_data_service.services.fyers_collector import FyersDataCollector
    from django.core.cache import cache
    
    health_report = {
        'timestamp': timezone.now().isoformat(),
        'fyers_api': False,
        'database': False,
        'cache': False,
        'alerts': []
    }
    
    # Check Fyers API
    try:
        fyers_collector = FyersDataCollector()
        health_report['fyers_api'] = fyers_collector.is_connected()
    except:
        health_report['alerts'].append('Fyers API connection failed')
    
    # Check cache
    try:
        cache.set('health_check', 'ok', timeout=60)
        health_report['cache'] = cache.get('health_check') == 'ok'
    except:
        health_report['alerts'].append('Cache system failed')
    
    # Send alerts if issues found
    if health_report['alerts']:
        send_system_alert(health_report)
    
    return health_report

def send_system_alert(health_report):
    """Send system alerts via email/Slack"""
    
    alert_message = f"""
    🚨 NSE Trading System Alert
    
    Issues detected:
    {chr(10).join(health_report['alerts'])}
    
    System Status:
    - Fyers API: {'✅' if health_report['fyers_api'] else '❌'}
    - Cache: {'✅' if health_report['cache'] else '❌'}
    
    Time: {health_report['timestamp']}
    """
    
    # Send email alert
    send_mail(
        'NSE Trading System Alert',
        alert_message,
        'trading-system@yourcompany.com',
        ['admin@yourcompany.com'],
        fail_silently=False,
    )
    
    # You can also integrate Slack, Discord, or SMS alerts here
    logger.critical("🚨 System alert sent: %s", health_report['alerts'])
