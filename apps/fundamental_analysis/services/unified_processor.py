# apps/fundamental_analysis/services/unified_processor.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from django.db import transaction
from django.utils import timezone

from core.interfaces.scraping_interfaces import ScrapingResult
from xbrl_processor import NSEXBRLProcessor
from ..services.analyzers import ValueAnalyzer, GrowthAnalyzer
from ...event_monitoring.services.quarterly_scraper import NSEQuarterlyResultsScraper
from ...event_monitoring.services.calendar_monitor import NSEEventCalendarMonitor
from ...market_data_service.models import (
    Company, FinancialStatement, ValuationMetrics, 
    ProfitabilityMetrics, GrowthMetrics, CorporateEvent
)

logger = logging.getLogger(__name__)

class UnifiedResultsProcessor:
    """Single responsibility: Process both XBRL and quarterly results"""
    
    def __init__(self):
        self.xbrl_processor = NSEXBRLProcessor()
        self.quarterly_scraper = NSEQuarterlyResultsScraper()
        self.calendar_monitor = NSEEventCalendarMonitor()
        self.value_analyzer = ValueAnalyzer()
        self.growth_analyzer = GrowthAnalyzer()
    
    def process_company_by_announcement_type(self, symbol: str) -> Dict[str, Any]:
        """Determine and process appropriate result type"""
        try:
            # Get recent events for this company
            announcement_type = self._determine_announcement_type(symbol)
            
            processing_result = {
                'symbol': symbol,
                'announcement_type': announcement_type,
                'processing_timestamp': timezone.now(),
                'success': False,
                'data': {},
                'analysis': {},
                'errors': []
            }
            
            if announcement_type == 'annual':
                result = self._process_annual_results(symbol)
                processing_result.update(result)
            elif announcement_type == 'quarterly':
                result = self._process_quarterly_results(symbol)
                processing_result.update(result)
            else:
                # Default to comprehensive processing
                result = self._process_comprehensive_data(symbol)
                processing_result.update(result)
            
            # Store results in database
            if processing_result['success']:
                self._store_unified_results(symbol, processing_result)
            
            return processing_result
            
        except Exception as e:
            logger.error(f"Error processing {symbol}: {e}")
            return {
                'symbol': symbol,
                'success': False,
                'error': str(e),
                'processing_timestamp': timezone.now()
            }
    
    def _determine_announcement_type(self, symbol: str) -> str:
        """Determine what type of announcement is expected"""
        try:
            # Check for recent corporate events
            recent_events = CorporateEvent.objects.filter(
                company__symbol=symbol,
                event_type='results_announcement',
                announcement_date__gte=timezone.now() - timedelta(days=7)
            ).order_by('-announcement_date')
            
            if recent_events.exists():
                latest_event = recent_events.first()
                event_description = latest_event.description.lower()
                
                if any(keyword in event_description for keyword in ['annual', 'yearly', 'fy', 'year ended']):
                    return 'annual'
                elif any(keyword in event_description for keyword in ['quarterly', 'quarter', 'q1', 'q2', 'q3', 'q4']):
                    return 'quarterly'
            
            # Fallback: check current month to guess
            current_month = timezone.now().month
            
            # Indian companies typically announce annual results in May-July
            if current_month in [5, 6, 7]:
                return 'annual'
            else:
                return 'quarterly'
                
        except Exception as e:
            logger.error(f"Error determining announcement type for {symbol}: {e}")
            return 'quarterly'  # Default fallback
    
    def _process_annual_results(self, symbol: str) -> Dict[str, Any]:
        """Process XBRL annual results"""
        try:
            logger.info(f"Processing annual results for {symbol}")
            
            # Download and parse XBRL data
            current_year = timezone.now().year
            xbrl_data = self.xbrl_processor.download_xbrl_data(symbol, current_year)
            
            if not xbrl_data:
                # Try previous year
                xbrl_data = self.xbrl_processor.download_xbrl_data(symbol, current_year - 1)
            
            if not xbrl_data:
                return {
                    'success': False,
                    'error': f'No XBRL data found for {symbol}',
                    'data_source': 'xbrl'
                }
            
            # Parse XBRL data
            parse_result = self.xbrl_processor.parse_xbrl_data(xbrl_data)
            
            if not parse_result.success:
                return {
                    'success': False,
                    'error': parse_result.error,
                    'data_source': 'xbrl'
                }
            
            # Analyze the data
            analysis_result = self._analyze_annual_data(parse_result.data)
            
            return {
                'success': True,
                'data_source': 'xbrl',
                'data': parse_result.data,
                'analysis': analysis_result,
                'processing_method': 'annual_xbrl'
            }
            
        except Exception as e:
            logger.error(f"Error processing annual results for {symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data_source': 'xbrl'
            }
    
    def _process_quarterly_results(self, symbol: str) -> Dict[str, Any]:
        """Process scraped quarterly results"""
        try:
            logger.info(f"Processing quarterly results for {symbol}")
            
            # Scrape quarterly results
            scrape_result = self.quarterly_scraper.scrape_quarterly_results(symbol)
            
            if not scrape_result.success:
                return {
                    'success': False,
                    'error': scrape_result.error,
                    'data_source': 'nse_quarterly'
                }
            
            # Compare with estimates
            estimates_comparison = self.quarterly_scraper.compare_with_estimates(symbol, scrape_result.data)
            
            # Analyze quarterly trends
            trend_analysis = self._analyze_quarterly_trends(scrape_result.data)
            
            return {
                'success': True,
                'data_source': 'nse_quarterly',
                'data': scrape_result.data,
                'estimates_comparison': estimates_comparison,
                'analysis': trend_analysis,
                'processing_method': 'quarterly_scrape'
            }
            
        except Exception as e:
            logger.error(f"Error processing quarterly results for {symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data_source': 'nse_quarterly'
            }
    
    def _process_comprehensive_data(self, symbol: str) -> Dict[str, Any]:
        """Process comprehensive data from screener.in as fallback"""
        try:
            logger.info(f"Processing comprehensive data for {symbol}")
            
            # This would use the existing screener scraper
            from ...market_data_service.services.parsers import ScreenerDataParser
            from ...market_data_service.services.scrapers import ScreenerWebScraper
            
            scraper = ScreenerWebScraper()
            parser = ScreenerDataParser()
            
            # Fetch and parse screener data
            url = f"https://www.screener.in/company/{symbol}/"
            html_content = scraper.fetch_page(url)
            
            if not html_content:
                return {
                    'success': False,
                    'error': 'Failed to fetch screener data',
                    'data_source': 'screener'
                }
            
            parse_result = parser.parse_company_data(html_content, symbol)
            
            if not parse_result.success:
                return {
                    'success': False,
                    'error': parse_result.error,
                    'data_source': 'screener'
                }
            
            # Analyze comprehensive data
            analysis_result = self._analyze_comprehensive_data(parse_result.data)
            
            return {
                'success': True,
                'data_source': 'screener',
                'data': parse_result.data,
                'analysis': analysis_result,
                'processing_method': 'comprehensive_screener'
            }
            
        except Exception as e:
            logger.error(f"Error processing comprehensive data for {symbol}: {e}")
            return {
                'success': False,
                'error': str(e),
                'data_source': 'screener'
            }
    
    def _analyze_annual_data(self, annual_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze annual XBRL data"""
        try:
            analysis = {}
            
            # Extract key metrics from XBRL data
            income_statement = annual_data.get('income_statement', {})
            balance_sheet = annual_data.get('balance_sheet', {})
            ratios = annual_data.get('financial_ratios', {})
            
            # Profitability analysis
            if 'net_profit_margin' in income_statement:
                analysis['profitability_score'] = min(100, max(0, income_statement['net_profit_margin'] * 5))
            
            # Financial health analysis
            if 'current_ratio' in ratios:
                current_ratio = ratios['current_ratio']
                if current_ratio >= 2:
                    analysis['liquidity_score'] = 100
                elif current_ratio >= 1.5:
                    analysis['liquidity_score'] = 75
                elif current_ratio >= 1:
                    analysis['liquidity_score'] = 50
                else:
                    analysis['liquidity_score'] = 25
            
            # Leverage analysis
            if 'debt_to_equity' in ratios:
                debt_ratio = ratios['debt_to_equity']
                if debt_ratio <= 0.3:
                    analysis['leverage_score'] = 100
                elif debt_ratio <= 0.6:
                    analysis['leverage_score'] = 75
                elif debt_ratio <= 1:
                    analysis['leverage_score'] = 50
                else:
                    analysis['leverage_score'] = 25
            
            # Overall financial health
            scores = [
                analysis.get('profitability_score', 50),
                analysis.get('liquidity_score', 50),
                analysis.get('leverage_score', 50)
            ]
            analysis['overall_financial_health'] = sum(scores) / len(scores)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing annual data: {e}")
            return {}
    
    def _analyze_quarterly_trends(self, quarterly_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze quarterly trends and momentum"""
        try:
            analysis = {}
            
            results = quarterly_data.get('results', [])
            if len(results) < 2:
                return analysis
            
            # Sort by period to get chronological order
            sorted_results = sorted(results, key=lambda x: x.get('period', ''))
            
            # Calculate quarter-over-quarter growth
            if len(sorted_results) >= 2:
                latest = sorted_results[-1].get('financial_data', {})
                previous = sorted_results[-2].get('financial_data', {})
                
                if 'revenue' in latest and 'revenue' in previous:
                    if previous['revenue'] > 0:
                        qoq_revenue_growth = ((latest['revenue'] - previous['revenue']) / previous['revenue']) * 100
                        analysis['qoq_revenue_growth'] = qoq_revenue_growth
                        
                        if qoq_revenue_growth > 15:
                            analysis['revenue_momentum'] = 'STRONG'
                        elif qoq_revenue_growth > 5:
                            analysis['revenue_momentum'] = 'MODERATE'
                        elif qoq_revenue_growth > 0:
                            analysis['revenue_momentum'] = 'WEAK'
                        else:
                            analysis['revenue_momentum'] = 'DECLINING'
                
                if 'net_profit' in latest and 'net_profit' in previous:
                    if previous['net_profit'] > 0:
                        qoq_profit_growth = ((latest['net_profit'] - previous['net_profit']) / previous['net_profit']) * 100
                        analysis['qoq_profit_growth'] = qoq_profit_growth
                        
                        if qoq_profit_growth > 20:
                            analysis['profit_momentum'] = 'STRONG'
                        elif qoq_profit_growth > 10:
                            analysis['profit_momentum'] = 'MODERATE'
                        elif qoq_profit_growth > 0:
                            analysis['profit_momentum'] = 'WEAK'
                        else:
                            analysis['profit_momentum'] = 'DECLINING'
            
            # Calculate overall momentum score
            momentum_factors = []
            if 'qoq_revenue_growth' in analysis:
                momentum_factors.append(min(100, max(0, analysis['qoq_revenue_growth'] * 2)))
            if 'qoq_profit_growth' in analysis:
                momentum_factors.append(min(100, max(0, analysis['qoq_profit_growth'] * 1.5)))
            
            if momentum_factors:
                analysis['momentum_score'] = sum(momentum_factors) / len(momentum_factors)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing quarterly trends: {e}")
            return {}
    
    def _analyze_comprehensive_data(self, comprehensive_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze comprehensive screener data"""
        try:
            # Use existing analyzers
            fundamental_data = self._extract_fundamental_data_for_analysis(comprehensive_data)
            
            value_analysis = self.value_analyzer.analyze_fundamentals(fundamental_data)
            growth_analysis = self.growth_analyzer.analyze_fundamentals(fundamental_data)
            
            return {
                'value_analysis': value_analysis,
                'growth_analysis': growth_analysis,
                'data_quality': self._assess_data_quality(comprehensive_data)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing comprehensive data: {e}")
            return {}
    
    def _extract_fundamental_data_for_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract fundamental data in format expected by analyzers"""
        try:
            valuation_metrics = data.get('valuation_metrics', {})
            profitability_metrics = data.get('profitability_metrics', {})
            growth_metrics = data.get('growth_metrics', {})
            
            return {
                'pe_ratio': valuation_metrics.get('stock_pe'),
                'pb_ratio': valuation_metrics.get('price_to_book'), 
                'dividend_yield': valuation_metrics.get('dividend_yield'),
                'roe': profitability_metrics.get('roe'),
                'roce': profitability_metrics.get('roce'),
                'net_profit_margin': profitability_metrics.get('net_profit_margin'),
                'revenue_growth': growth_metrics.get('sales_growth_1y'),
                'profit_growth': growth_metrics.get('profit_growth_1y'),
            }
            
        except Exception as e:
            logger.error(f"Error extracting fundamental data: {e}")
            return {}
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess quality of scraped data"""
        try:
            quality_metrics = {
                'completeness_score': 0,
                'freshness_score': 0,
                'consistency_score': 0,
                'overall_quality': 0
            }
            
            # Check data completeness
            required_fields = ['valuation_metrics', 'profitability_metrics', 'growth_metrics']
            present_fields = sum(1 for field in required_fields if data.get(field))
            quality_metrics['completeness_score'] = (present_fields / len(required_fields)) * 100
            
            # Check data freshness (placeholder - would need timestamps)
            quality_metrics['freshness_score'] = 85  # Assume reasonably fresh
            
            # Check data consistency (placeholder - would need validation logic)
            quality_metrics['consistency_score'] = 90  # Assume reasonably consistent
            
            # Calculate overall quality
            quality_metrics['overall_quality'] = (
                quality_metrics['completeness_score'] * 0.4 +
                quality_metrics['freshness_score'] * 0.3 +
                quality_metrics['consistency_score'] * 0.3
            )
            
            return quality_metrics
            
        except Exception as e:
            logger.error(f"Error assessing data quality: {e}")
            return {'overall_quality': 50}  # Default moderate quality
    
    @transaction.atomic
    def _store_unified_results(self, symbol: str, processing_result: Dict[str, Any]):
        """Store unified processing results in database"""
        try:
            company = Company.objects.get(symbol=symbol)
            
            # Store financial statement
            statement_type = 'annual_xbrl' if processing_result.get('processing_method') == 'annual_xbrl' else 'quarterly_results'
            
            financial_statement, created = FinancialStatement.objects.update_or_create(
                company=company,
                statement_type=statement_type,
                data_source=processing_result.get('data_source', 'unknown'),
                period=self._extract_period(processing_result),
                defaults={
                    'raw_data': processing_result.get('data', {}),
                    'processed_metrics': processing_result.get('analysis', {}),
                    'announcement_date': timezone.now(),
                    'updated_at': timezone.now()
                }
            )
            
            # Update company's last scraped timestamp
            company.last_scraped = timezone.now()
            company.save()
            
            logger.info(f"Stored unified results for {symbol}")
            
        except Company.DoesNotExist:
            logger.error(f"Company {symbol} not found in database")
        except Exception as e:
            logger.error(f"Error storing unified results for {symbol}: {e}")
    
    def _extract_period(self, processing_result: Dict[str, Any]) -> str:
        """Extract period information from processing result"""
        try:
            if processing_result.get('processing_method') == 'annual_xbrl':
                metadata = processing_result.get('data', {}).get('metadata', {})
                return metadata.get('fiscal_year', str(timezone.now().year))
            elif processing_result.get('processing_method') == 'quarterly_scrape':
                latest_quarter = processing_result.get('data', {}).get('latest_quarter', {})
                return latest_quarter.get('period', 'Unknown')
            else:
                return f"FY{timezone.now().year}"
                
        except Exception:
            return f"FY{timezone.now().year}"

    def process_companies_batch(self, symbols: List[str]) -> Dict[str, Any]:
        """Process multiple companies in batch"""
        batch_results = {
            'processed_count': 0,
            'success_count': 0,
            'failed_count': 0,
            'results': {},
            'errors': []
        }
        
        for symbol in symbols:
            try:
                result = self.process_company_by_announcement_type(symbol)
                batch_results['results'][symbol] = result
                batch_results['processed_count'] += 1
                
                if result['success']:
                    batch_results['success_count'] += 1
                else:
                    batch_results['failed_count'] += 1
                    batch_results['errors'].append(f"{symbol}: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                batch_results['failed_count'] += 1
                batch_results['errors'].append(f"{symbol}: {str(e)}")
        
        return batch_results
