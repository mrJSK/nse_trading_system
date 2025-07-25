# apps/event_monitoring/services/calendar_scraper.py
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from core.interfaces.scraping_interfaces import EventMonitorInterface

class NSEEventCalendarMonitor(EventMonitorInterface):
    """Single responsibility: Monitor NSE event calendar for result dates"""
    
    def __init__(self, selenium_driver_factory):
        self.driver_factory = selenium_driver_factory
        self.download_dir = "nse_event_csv_downloads"
    
    def get_upcoming_result_dates(self, days_ahead: int = 30) -> Dict[str, List[str]]:
        """Get companies with results in next N days"""
        equity_dates = self._download_and_parse_equity_events()
        sme_dates = self._download_and_parse_sme_events()
        
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        return {
            'equity_companies': [
                company for company, date in equity_dates.items()
                if self._parse_date(date) <= cutoff_date
            ],
            'sme_companies': [
                company for company, date in sme_dates.items()
                if self._parse_date(date) <= cutoff_date
            ]
        }
    
    def get_companies_announcing_today(self) -> List[str]:
        """Get companies announcing results today"""
        today = datetime.now().date()
        upcoming = self.get_upcoming_result_dates(days_ahead=1)
        
        return [
            company for company_list in upcoming.values()
            for company in company_list
        ]

# Integration with your existing scraper
class IntelligentScrapingOrchestrator(ScrapingOrchestratorInterface):
    """Enhanced orchestrator that uses event calendar for targeted scraping"""
    
    def __init__(self, scraper, parser, storage, calendar_monitor):
        super().__init__(scraper, parser, storage)
        self.calendar_monitor = calendar_monitor
    
    def scrape_upcoming_results_companies(self) -> Dict[str, Any]:
        """Scrape only companies with upcoming results"""
        upcoming_companies = self.calendar_monitor.get_upcoming_result_dates()
        
        # Combine equity and SME companies
        companies_to_scrape = (
            upcoming_companies['equity_companies'] + 
            upcoming_companies['sme_companies']
        )
        
        logger.info(f"Intelligent scraping: {len(companies_to_scrape)} companies with upcoming results")
        
        return self._scrape_company_list(companies_to_scrape)
