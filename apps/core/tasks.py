# apps/core/tasks.py
from celery import shared_task, group, chain
from celery.utils.log import get_task_logger
from django.utils import timezone
from typing import Dict, Any
import time
from apps.fundamental_analysis import models
logger = get_task_logger(__name__)

@shared_task(bind=True, name='core.master_trading_orchestrator')
def master_trading_orchestrator(self) -> Dict[str, Any]:
    """🚀 Master 24x7 Trading System Orchestrator"""
    
    start_time = timezone.now()
    logger.info("🚀 Starting Master Trading Orchestrator at %s", start_time)
    
    try:
        # Check if markets are open (Indian trading hours: 9:15 AM - 3:30 PM IST)
        current_hour = timezone.now().hour
        current_minute = timezone.now().minute
        is_trading_hours = (9 <= current_hour < 15) or (current_hour == 15 and current_minute <= 30)
        is_premarket = (current_hour == 9 and current_minute < 15)
        
        execution_plan = {
            'execution_id': f"exec_{int(time.time())}",
            'start_time': start_time.isoformat(),
            'market_session': 'TRADING' if is_trading_hours else 'PREMARKET' if is_premarket else 'CLOSED',
            'tasks_executed': [],
            'results': {}
        }
        
        # 🔄 CONTINUOUS DATA PIPELINE
        data_pipeline = chain(
            # Step 1: Update company fundamentals (daily)
            update_company_fundamentals.s(),
            
            # Step 2: Monitor events and announcements
            monitor_market_events.s(),
            
            # Step 3: Fetch latest market data from Fyers
            fetch_live_market_data.s(),
            
            # Step 4: Run comprehensive analysis
            run_comprehensive_analysis.s(),
            
            # Step 5: Generate trading signals
            generate_trading_signals.s(),
            
            # Step 6: Execute trades (if market is open)
            execute_trading_decisions.s() if is_trading_hours else None
        )
        
        # Execute the pipeline
        if is_trading_hours or is_premarket:
            result = data_pipeline.apply_async()
            execution_plan['pipeline_result'] = result.id
            logger.info("✅ Full trading pipeline initiated: %s", result.id)
        else:
            # After market hours - run data collection and analysis only
            after_hours_tasks = group(
                update_company_fundamentals.s(),
                monitor_market_events.s(),
                cleanup_old_data.s()
            )
            result = after_hours_tasks.apply_async()
            execution_plan['after_hours_result'] = result.id
            logger.info("✅ After-hours data collection initiated: %s", result.id)
        
        return execution_plan
        
    except Exception as e:
        logger.error("❌ Master orchestrator failed: %s", e)
        return {'error': str(e), 'timestamp': timezone.now().isoformat()}

@shared_task(name='core.update_company_fundamentals')
def update_company_fundamentals() -> Dict[str, Any]:
    """📊 Update fundamental data from multiple sources"""
    
    from apps.market_data_service.services.scrapers import ScreenerWebScraper
    from apps.fundamental_analysis.services.unified_processor import UnifiedResultsProcessor
    from apps.market_data_service.models import Company
    
    try:
        logger.info("📊 Starting fundamental data update...")
        
        # Get companies that need updates (last updated > 1 day ago or never)
        stale_companies = Company.objects.filter(
            models.Q(last_scraped__lt=timezone.now() - timezone.timedelta(days=1)) |
            models.Q(last_scraped__isnull=True)
        ).order_by('scraping_priority')[:50]  # Top 50 priority companies
        
        processor = UnifiedResultsProcessor()
        results = {
            'companies_processed': 0,
            'successful_updates': 0,
            'errors': []
        }
        
        for company in stale_companies:
            try:
                # Process using unified processor (XBRL + Quarterly + Screener)
                result = processor.process_company_by_announcement_type(company.symbol)
                
                if result['success']:
                    results['successful_updates'] += 1
                    logger.info("✅ Updated fundamentals for %s", company.symbol)
                else:
                    results['errors'].append(f"{company.symbol}: {result.get('error', 'Unknown error')}")
                
                results['companies_processed'] += 1
                
                # Rate limiting
                time.sleep(2)
                
            except Exception as e:
                results['errors'].append(f"{company.symbol}: {str(e)}")
                logger.error("❌ Error updating %s: %s", company.symbol, e)
        
        logger.info("📊 Fundamental update completed: %d/%d successful", 
                   results['successful_updates'], results['companies_processed'])
        
        return results
        
    except Exception as e:
        return {'error': str(e), 'task': 'update_company_fundamentals'}

