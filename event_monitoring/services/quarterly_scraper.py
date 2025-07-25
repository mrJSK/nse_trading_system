# apps/event_monitoring/services/quarterly_scraper.py
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from core.interfaces.scraping_interfaces import QuarterlyResultsProcessorInterface, ScrapingResult

logger = logging.getLogger(__name__)

class NSEQuarterlyResultsScraper(QuarterlyResultsProcessorInterface):
    """Single responsibility: Scrape quarterly results from NSE website"""
    
    def __init__(self):
        self.base_url = "https://www.nseindia.com"
        self.results_url = f"{self.base_url}/companies-listing/corporate-filings-financial-results"
        self.driver = None
        self._setup_driver()
    
    def _setup_driver(self):
        """Setup Selenium WebDriver"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            
        except Exception as e:
            logger.error(f"Failed to setup WebDriver: {e}")
            self.driver = None
    
    def scrape_quarterly_results(self, symbol: str) -> ScrapingResult:
        """Scrape quarterly results for a specific company"""
        try:
            if not self.driver:
                return ScrapingResult(
                    success=False,
                    error="WebDriver not initialized",
                    symbol=symbol,
                    data_source="nse_quarterly"
                )
            
            # Navigate to results page
            self.driver.get(self.results_url)
            time.sleep(3)
            
            # Search for the specific company
            company_results = self._search_company_results(symbol)
            
            if not company_results:
                return ScrapingResult(
                    success=False,
                    error=f"No quarterly results found for {symbol}",
                    symbol=symbol,
                    data_source="nse_quarterly"
                )
            
            # Parse the results
            parsed_results = self._parse_quarterly_data(company_results, symbol)
            
            return ScrapingResult(
                success=True,
                data=parsed_results,
                symbol=symbol,
                data_source="nse_quarterly",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error scraping quarterly results for {symbol}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                symbol=symbol,
                data_source="nse_quarterly"
            )
    
    def _search_company_results(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """Search for company-specific results"""
        try:
            # Look for search input
            search_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Search']"))
            )
            
            # Clear and enter company symbol
            search_input.clear()
            search_input.send_keys(symbol)
            time.sleep(2)
            
            # Wait for results to load
            results_container = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".table-responsive, .results-container"))
            )
            
            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Find results table
            table = soup.find('table', class_=['table', 'data-table']) or soup.find('table')
            
            if not table:
                logger.warning(f"No results table found for {symbol}")
                return None
            
            # Parse table rows
            results = []
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 4:  # Ensure we have enough columns
                    result = {
                        'company': self._safe_text(cols[0]),
                        'result_type': self._safe_text(cols[1]),
                        'period': self._safe_text(cols[2]),
                        'announcement_date': self._safe_text(cols[3]),
                        'link': self._extract_link(cols[-1]) if len(cols) > 4 else None
                    }
                    
                    # Filter for the specific company
                    if symbol.upper() in result['company'].upper():
                        results.append(result)
            
            return results if results else None
            
        except Exception as e:
            logger.error(f"Error searching for {symbol} results: {e}")
            return None
    
    def _parse_quarterly_data(self, results_data: List[Dict[str, Any]], symbol: str) -> Dict[str, Any]:
        """Parse quarterly results data"""
        try:
            parsed_data = {
                'symbol': symbol,
                'results': [],
                'latest_quarter': None,
                'summary': {}
            }
            
            for result in results_data:
                # Parse each result
                quarter_data = {
                    'period': result.get('period', ''),
                    'result_type': result.get('result_type', ''),
                    'announcement_date': self._parse_date(result.get('announcement_date', '')),
                    'link': result.get('link'),
                    'financial_data': {}
                }
                
                # If there's a link, try to extract detailed financial data
                if quarter_data['link']:
                    detailed_data = self._extract_detailed_financial_data(quarter_data['link'])
                    quarter_data['financial_data'] = detailed_data
                
                parsed_data['results'].append(quarter_data)
            
            # Sort by announcement date and get latest
            if parsed_data['results']:
                sorted_results = sorted(
                    parsed_data['results'], 
                    key=lambda x: x.get('announcement_date', datetime.min),
                    reverse=True
                )
                parsed_data['latest_quarter'] = sorted_results[0]
            
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error parsing quarterly data: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _extract_detailed_financial_data(self, link: str) -> Dict[str, Any]:
        """Extract detailed financial data from result PDF/HTML"""
        try:
            if not link.startswith('http'):
                link = f"{self.base_url}{link}"
            
            # Navigate to the detailed page
            self.driver.get(link)
            time.sleep(2)
            
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            
            # Look for financial tables
            financial_data = {}
            
            # Try to find revenue, profit, and other key metrics
            tables = soup.find_all('table')
            
            for table in tables:
                # Look for key financial metrics in table headers/cells
                table_text = table.get_text().lower()
                
                if 'revenue' in table_text or 'sales' in table_text:
                    revenue_data = self._extract_revenue_from_table(table)
                    if revenue_data:
                        financial_data.update(revenue_data)
                
                if 'profit' in table_text or 'income' in table_text:
                    profit_data = self._extract_profit_from_table(table)
                    if profit_data:
                        financial_data.update(profit_data)
                
                if 'eps' in table_text or 'earnings per share' in table_text:
                    eps_data = self._extract_eps_from_table(table)
                    if eps_data:
                        financial_data.update(eps_data)
            
            return financial_data
            
        except Exception as e:
            logger.error(f"Error extracting detailed financial data: {e}")
            return {}
    
    def _extract_revenue_from_table(self, table) -> Dict[str, Any]:
        """Extract revenue data from table"""
        try:
            revenue_data = {}
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    if 'revenue' in header or 'sales' in header or 'income from operations' in header:
                        revenue_data['revenue'] = self._parse_financial_value(value)
                    elif 'total income' in header:
                        revenue_data['total_income'] = self._parse_financial_value(value)
            
            return revenue_data
            
        except Exception as e:
            logger.error(f"Error extracting revenue data: {e}")
            return {}
    
    def _extract_profit_from_table(self, table) -> Dict[str, Any]:
        """Extract profit data from table"""
        try:
            profit_data = {}
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    if 'net profit' in header or 'profit after tax' in header:
                        profit_data['net_profit'] = self._parse_financial_value(value)
                    elif 'profit before tax' in header:
                        profit_data['profit_before_tax'] = self._parse_financial_value(value)
                    elif 'operating profit' in header or 'ebitda' in header:
                        profit_data['operating_profit'] = self._parse_financial_value(value)
            
            return profit_data
            
        except Exception as e:
            logger.error(f"Error extracting profit data: {e}")
            return {}
    
    def _extract_eps_from_table(self, table) -> Dict[str, Any]:
        """Extract EPS data from table"""
        try:
            eps_data = {}
            
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    header = cells[0].get_text().strip().lower()
                    value = cells[1].get_text().strip()
                    
                    if 'earnings per share' in header or 'eps' in header:
                        eps_data['eps'] = self._parse_financial_value(value)
                    elif 'basic eps' in header:
                        eps_data['basic_eps'] = self._parse_financial_value(value)
                    elif 'diluted eps' in header:
                        eps_data['diluted_eps'] = self._parse_financial_value(value)
            
            return eps_data
            
        except Exception as e:
            logger.error(f"Error extracting EPS data: {e}")
            return {}
    
    def compare_with_estimates(self, symbol: str, results: Dict[str, Any]) -> Dict[str, float]:
        """Compare results with analyst estimates"""
        try:
            # This is a placeholder implementation
            # In reality, you would integrate with analyst estimate providers
            # like Bloomberg, Thomson Reuters, or other financial data providers
            
            comparison = {}
            
            latest_quarter = results.get('latest_quarter', {})
            financial_data = latest_quarter.get('financial_data', {})
            
            if 'revenue' in financial_data:
                # Placeholder: assume 5% revenue growth expectation
                actual_revenue = financial_data['revenue']
                # You would get this from an estimates database
                estimated_revenue = actual_revenue * 0.95  # Placeholder
                
                if estimated_revenue > 0:
                    surprise_pct = ((actual_revenue - estimated_revenue) / estimated_revenue) * 100
                    comparison['revenue_surprise_pct'] = surprise_pct
            
            if 'net_profit' in financial_data:
                # Placeholder: assume 10% profit growth expectation
                actual_profit = financial_data['net_profit']
                estimated_profit = actual_profit * 0.90  # Placeholder
                
                if estimated_profit > 0:
                    surprise_pct = ((actual_profit - estimated_profit) / estimated_profit) * 100
                    comparison['profit_surprise_pct'] = surprise_pct
            
            if 'eps' in financial_data:
                actual_eps = financial_data['eps']
                estimated_eps = actual_eps * 0.95  # Placeholder
                
                if estimated_eps > 0:
                    surprise_pct = ((actual_eps - estimated_eps) / estimated_eps) * 100
                    comparison['eps_surprise_pct'] = surprise_pct
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing with estimates: {e}")
            return {}
    
    def _safe_text(self, element) -> str:
        """Safely extract text from element"""
        try:
            return element.get_text().strip() if element else ""
        except:
            return ""
    
    def _extract_link(self, element) -> Optional[str]:
        """Extract link from element"""
        try:
            link_tag = element.find('a')
            if link_tag and link_tag.get('href'):
                return link_tag['href']
            return None
        except:
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        try:
            if not date_str:
                return None
            
            # Try different date formats
            formats = [
                '%d-%m-%Y',
                '%d/%m/%Y', 
                '%Y-%m-%d',
                '%d %b %Y',
                '%d %B %Y'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str.strip(), fmt)
                except ValueError:
                    continue
            
            return None
            
        except Exception:
            return None
    
    def _parse_financial_value(self, value_str: str) -> Optional[float]:
        """Parse financial value string to float"""
        try:
            if not value_str:
                return None
            
            # Clean the string
            cleaned = value_str.replace(',', '').replace('₹', '').replace('Rs.', '').strip()
            
            # Handle different units
            multiplier = 1
            if 'crore' in cleaned.lower() or 'cr' in cleaned.lower():
                multiplier = 10000000  # 1 crore = 10 million
                cleaned = cleaned.lower().replace('crore', '').replace('cr', '').strip()
            elif 'lakh' in cleaned.lower() or 'lac' in cleaned.lower():
                multiplier = 100000  # 1 lakh = 100 thousand
                cleaned = cleaned.lower().replace('lakh', '').replace('lac', '').strip()
            
            # Extract numeric value
            import re
            match = re.search(r'[-+]?\d*\.?\d+', cleaned)
            if match:
                return float(match.group(0)) * multiplier
            
            return None
            
        except Exception:
            return None
    
    def __del__(self):
        """Cleanup WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
