# apps/event_monitoring/services/announcement_monitor.py
from datetime import datetime, timedelta
from typing import Any, Dict, List

from celery import shared_task
from apps.event_monitoring.tasks import send_trading_alert, trigger_immediate_analysis
from core.interfaces.scraping_interfaces import EventMonitorInterface


class OrderAnnouncementMonitor(EventMonitorInterface):
    """Single responsibility: Monitor order/contract announcements"""
    
    def __init__(self):
        self.rss_url = "https://nsearchives.nseindia.com/content/RSS/Online_announcements.xml"
        self.positive_signals = [
            "bagging/receiving of orders/contracts",
            "updates", 
            "spurt in volume"
        ]
    
    def get_recent_order_announcements(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get order announcements from last N hours"""
        announcements = self._fetch_rss_announcements()
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        recent_orders = []
        for announcement in announcements:
            announcement_time = self._parse_announcement_date(announcement['Date'])
            if announcement_time >= cutoff_time:
                recent_orders.append({
                    'company': announcement['Company'],
                    'subject': announcement['Subject'],
                    'description': announcement['Description'],
                    'timestamp': announcement_time,
                    'trading_impact': self._assess_trading_impact(announcement)
                })
        
        return recent_orders
    
    def _assess_trading_impact(self, announcement: Dict[str, Any]) -> str:
        """Assess potential trading impact of announcement"""
        description = announcement['Description'].lower()
        
        if any(word in description for word in ['billion', 'crore', 'large order']):
            return 'HIGH'
        elif any(word in description for word in ['million', 'contract', 'project']):
            return 'MEDIUM'
        else:
            return 'LOW'

# Real-time alert system
@shared_task
def monitor_breaking_announcements():
    """Monitor for breaking order announcements"""
    monitor = OrderAnnouncementMonitor()
    recent_orders = monitor.get_recent_order_announcements(hours_back=1)
    
    for order in recent_orders:
        if order['trading_impact'] in ['HIGH', 'MEDIUM']:
            # Trigger immediate fundamental re-analysis
            trigger_immediate_analysis.delay(order['company'])
            
            # Send alert to trading system
            send_trading_alert(
                symbol=order['company'],
                event_type='ORDER_ANNOUNCEMENT',
                impact=order['trading_impact'],
                details=order['description']
            )
