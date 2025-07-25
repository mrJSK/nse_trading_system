# apps/event_monitoring/services/notification_service.py
from typing import Dict, Any, List
import logging
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class TradingNotificationService:
    """Handle all trading-related notifications"""
    
    def __init__(self):
        self.notification_channels = ['console', 'database']  # Add 'email', 'slack', etc. as needed
    
    def send_trading_alert(self, symbol: str, event_type: str, impact: str, details: str) -> bool:
        """Send trading alert for events"""
        try:
            alert_data = {
                'symbol': symbol,
                'event_type': event_type,
                'impact_level': impact,
                'details': details,
                'timestamp': timezone.now(),
                'alert_type': 'EVENT_DRIVEN'
            }
            
            # Log to console
            self._log_alert(alert_data)
            
            # Store in database
            self._store_alert(alert_data)
            
            # Send to external channels if configured
            self._send_external_notifications(alert_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending trading alert for {symbol}: {e}")
            return False
    
    def send_urgent_signal_alert(self, symbol: str, analysis_result: Dict[str, Any]) -> bool:
        """Send urgent alert for high-confidence trading signals"""
        try:
            recommendation = analysis_result.get('recommendation', {})
            
            alert_data = {
                'symbol': symbol,
                'event_type': 'HIGH_CONFIDENCE_SIGNAL',
                'action': recommendation.get('action', 'UNKNOWN'),
                'confidence': recommendation.get('confidence', 0),
                'reasons': recommendation.get('reasons', []),
                'urgency': recommendation.get('urgency', 'HIGH'),
                'timestamp': timezone.now(),
                'alert_type': 'URGENT_SIGNAL'
            }
            
            # Priority logging
            logger.warning(f"🚨 URGENT SIGNAL: {symbol} - {recommendation.get('action')} with {recommendation.get('confidence', 0):.2f} confidence")
            
            # Store in database with high priority
            self._store_alert(alert_data, priority='HIGH')
            
            # Send immediate notifications
            self._send_urgent_notifications(alert_data)
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending urgent signal alert for {symbol}: {e}")
            return False
    
    def _log_alert(self, alert_data: Dict[str, Any]):
        """Log alert to console"""
        symbol = alert_data['symbol']
        event_type = alert_data['event_type']
        impact = alert_data.get('impact_level', alert_data.get('urgency', 'UNKNOWN'))
        
        logger.info(f"📢 TRADING ALERT: {symbol} | {event_type} | Impact: {impact}")
        logger.info(f"   Details: {alert_data.get('details', alert_data.get('reasons', 'No details'))}")
    
    def _store_alert(self, alert_data: Dict[str, Any], priority: str = 'MEDIUM'):
        """Store alert in database"""
        try:
            from ...market_data_service.models import Company
            from ..models import TradingAlert  # We'll create this model
            
            company = Company.objects.get(symbol=alert_data['symbol'])
            
            # Create alert record
            # Note: You'll need to create the TradingAlert model
            # For now, we'll just log this
            logger.info(f"📊 Storing {priority} priority alert for {alert_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Error storing alert: {e}")
    
    def _send_external_notifications(self, alert_data: Dict[str, Any]):
        """Send notifications to external channels"""
        try:
            # Placeholder for external notifications
            # You can add email, Slack, Discord, etc. integrations here
            
            if alert_data.get('impact_level') == 'HIGH' or alert_data.get('urgency') == 'HIGH':
                logger.info(f"📧 Would send external notification for {alert_data['symbol']}")
            
        except Exception as e:
            logger.error(f"Error sending external notifications: {e}")
    
    def _send_urgent_notifications(self, alert_data: Dict[str, Any]):
        """Send urgent notifications through all available channels"""
        try:
            symbol = alert_data['symbol']
            action = alert_data['action']
            confidence = alert_data['confidence']
            
            # Console alert with special formatting
            print("=" * 60)
            print(f"🚨 URGENT TRADING SIGNAL 🚨")
            print(f"Symbol: {symbol}")
            print(f"Action: {action}")
            print(f"Confidence: {confidence:.2%}")
            print(f"Time: {alert_data['timestamp']}")
            print("=" * 60)
            
            # Log with high priority
            logger.critical(f"URGENT: {symbol} signal - {action} at {confidence:.2%} confidence")
            
        except Exception as e:
            logger.error(f"Error sending urgent notifications: {e}")

# Global function for backward compatibility
def send_high_priority_alert(symbol: str, event_type: str, impact: str, details: str) -> bool:
    """Global function to send trading alerts"""
    notification_service = TradingNotificationService()
    return notification_service.send_trading_alert(symbol, event_type, impact, details)
