# apps/trading_engine/services/intelligent_orchestrator.py
class IntelligentTradingOrchestrator:
    """Orchestrates all data sources for intelligent trading decisions"""
    
    def __init__(self):
        self.calendar_monitor = NSEEventCalendarMonitor()
        self.order_monitor = OrderAnnouncementMonitor()
        self.results_monitor = FinancialResultsMonitor()
        self.fundamental_analyzer = ValueAnalyzer()
        self.technical_analyzer = EFIIndicator()
    
    def execute_intelligent_trading_cycle(self):
        """Enhanced trading cycle using all data sources"""
        
        # 1. Get companies with upcoming events (next 7 days)
        upcoming_events = self.calendar_monitor.get_upcoming_result_dates(7)
        
        # 2. Check for breaking order announcements (last hour)
        breaking_orders = self.order_monitor.get_recent_order_announcements(1)
        
        # 3. Get latest financial results
        latest_results = self.results_monitor.get_latest_results()
        
        # 4. Create prioritized watchlist
        priority_watchlist = self._create_priority_watchlist(
            upcoming_events, breaking_orders, latest_results
        )
        
        # 5. Apply technical analysis only to priority companies
        trading_signals = []
        for company in priority_watchlist:
            # Get latest market data
            market_data = self.get_market_data(company['symbol'])
            
            # Apply EFI analysis
            efi_signal = self.technical_analyzer.generate_signals(market_data)
            
            if efi_signal['action'] == 'BUY':
                signal = TradingSignal(
                    symbol=company['symbol'],
                    action='BUY',
                    confidence=self._calculate_confidence(company, efi_signal),
                    reason=company['event_reason'],
                    data_sources=['fundamental', 'technical', 'event']
                )
                trading_signals.append(signal)
        
        return trading_signals
    
    def _create_priority_watchlist(self, events, orders, results):
        """Create prioritized list based on multiple data sources"""
        priority_companies = []
        
        # High priority: Companies with recent order announcements
        for order in orders:
            if order['trading_impact'] in ['HIGH', 'MEDIUM']:
                priority_companies.append({
                    'symbol': order['company'],
                    'priority': 'HIGH',
                    'event_reason': f"Order announcement: {order['subject']}",
                    'event_type': 'ORDER'
                })
        
        # Medium priority: Companies announcing results in next 3 days
        for company in events['equity_companies'][:20]:  # Top 20
            priority_companies.append({
                'symbol': company,
                'priority': 'MEDIUM',
                'event_reason': "Results due within 3 days",
                'event_type': 'RESULTS'
            })
        
        return priority_companies

# Scheduled tasks coordination
@shared_task
def run_intelligent_trading_cycle():
    """Main trading cycle using all data sources"""
    orchestrator = IntelligentTradingOrchestrator()
    signals = orchestrator.execute_intelligent_trading_cycle()
    
    for signal in signals:
        if signal.confidence > 0.7:  # High confidence threshold
            execute_trade_order.delay(signal)

# Celery beat schedule
app.conf.beat_schedule.update({
    'intelligent-trading-cycle': {
        'task': 'run_intelligent_trading_cycle',
        'schedule': crontab(minute='*/30'),  # Every 30 minutes during market hours
    },
    'monitor-breaking-news': {
        'task': 'monitor_breaking_announcements',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'update-event-calendar': {
        'task': 'update_nse_event_calendar',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    }
})
