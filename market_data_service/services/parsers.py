# apps/market_data_service/services/parsers.py
import re
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from decimal import Decimal, InvalidOperation
from core.interfaces.scraping_interfaces import DataParserInterface, ScrapingResult
import logging

logger = logging.getLogger(__name__)

class ScreenerDataParser(DataParserInterface):
    """Single responsibility: Parse screener.in HTML data"""
    
    def __init__(self):
        self.month_map = {
            'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
            'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
        }
    
    def parse_company_data(self, html_content: str, symbol: str) -> ScrapingResult:
        """Parse complete company data from HTML"""
        try:
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Parse different data sections
            basic_info = self._parse_basic_info(soup, symbol)
            valuation_metrics = self._parse_valuation_metrics(soup)
            profitability_metrics = self._parse_profitability_metrics(soup)
            growth_metrics = self._parse_growth_metrics(soup)
            financial_statements = self._parse_financial_statements(soup)
            qualitative_analysis = self._parse_qualitative_analysis(soup)
            shareholding_patterns = self._parse_shareholding_patterns(soup)
            industry_classification = self._parse_industry_classification(soup)
            
            parsed_data = {
                'basic_info': basic_info,
                'valuation_metrics': valuation_metrics,
                'profitability_metrics': profitability_metrics,
                'growth_metrics': growth_metrics,
                'financial_statements': financial_statements,
                'qualitative_analysis': qualitative_analysis,
                'shareholding_patterns': shareholding_patterns,
                'industry_classification': industry_classification,
            }
            
            if self.validate_parsed_data(parsed_data):
                return ScrapingResult(success=True, data=parsed_data, symbol=symbol)
            else:
                return ScrapingResult(
                    success=False, 
                    error="Data validation failed", 
                    symbol=symbol
                )
                
        except Exception as e:
            logger.error(f"Failed to parse data for {symbol}: {e}")
            return ScrapingResult(
                success=False, 
                error=str(e), 
                symbol=symbol
            )
    
    def validate_parsed_data(self, data: Dict[str, Any]) -> bool:
        """Validate that essential data is present"""
        try:
            basic_info = data.get('basic_info', {})
            
            # Check for essential fields
            required_fields = ['name', 'symbol']
            for field in required_fields:
                if not basic_info.get(field):
                    logger.warning(f"Missing required field: {field}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def _parse_basic_info(self, soup: BeautifulSoup, symbol: str) -> Dict[str, Any]:
        """Parse basic company information"""
        try:
            name_element = soup.select_one('h1.margin-0')
            name = name_element.get_text(strip=True) if name_element else symbol
            
            # Parse about section
            about_element = soup.select_one('.company-profile .about p')
            about = about_element.get_text(strip=True) if about_element else None
            
            # Parse website
            website = self._parse_website_link(soup)
            
            # Parse BSE and NSE codes
            bse_element = soup.select_one('a[href*="bseindia.com"]')
            nse_element = soup.select_one('a[href*="nseindia.com"]')
            
            bse_code = self._clean_exchange_code(
                bse_element.get_text(strip=True) if bse_element else None
            )
            nse_code = self._clean_exchange_code(
                nse_element.get_text(strip=True) if nse_element else None
            )
            
            return {
                'symbol': symbol,
                'name': name,
                'about': about,
                'website': website,
                'bse_code': bse_code,
                'nse_code': nse_code,
            }
            
        except Exception as e:
            logger.error(f"Error parsing basic info: {e}")
            return {'symbol': symbol, 'name': symbol}
    
    def _parse_valuation_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse valuation metrics from top ratios section"""
        try:
            metrics = {}
            ratios_section = soup.select('#top-ratios li')
            
            for li in ratios_section:
                name_elem = li.select_one('.name')
                value_elem = li.select_one('.value')
                
                if name_elem and value_elem:
                    name = name_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    
                    if 'Market Cap' in name:
                        metrics['market_cap'] = self._parse_currency_value(value)
                    elif 'Current Price' in name:
                        metrics['current_price'] = self._parse_numeric_value(value)
                    elif 'High / Low' in name:
                        high_low = self._parse_high_low(value)
                        metrics.update(high_low)
                    elif 'Stock P/E' in name:
                        metrics['stock_pe'] = self._parse_numeric_value(value)
                    elif 'Book Value' in name:
                        metrics['book_value'] = self._parse_numeric_value(value)
                    elif 'Dividend Yield' in name:
                        metrics['dividend_yield'] = self._parse_percentage_value(value)
                    elif 'Face Value' in name:
                        metrics['face_value'] = self._parse_numeric_value(value)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error parsing valuation metrics: {e}")
            return {}
    
    def _parse_profitability_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse profitability metrics"""
        try:
            metrics = {}
            ratios_section = soup.select('#top-ratios li')
            
            for li in ratios_section:
                name_elem = li.select_one('.name')
                value_elem = li.select_one('.value')
                
                if name_elem and value_elem:
                    name = name_elem.get_text(strip=True)
                    value = value_elem.get_text(strip=True)
                    
                    if 'ROCE' in name:
                        metrics['roce'] = self._parse_percentage_value(value)
                    elif 'ROE' in name:
                        metrics['roe'] = self._parse_percentage_value(value)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error parsing profitability metrics: {e}")
            return {}
    
    def _parse_growth_metrics(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse growth metrics from growth tables"""
        try:
            growth_data = {}
            pl_section = soup.select_one('section#profit-loss')
            
            if not pl_section:
                return growth_data
            
            tables = pl_section.select('table.ranges-table')
            
            for table in tables:
                title_elem = table.select_one('th')
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True).replace(':', '')
                table_data = {}
                
                for row in table.select('tr')[1:]:  # Skip header row
                    cols = row.select('td')
                    if len(cols) == 2:
                        key = cols[0].get_text(strip=True).replace(':', '')
                        value = cols[1].get_text(strip=True)
                        table_data[key] = self._parse_percentage_value(value)
                
                growth_data[title] = table_data
            
            return growth_data
            
        except Exception as e:
            logger.error(f"Error parsing growth metrics: {e}")
            return {}
    
    def _parse_financial_statements(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse all financial statement tables"""
        statements = {}
        
        statement_ids = [
            'quarters', 'profit-loss', 'balance-sheet', 'cash-flow', 'ratios'
        ]
        
        for statement_id in statement_ids:
            try:
                statement_data = self._parse_financial_table(soup, statement_id)
                if statement_data:
                    statements[statement_id] = statement_data
            except Exception as e:
                logger.error(f"Error parsing {statement_id}: {e}")
        
        return statements
    
    def _parse_financial_table(self, soup: BeautifulSoup, table_id: str) -> Dict[str, Any]:
        """Parse a specific financial table"""
        try:
            section = soup.select_one(f'section#{table_id}')
            if not section:
                return {}
            
            table = section.select_one('table.data-table')
            if not table:
                return {}
            
            # Parse headers (time periods)
            header_elements = table.select('thead th')[1:]  # Skip first column
            original_headers = [th.get_text(strip=True) for th in header_elements]
            
            if not original_headers:
                return {}
            
            # Sort headers chronologically
            sorted_headers = sorted(original_headers, key=self._get_calendar_sort_key, reverse=True)
            
            # Parse data rows
            body_data = []
            for row in table.select('tbody tr'):
                cols = row.select('td')
                if not cols or 'sub' in row.get('class', []):
                    continue
                
                row_name = cols[0].get_text(strip=True).replace('+', '').strip()
                if not row_name:
                    continue
                
                # Map original values to headers
                original_values = [col.get_text(strip=True) for col in cols[1:]]
                value_map = dict(zip(original_headers, original_values))
                
                # Reorder values according to sorted headers
                sorted_values = [value_map.get(h, '') for h in sorted_headers]
                
                body_data.append({
                    'Description': row_name,
                    'values': sorted_values
                })
            
            return {
                'headers': sorted_headers,
                'body': body_data
            }
            
        except Exception as e:
            logger.error(f"Error parsing financial table {table_id}: {e}")
            return {}
    
    def _parse_qualitative_analysis(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse pros and cons"""
        try:
            pros = []
            cons = []
            
            # Parse pros
            pros_section = soup.select('.pros ul li')
            pros = [li.get_text(strip=True) for li in pros_section]
            
            # Parse cons
            cons_section = soup.select('.cons ul li')
            cons = [li.get_text(strip=True) for li in cons_section]
            
            return {
                'pros': pros,
                'cons': cons
            }
            
        except Exception as e:
            logger.error(f"Error parsing qualitative analysis: {e}")
            return {'pros': [], 'cons': []}
    
    def _parse_shareholding_patterns(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """Parse shareholding pattern data"""
        try:
            patterns = {}
            
            # Parse quarterly shareholding pattern
            quarterly_data = self._parse_shareholding_table(soup, 'quarterly-shp')
            if quarterly_data:
                patterns['quarterly'] = quarterly_data
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error parsing shareholding patterns: {e}")
            return {}
    
    def _parse_shareholding_table(self, soup: BeautifulSoup, table_id: str) -> Dict[str, Any]:
        """Parse shareholding table"""
        try:
            table = soup.select_one(f'div#{table_id} table.data-table')
            if not table:
                return {}
            
            # Parse headers
            original_headers = [th.get_text(strip=True) for th in table.select('thead th')][1:]
            sorted_headers = sorted(original_headers, key=self._get_calendar_sort_key, reverse=True)
            
            data = {}
            for row in table.select('tbody tr'):
                cols = row.select('td')
                if not cols or 'sub' in row.get('class', []):
                    continue
                
                row_name = cols[0].get_text(strip=True).replace('+', '').strip()
                if not row_name:
                    continue
                
                original_values = [col.get_text(strip=True) for col in cols[1:]]
                value_map = dict(zip(original_headers, original_values))
                
                row_data = {h: value_map.get(h, '') for h in sorted_headers}
                data[row_name] = row_data
            
            return data
            
        except Exception as e:
            logger.error(f"Error parsing shareholding table {table_id}: {e}")
            return {}
    
    def _parse_industry_classification(self, soup: BeautifulSoup) -> Optional[str]:
        """Parse industry classification path"""
        try:
            peers_section = soup.select_one('section#peers')
            if not peers_section:
                return None
            
            path_paragraph = peers_section.select_one('p.sub:not(#benchmarks)')
            if not path_paragraph:
                return None
            
            path_links = path_paragraph.select('a')
            if not path_links:
                return None
            
            # Get the last (most specific) classification
            last_link = path_links[-1]
            return last_link.get_text(strip=True).replace('&', 'and')
            
        except Exception as e:
            logger.error(f"Error parsing industry classification: {e}")
            return None
    
    # Utility methods
    def _parse_website_link(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract website link"""
        try:
            company_links_div = soup.select_one('div.company-links')
            if not company_links_div:
                return None
            
            all_links = company_links_div.find_all('a', href=True)
            for link in all_links:
                href = link['href']
                if 'bseindia.com' not in href and 'nseindia.com' not in href:
                    return href
            return None
            
        except Exception as e:
            logger.error(f"Error parsing website link: {e}")
            return None
    
    def _clean_exchange_code(self, text: str) -> Optional[str]:
        """Clean BSE/NSE codes"""
        if not text:
            return None
        return text.strip().replace('BSE:', '').replace('NSE:', '').strip()
    
    def _parse_currency_value(self, value: str) -> Optional[Decimal]:
        """Parse currency values like '₹ 33,162 Cr.' to Decimal"""
        if not value or value.strip() == '-':
            return None
        
        try:
            # Remove currency symbols and spaces
            cleaned = re.sub(r'[₹,\s]', '', value)
            
            # Handle different units
            if 'Cr.' in value:
                number = float(cleaned.replace('Cr.', ''))
                return Decimal(str(number * 10000000))  # 1 Cr = 10M
            elif 'L' in value:
                number = float(cleaned.replace('L', ''))
                return Decimal(str(number * 100000))  # 1 L = 100K
            else:
                # Try to extract just the number
                match = re.search(r'[-+]?\d*\.?\d+', cleaned)
                if match:
                    return Decimal(match.group(0))
                    
        except (ValueError, InvalidOperation) as e:
            logger.warning(f"Could not parse currency value '{value}': {e}")
        
        return None
    
    def _parse_numeric_value(self, value: str) -> Optional[Decimal]:
        """Parse simple numeric values"""
        if not value or value.strip() == '-':
            return None
        
        try:
            # Remove commas and extra spaces
            cleaned = value.replace(',', '').strip()
            match = re.search(r'[-+]?\d*\.?\d+', cleaned)
            if match:
                return Decimal(match.group(0))
        except (ValueError, InvalidOperation) as e:
            logger.warning(f"Could not parse numeric value '{value}': {e}")
        
        return None
    
    def _parse_percentage_value(self, value: str) -> Optional[Decimal]:
        """Parse percentage values"""
        if not value or value.strip() == '-':
            return None
        
        try:
            cleaned = value.replace('%', '').strip()
            return Decimal(cleaned)
        except (ValueError, InvalidOperation) as e:
            logger.warning(f"Could not parse percentage value '{value}': {e}")
        
        return None
    
    def _parse_high_low(self, value: str) -> Dict[str, Optional[Decimal]]:
        """Parse high/low values like '2,500 / 1,200'"""
        try:
            if '/' in value:
                parts = value.split('/')
                if len(parts) == 2:
                    high = self._parse_numeric_value(parts[0].strip())
                    low = self._parse_numeric_value(parts[1].strip())
                    return {
                        'high_52_week': high,
                        'low_52_week': low
                    }
        except Exception as e:
            logger.warning(f"Could not parse high/low value '{value}': {e}")
        
        return {'high_52_week': None, 'low_52_week': None}
    
    def _get_calendar_sort_key(self, header_string: str) -> tuple:
        """Generate sort key for calendar headers"""
        try:
            if not header_string.strip():
                return (0, 0)
            
            parts = header_string.strip().split()
            if len(parts) == 2:
                month_str, year_str = parts
                month_num = self.month_map.get(month_str, 0)
                year_num = int(year_str)
                return (year_num, month_num)
            else:
                # Handle year-only headers
                return (int(header_string), 0)
                
        except (ValueError, KeyError, IndexError):
            return (0, 0)
