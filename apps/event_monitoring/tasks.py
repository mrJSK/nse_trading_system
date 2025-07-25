# apps/event_monitoring/tasks.py
from celery import shared_task
from typing import Dict, Any
import logging
from django.utils import timezone

from apps.event_monitoring.services.notification_service import TradingNotificationService, send_high_priority_alert

logger = logging.getLogger(__name__)

@shared_task
def trigger_immediate_analysis(symbol: str) -> Dict[str, Any]:
    """Trigger immediate fundamental analysis for a company"""
    try:
        logger.info(f"Triggering immediate analysis for {symbol} due to event")
        
        # Import here to avoid circular imports
        from ..trading_engine.services.market_data_orchestrator import IntelligentMarketDataOrchestrator
        
        # Create orchestrator and analyze the specific company
        orchestrator = IntelligentMarketDataOrchestrator()
        
        # Add the company to high-priority list
        result = orchestrator._analyze_single_company_with_fyers_data(symbol)
        
        if result and 'error' not in result:
            logger.info(f"✅ Successfully triggered analysis for {symbol}")
            
            # Check if analysis generated strong signals
            recommendation = result.get('recommendation', {})
            if recommendation.get('action') in ['BUY', 'STRONG_BUY'] and recommendation.get('confidence', 0) >= 0.7:
                # Trigger additional alert for high-confidence signals
                send_high_priority_alert.delay(symbol, result)
            
            return {
                'success': True,
                'symbol': symbol,
                'analysis_result': result,
                'timestamp': timezone.now().isoformat()
            }
        else:
            logger.error(f"❌ Failed to analyze {symbol}: {result.get('error', 'Unknown error')}")
            return {
                'success': False,
                'symbol': symbol,
                'error': result.get('error', 'Analysis failed')
            }
            
    except Exception as e:
        logger.error(f"❌ Error triggering analysis for {symbol}: {e}")
        return {
            'success': False,
            'symbol': symbol,
            'error': str(e)
        }

@shared_task
def send_trading_alert(symbol: str, analysis_result: Dict[str, Any]):
    """Send high-priority alert for strong trading signals"""
    try:
        
        notification_service = TradingNotificationService()
        
        # Send immediate alert
        notification_service.send_urgent_signal_alert(symbol, analysis_result)
        
        logger.info(f"✅ Sent high-priority alert for {symbol}")
        
    except Exception as e:
        logger.error(f"❌ Error sending high-priority alert for {symbol}: {e}")