@shared_task(name='core.monitor_market_events')
def monitor_market_events() -> Dict[str, Any]:
    """📅 Monitor NSE events, announcements, and order feeds"""
    
    from apps.event_monitoring.services.calendar_monitor import NSEEventCalendarMonitor
    from apps.event_monitoring.services.announcement_monitor import OrderAnnouncementMonitor
    from apps.event_monitoring.services.quarterly_scraper import NSEQuarterlyResultsScraper
    
    try:
        logger.info("📅 Starting market events monitoring...")
        
        results = {
            'upcoming_events': 0,
            'new_announcements': 0,
            'quarterly_results': 0,
            'high_impact_events': []
        }
        
        # 1. NSE Event Calendar
        calendar_monitor = NSEEventCalendarMonitor()
        upcoming_events = calendar_monitor.get_upcoming_events(days_ahead=7)
        results['upcoming_events'] = len(upcoming_events.get('equity_companies', [])) + len(upcoming_events.get('sme_companies', []))
        
        # 2. Order Announcements (RSS)
        announcement_monitor = OrderAnnouncementMonitor()
        recent_announcements = announcement_monitor.get_recent_order_announcements(hours_back=4)
        results['new_announcements'] = len(recent_announcements)
        
        # Process high-impact announcements immediately
        for announcement in recent_announcements:
            if announcement['trading_impact'] in ['HIGH', 'MEDIUM']:
                results['high_impact_events'].append({
                    'company': announcement['company'],
                    'impact': announcement['trading_impact'],
                    'description': announcement['description'][:100]
                })
                
                # Trigger immediate analysis for high-impact events
                from apps.event_monitoring.tasks import trigger_immediate_analysis
                trigger_immediate_analysis.delay(announcement['company'])
        
        # 3. Quarterly Results Monitoring
        quarterly_scraper = NSEQuarterlyResultsScraper()
        # This would be implemented to check for new quarterly results
        
        logger.info("📅 Event monitoring completed: %d events, %d announcements", 
                   results['upcoming_events'], results['new_announcements'])
        
        return results
        
    except Exception as e:
        return {'error': str(e), 'task': 'monitor_market_events'}

@shared_task(name='core.fetch_live_market_data')
def fetch_live_market_data() -> Dict[str, Any]:
    """📈 Fetch latest market data from Fyers API"""
    
    from apps.trading_engine.services.market_data_orchestrator import IntelligentMarketDataOrchestrator
    
    try:
        logger.info("📈 Fetching live market data from Fyers...")
        
        orchestrator = IntelligentMarketDataOrchestrator()
        
        # Get priority companies for live data
        priority_companies = orchestrator.get_priority_companies_for_analysis()[:30]  # Top 30
        
        if not priority_companies:
            return {'message': 'No priority companies identified', 'data_points': 0}
        
        # Fetch live data for priority companies
        from apps.market_data_service.services.fyers_collector import FyersDataCollector
        fyers_collector = FyersDataCollector()
        
        live_data = fyers_collector.get_multiple_quotes(priority_companies)
        
        # Store in cache for immediate use
        from django.core.cache import cache
        cache.set('live_market_data', live_data, timeout=300)  # 5 minutes cache
        
        logger.info("📈 Live data fetched for %d companies", len(live_data))
        
        return {
            'companies_updated': len(live_data),
            'priority_companies': priority_companies,
            'market_data_timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e), 'task': 'fetch_live_market_data'}

@shared_task(name='core.run_comprehensive_analysis')
def run_comprehensive_analysis() -> Dict[str, Any]:
    """🧠 Run comprehensive fundamental + technical analysis"""
    
    from apps.trading_engine.services.market_data_orchestrator import IntelligentMarketDataOrchestrator
    
    try:
        logger.info("🧠 Starting comprehensive analysis...")
        
        orchestrator = IntelligentMarketDataOrchestrator()
        
        # Execute comprehensive analysis on priority companies
        analysis_results = orchestrator.execute_comprehensive_analysis()
        
        logger.info("🧠 Analysis completed: %d companies analyzed, %d successful", 
                   analysis_results.get('companies_analyzed', 0),
                   analysis_results.get('successful_analyses', 0))
        
        # Store results in cache for signal generation
        from django.core.cache import cache
        cache.set('latest_analysis_results', analysis_results, timeout=1800)  # 30 minutes
        
        return analysis_results
        
    except Exception as e:
        return {'error': str(e), 'task': 'run_comprehensive_analysis'}

@shared_task(name='core.generate_trading_signals')
def generate_trading_signals() -> Dict[str, Any]:
    """📊 Generate actionable trading signals"""
    
    from django.core.cache import cache
    from apps.market_data_service.models import TradingSignal, Company
    
    try:
        logger.info("📊 Generating trading signals...")
        
        # Get latest analysis results
        analysis_results = cache.get('latest_analysis_results', {})
        detailed_results = analysis_results.get('detailed_results', {})
        
        signals_generated = 0
        high_confidence_signals = []
        
        for symbol, analysis in detailed_results.items():
            if 'error' in analysis:
                continue
            
            recommendation = analysis.get('recommendation', {})
            action = recommendation.get('action', 'HOLD')
            confidence = recommendation.get('confidence', 0.0)
            
            if action in ['BUY', 'STRONG_BUY'] and confidence >= 0.6:
                # Create trading signal
                try:
                    company = Company.objects.get(symbol=symbol)
                    
                    signal = TradingSignal.objects.create(
                        company=company,
                        signal_type='composite',
                        action=action,
                        confidence=confidence,
                        price_at_signal=analysis.get('live_market_data', {}).get('ltp', 0),
                        target_price=recommendation.get('target_price'),
                        stop_loss=recommendation.get('stop_loss'),
                        data_sources=['fundamental', 'technical', 'event'],
                        signal_reasons=recommendation.get('reasons', []),
                        urgency=recommendation.get('urgency', 'MEDIUM')
                    )
                    
                    signals_generated += 1
                    
                    if confidence >= 0.8:
                        high_confidence_signals.append({
                            'symbol': symbol,
                            'action': action,
                            'confidence': confidence,
                            'price': signal.price_at_signal
                        })
                    
                except Company.DoesNotExist:
                    logger.warning("Company %s not found for signal generation", symbol)
        
        logger.info("📊 Generated %d trading signals, %d high-confidence", 
                   signals_generated, len(high_confidence_signals))
        
        return {
            'signals_generated': signals_generated,
            'high_confidence_signals': high_confidence_signals,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e), 'task': 'generate_trading_signals'}

