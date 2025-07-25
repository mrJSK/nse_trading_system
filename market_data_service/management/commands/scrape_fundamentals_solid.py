# apps/market_data_service/management/commands/scrape_fundamentals_solid.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from market_data_service.services.scrapers import ScreenerWebScraper
from market_data_service.services.parsers import ScreenerDataParser
from market_data_service.services.storage import DatabaseStorageService
from market_data_service.services.orchestrator import ScrapingOrchestrator
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'SOLID-architecture based fundamental data scraping from screener.in'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--symbol',
            type=str,
            help='Scrape data for a specific company symbol'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limit number of companies to scrape (0 = no limit)'
        )
    
    def handle(self, *args, **options):
        start_time = timezone.now()
        self.stdout.write(
            self.style.SUCCESS(f'[{start_time}] Starting SOLID scraping process...')
        )
        
        # Dependency injection - can easily swap implementations
        web_scraper = ScreenerWebScraper()
        data_parser = ScreenerDataParser()
        data_storage = DatabaseStorageService()
        
        orchestrator = ScrapingOrchestrator(
            web_scraper=web_scraper,
            data_parser=data_parser,
            data_storage=data_storage
        )
        
        # Check if scraper is available
        if not web_scraper.is_available():
            self.stdout.write(
                self.style.ERROR('Screener.in is not available. Please try again later.')
            )
            return
        
        symbol = options.get('symbol')
        
        if symbol:
            # Scrape single company
            self.stdout.write(f'Scraping data for {symbol}...')
            result = orchestrator.scrape_company(symbol)
            
            if result.success:
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully scraped {symbol}')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Failed to scrape {symbol}: {result.error}')
                )
        else:
            # Scrape all companies
            self.stdout.write('Scraping all companies...')
            summary = orchestrator.scrape_all_companies()
            
            # Display summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write('SCRAPING SUMMARY')
            self.stdout.write('='*50)
            self.stdout.write(f"Total companies: {summary['total_companies']}")
            self.stdout.write(f"Successful: {summary['successful_scrapes']}")
            self.stdout.write(f"Failed: {summary['failed_scrapes']}")
            self.stdout.write(f"Success rate: {summary['success_rate']:.1f}%")
            
            if summary['errors']:
                self.stdout.write('\nFirst few errors:')
                for error in summary['errors'][:5]:
                    self.stdout.write(f"- {error}")
        
        end_time = timezone.now()
        duration = (end_time - start_time).total_seconds()
        
        self.stdout.write(
            self.style.SUCCESS(f'\n[{end_time}] Scraping completed in {duration:.1f} seconds')
        )
