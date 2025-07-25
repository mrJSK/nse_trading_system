# apps/market_data_service/services/scrapers.py
import requests
import time
import random
import logging
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from django.conf import settings
from core.interfaces.scraping_interfaces import WebScraperInterface, ScrapingResult

logger = logging.getLogger(__name__)

class ScreenerWebScraper(WebScraperInterface):
    """Single responsibility: Handle web scraping operations for screener.in"""
    
    def __init__(self):
        self.base_url = "https://www.screener.in"
        self.session = requests.Session()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        ]
        self.max_retries = 3
        self.backoff_factor = 0.8
    
    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch HTML content with retry mechanism and rate limiting"""
        retries = kwargs.get('retries', self.max_retries)
        referer = kwargs.get('referer', None)
        
        headers = self._get_headers(referer)
        
        for attempt in range(retries):
            try:
                logger.info(f"Fetching {url} (attempt {attempt + 1}/{retries})")
                
                response = self.session.get(
                    url, 
                    headers=headers, 
                    timeout=30,
                    allow_redirects=True
                )
                response.raise_for_status()
                
                # Add random delay to avoid being blocked
                time.sleep(random.uniform(1.5, 3.5))
                
                return response.text
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                
                if attempt < retries - 1:
                    wait_time = self.backoff_factor * (2 ** attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                else:
                    logger.error(f"Final attempt failed for {url}")
                    return None
        
        return None
    
    def is_available(self) -> bool:
        """Check if screener.in is accessible"""
        try:
            response = self.session.get(
                f"{self.base_url}/", 
                headers=self._get_headers(),
                timeout=10
            )
            return response.status_code == 200
        except:
            return False
    
    def _get_headers(self, referer: Optional[str] = None) -> Dict[str, str]:
        """Generate headers with random user agent"""
        headers = {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        if referer:
            headers['Referer'] = referer
            
        return headers

class CompanyListScraper(WebScraperInterface):
    """Single responsibility: Scrape company listings from screener.in"""
    
    def __init__(self, web_scraper: WebScraperInterface):
        self.web_scraper = web_scraper
        self.listing_url_template = "https://www.screener.in/screens/515361/largecaptop-100midcap101-250smallcap251/?page={}&limit=50"
    
    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Delegate to the web scraper"""
        return self.web_scraper.fetch_page(url, **kwargs)
    
    def is_available(self) -> bool:
        """Check availability through web scraper"""
        return self.web_scraper.is_available()
    
    def get_all_company_urls(self) -> List[str]:
        """Get all company URLs from listing pages"""
        company_urls = []
        page = 1
        
        while True:
            list_url = self.listing_url_template.format(page)
            logger.info(f"Fetching company list from page {page}")
            
            html_content = self.fetch_page(list_url)
            if not html_content:
                logger.warning(f"Failed to fetch page {page}, stopping")
                break
            
            soup = BeautifulSoup(html_content, 'lxml')
            rows = soup.select('table.data-table tr[data-row-company-id]')
            
            if not rows:
                logger.info(f"No more companies found on page {page}")
                break
            
            for row in rows:
                link_tag = row.select_one('a')
                if link_tag and link_tag.get('href'):
                    company_urls.append(f"https://www.screener.in{link_tag['href']}")
            
            page += 1
            
            # Safety break to avoid infinite loops
            if page > 100:
                logger.warning("Reached maximum page limit (100), stopping")
                break
        
        logger.info(f"Found {len(company_urls)} company URLs")
        return company_urls
