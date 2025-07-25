# core/interfaces/scraping_interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass
class ScrapingResult:
    """Data transfer object for scraping results"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    symbol: Optional[str] = None
    data_source: Optional[str] = None
    timestamp: Optional[datetime] = None

@dataclass
class TradingSignal:
    """Data transfer object for trading signals"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    confidence: float  # 0.0 to 1.0
    reason: str
    data_sources: List[str]
    timestamp: datetime
    metadata: Dict[str, Any] = None

class WebScraperInterface(ABC):
    """Interface for web scraping operations"""
    
    @abstractmethod
    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch HTML content from URL"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the scraper is available"""
        pass

class DataParserInterface(ABC):
    """Interface for parsing scraped data"""
    
    @abstractmethod
    def parse_company_data(self, html_content: str, symbol: str) -> ScrapingResult:
        """Parse company data from HTML"""
        pass
    
    @abstractmethod
    def validate_parsed_data(self, data: Dict[str, Any]) -> bool:
        """Validate parsed data"""
        pass

class XBRLProcessorInterface(ABC):
    """Interface for XBRL data processing"""
    
    @abstractmethod
    def download_xbrl_data(self, symbol: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Download XBRL data for a company"""
        pass
    
    @abstractmethod
    def parse_xbrl_data(self, xbrl_data: Dict[str, Any]) -> ScrapingResult:
        """Parse XBRL data into structured format"""
        pass

class QuarterlyResultsProcessorInterface(ABC):
    """Interface for quarterly results processing"""
    
    @abstractmethod
    def scrape_quarterly_results(self, symbol: str) -> ScrapingResult:
        """Scrape quarterly results from NSE"""
        pass
    
    @abstractmethod
    def compare_with_estimates(self, symbol: str, results: Dict[str, Any]) -> Dict[str, float]:
        """Compare results with analyst estimates"""
        pass

class EventMonitorInterface(ABC):
    """Interface for event monitoring"""
    
    @abstractmethod
    def get_upcoming_events(self, days_ahead: int = 30) -> Dict[str, List[str]]:
        """Get upcoming corporate events"""
        pass
    
    @abstractmethod
    def get_recent_announcements(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent corporate announcements"""
        pass

class DataStorageInterface(ABC):
    """Interface for storing parsed data"""
    
    @abstractmethod
    def store_company_data(self, symbol: str, data: Dict[str, Any], data_source: str) -> bool:
        """Store company data in database"""
        pass
    
    @abstractmethod
    def get_companies_to_scrape(self) -> List[str]:
        """Get list of company symbols to scrape"""
        pass

class TradingSignalGeneratorInterface(ABC):
    """Interface for generating trading signals"""
    
    @abstractmethod
    def generate_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate trading signals from analysis data"""
        pass

class ScrapingOrchestratorInterface(ABC):
    """Interface for orchestrating the scraping process"""
    
    @abstractmethod
    def scrape_company(self, symbol: str) -> ScrapingResult:
        """Scrape data for a single company"""
        pass
    
    @abstractmethod
    def scrape_all_companies(self) -> Dict[str, Any]:
        """Scrape data for all companies"""
        pass