@shared_task(name='core.execute_trading_decisions')
def execute_trading_decisions() -> Dict[str, Any]:
    """💰 Execute trading decisions (only during market hours)"""
    
    from apps.market_data_service.models import TradingSignal
    from apps.portfolio.services.portfolio_manager import PortfolioManager
    
    try:
        logger.info("💰 Executing trading decisions...")
        
        # Get unexecuted high-confidence signals
        pending_signals = TradingSignal.objects.filter(
            is_executed=False,
            confidence__gte=0.7,
            action__in=['BUY', 'STRONG_BUY'],
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        ).order_by('-confidence')[:5]  # Top 5 signals
        
        if not pending_signals.exists():
            return {'message': 'No high-confidence signals to execute', 'trades': 0}
        
        # Initialize portfolio manager (you'll need to configure account)
        portfolio_manager = PortfolioManager('YOUR_TRADING_ACCOUNT_ID')
        
        executed_trades = 0
        trade_results = []
        
        for signal in pending_signals:
            try:
                # Execute the signal
                execution_result = portfolio_manager.execute_signal(signal)
                
                if execution_result.get('success'):
                    signal.is_executed = True
                    signal.execution_price = execution_result.get('price')
                    signal.execution_date = timezone.now()
                    signal.save()
                    
                    executed_trades += 1
                    trade_results.append({
                        'symbol': signal.company.symbol,
                        'action': signal.action,
                        'price': execution_result.get('price'),
                        'quantity': execution_result.get('position_size')
                    })
                    
                    logger.info("✅ Executed trade: %s %s at ₹%.2f", 
                               signal.action, signal.company.symbol, 
                               execution_result.get('price', 0))
                
            except Exception as e:
                logger.error("❌ Failed to execute signal for %s: %s", 
                           signal.company.symbol, e)
        
        logger.info("💰 Trading execution completed: %d trades executed", executed_trades)
        
        return {
            'trades_executed': executed_trades,
            'trade_details': trade_results,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e), 'task': 'execute_trading_decisions'}

@shared_task(name='core.cleanup_old_data')
def cleanup_old_data() -> Dict[str, Any]:
    """🧹 Cleanup old data and maintain system health"""
    
    from apps.market_data_service.models import TradingSignal, MarketDataCache
    from django.core.cache import cache
    
    try:
        logger.info("🧹 Starting data cleanup...")
        
        # Clean old trading signals (older than 30 days)
        old_signals_count = TradingSignal.objects.filter(
            created_at__lt=timezone.now() - timezone.timedelta(days=30)
        ).count()
        
        TradingSignal.objects.filter(
            created_at__lt=timezone.now() - timezone.timedelta(days=30)
        ).delete()
        
        # Clean expired cache entries
        expired_cache_count = MarketDataCache.objects.filter(
            expires_at__lt=timezone.now()
        ).count()
        
        MarketDataCache.objects.filter(
            expires_at__lt=timezone.now()
        ).delete()
        
        # Clear old Django cache
        cache.clear()
        
        logger.info("🧹 Cleanup completed: %d old signals, %d cache entries removed", 
                   old_signals_count, expired_cache_count)
        
        return {
            'old_signals_removed': old_signals_count,
            'cache_entries_removed': expired_cache_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        return {'error': str(e), 'task': 'cleanup_old_data'}
