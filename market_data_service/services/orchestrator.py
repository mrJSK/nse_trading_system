# apps/market_data_service/services/orchestrator.py
from typing import Dict, List, Any
from core.interfaces.scraping_interfaces import (
    ScrapingOrchestratorInterface, WebScraperInterface, 
    DataParserInterface, DataStorageInterface, ScrapingResult
)
import logging
import time

logger = logging.getLogger(__name__)

class ScrapingOrchestrator(ScrapingOrchestratorInterface):
    """Single responsibility: Orchestrate the complete scraping process"""
    
    def __init__(
        self,
        web_scraper: WebScraperInterface,
        data_parser: DataParserInterface,
        data_storage: DataStorageInterface
    ):
        self.web_scraper = web_scraper
        self.data_parser = data_parser
        self.data_storage = data_storage
        self.base_url = "https://www.screener.in/company"
    
    def scrape_company(self, symbol: str) -> ScrapingResult:
        """Scrape data for a single company"""
        try:
            # Step 1: Fetch HTML content
            company_url = f"{self.base_url}/{symbol}/"
            html_content = self.web_scraper.fetch_page(company_url)
            
            if not html_content:
                return ScrapingResult(
                    success=False,
                    error="Failed to fetch HTML content",
                    symbol=symbol
                )
            
            # Step 2: Parse the data
            parse_result = self.data_parser.parse_company_data(html_content, symbol)
            
            if not parse_result.success:
                return parse_result
            
            # Step 3: Store the data
            storage_success = self.data_storage.store_company_data(symbol, parse_result.data)
            
            if not storage_success:
                return ScrapingResult(
                    success=False,
                    error="Failed to store data in database",
                    symbol=symbol
                )
            
            return ScrapingResult(
                success=True,
                data=parse_result.data,
                symbol=symbol
            )
            
        except Exception as e:
            logger.error(f"Error scraping {symbol}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                symbol=symbol
            )
    
    def scrape_all_companies(self) -> Dict[str, Any]:
        """Scrape data for all active companies"""
        # Get companies to scrape
        companies = self.data_storage.get_companies_to_scrape()
        
        if not companies:
            # If no companies in database, get from listing pages
            from .scrapers import CompanyListScraper
            list_scraper = CompanyListScraper(self.web_scraper)
            company_urls = list_scraper.get_all_company_urls()
            companies = [url.split('/')[-2] for url in company_urls]  # Extract symbols
        
        total_companies = len(companies)
        successful_scrapes = 0
        failed_scrapes = 0
        errors = []
        
        logger.info(f"Starting to scrape {total_companies} companies")
        
        for i, symbol in enumerate(companies):
            try:
                logger.info(f"[{i+1}/{total_companies}] Scraping {symbol}")
                
                result = self.scrape_company(symbol)
                
                if result.success:
                    successful_scrapes += 1
                    logger.info(f"[{i+1}/{total_companies}] Successfully scraped {symbol}")
                else:
                    failed_scrapes += 1
                    error_msg = f"Failed to scrape {symbol}: {result.error}"
                    errors.append(error_msg)
                    logger.error(f"[{i+1}/{total_companies}] {error_msg}")
                
            except Exception as e:
                failed_scrapes += 1
                error_msg = f"Unexpected error scraping {symbol}: {e}"
                errors.append(error_msg)
                logger.error(f"[{i+1}/{total_companies}] {error_msg}")
            
            # Add delay between requests to be respectful
            time.sleep(1.5)
        
        summary = {
            'total_companies': total_companies,
            'successful_scrapes': successful_scrapes,
            'failed_scrapes': failed_scrapes,
            'success_rate': (successful_scrapes / total_companies * 100) if total_companies > 0 else 0,
            'errors': errors[:10]  # Only include first 10 errors
        }
        
        logger.info(f"Scraping completed: {successful_scrapes}/{total_companies} successful")
        return summary
