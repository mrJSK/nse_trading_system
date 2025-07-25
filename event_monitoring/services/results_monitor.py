# apps/event_monitoring/services/results_monitor.py
class FinancialResultsMonitor(EventMonitorInterface):
    """Single responsibility: Monitor financial results announcements"""
    
    def __init__(self, selenium_scraper):
        self.selenium_scraper = selenium_scraper
        self.results_url = "https://www.nseindia.com/companies-listing/corporate-filings-financial-results"
    
    def get_latest_results(self) -> List[Dict[str, Any]]:
        """Get latest financial results from NSE"""
        return self.selenium_scraper.scrape_financial_results_page()
    
    def compare_with_estimates(self, company: str, actual_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compare actual results with analyst estimates"""
        estimates = self._get_analyst_estimates(company)
        
        surprise_analysis = {}
        
        if 'revenue' in actual_results and 'revenue_estimate' in estimates:
            revenue_surprise = ((actual_results['revenue'] - estimates['revenue_estimate']) / 
                              estimates['revenue_estimate']) * 100
            surprise_analysis['revenue_surprise_pct'] = revenue_surprise
        
        if 'eps' in actual_results and 'eps_estimate' in estimates:
            eps_surprise = ((actual_results['eps'] - estimates['eps_estimate']) / 
                           estimates['eps_estimate']) * 100
            surprise_analysis['eps_surprise_pct'] = eps_surprise
        
        return surprise_analysis
