# apps/fundamental_analysis/services/xbrl_analyzer.py
class XBRLFundamentalAnalyzer(AnalyzerInterface):
    """Single responsibility: Analyze XBRL data for fundamental insights"""
    
    def analyze_annual_results(self, xbrl_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract key ratios from XBRL annual results"""
        
        # Extract financial statement data
        income_statement = xbrl_data.get('Income Statement', [])
        balance_sheet = xbrl_data.get('Balance Sheet - Assets', [])
        
        analysis = {}
        
        # Revenue Growth Analysis
        revenue_facts = [f for f in income_statement if f['Concept'] == 'RevenueFromOperations']
        if len(revenue_facts) >= 2:
            current_revenue = revenue_facts[0]['Value']
            previous_revenue = revenue_facts[1]['Value']
            analysis['revenue_growth'] = ((current_revenue - previous_revenue) / previous_revenue) * 100
        
        # Profitability Analysis
        profit_facts = [f for f in income_statement if f['Concept'] == 'ProfitLoss']
        if profit_facts:
            analysis['net_profit_margin'] = (profit_facts[0]['Value'] / revenue_facts[0]['Value']) * 100
        
        # Return on Equity
        equity_facts = [f for f in balance_sheet if f['Concept'] == 'TotalEquity']
        if profit_facts and equity_facts:
            analysis['roe'] = (profit_facts[0]['Value'] / equity_facts[0]['Value']) * 100
        
        return analysis

# Celery task for automated XBRL processing
@shared_task
def process_new_annual_results():
    """Process newly announced annual results"""
    calendar_monitor = NSEEventCalendarMonitor()
    companies_announcing = calendar_monitor.get_companies_announcing_today()
    
    xbrl_processor = XBRLFundamentalAnalyzer()
    
    for company in companies_announcing:
        try:
            # Download and process XBRL for this company
            xbrl_data = download_company_xbrl(company)
            if xbrl_data:
                analysis = xbrl_processor.analyze_annual_results(xbrl_data)
                update_company_fundamental_score(company, analysis)
        except Exception as e:
            logger.error(f"Failed to process XBRL for {company}: {e}")
