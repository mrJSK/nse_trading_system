# core/interfaces/scraping_interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
import pandas as pd

# =============================================================================
# ENUMS FOR TYPE SAFETY
# =============================================================================

class SignalAction(Enum):
    """Trading signal actions"""
    BUY = "BUY"
    SELL = "SELL" 
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"
    AVOID = "AVOID"

class RiskLevel(Enum):
    """Risk assessment levels"""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"

class DataSource(Enum):
    """Data source types"""
    SCREENER = "screener"
    XBRL = "xbrl"
    NSE_QUARTERLY = "nse_quarterly"
    NSE_CALENDAR = "nse_calendar"
    RSS_FEED = "rss"
    FYERS = "fyers"
    TECHNICAL = "technical"

class EventType(Enum):
    """Corporate event types"""
    RESULTS_ANNOUNCEMENT = "results_announcement"
    ORDER_RECEIVED = "order_received"
    DIVIDEND = "dividend"
    BONUS = "bonus"
    RIGHTS = "rights"
    BUYBACK = "buyback"
    MERGER = "merger"
    DELISTING = "delisting"
    OTHER = "other"

# =============================================================================
# DATA TRANSFER OBJECTS
# =============================================================================

@dataclass
class ScrapingResult:
    """Enhanced data transfer object for scraping results"""
    success: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    symbol: Optional[str] = None
    data_source: Optional[DataSource] = None
    timestamp: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    data_quality_score: Optional[float] = None  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TradingSignal:
    """Enhanced data transfer object for trading signals"""
    symbol: str
    action: SignalAction
    confidence: float  # 0.0 to 1.0
    reason: str
    data_sources: List[DataSource]
    timestamp: datetime
    
    # Price information
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    # Risk management
    risk_level: RiskLevel = RiskLevel.MEDIUM
    position_size_pct: Optional[float] = None  # Recommended position size %
    max_loss_pct: Optional[float] = None  # Maximum acceptable loss %
    
    # Signal metadata
    urgency: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    time_horizon: str = "MEDIUM_TERM"  # SHORT_TERM, MEDIUM_TERM, LONG_TERM
    signal_strength: float = 0.5  # 0.0 to 1.0
    
    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)
    component_signals: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AnalysisData:
    """Data transfer object for comprehensive analysis data"""
    symbol: str
    timestamp: datetime
    
    # Fundamental data
    fundamental_analysis: Optional[Dict[str, Any]] = None
    
    # Technical data
    technical_analysis: Optional[Dict[str, Any]] = None
    
    # Event data
    recent_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Market data
    market_data: Optional[pd.DataFrame] = None
    live_data: Optional[Dict[str, Any]] = None
    
    # Quality metrics
    data_completeness: float = 0.0  # 0.0 to 1.0
    data_freshness_hours: Optional[int] = None
    
    # Analysis results
    recommendation: Optional[Dict[str, Any]] = None
    attractiveness_score: Optional[float] = None
    risk_assessment: Optional[Dict[str, Any]] = None

@dataclass
class CompanyPriority:
    """Data transfer object for company prioritization"""
    symbol: str
    priority_score: float  # 0.0 to 100.0
    reasons: List[str]
    data_sources: List[DataSource]
    last_updated: datetime
    
    # Categorization
    category: str = "UNKNOWN"  # FUNDAMENTAL, EVENT, MOMENTUM, WATCHLIST
    urgency: str = "MEDIUM"  # LOW, MEDIUM, HIGH
    
    # Supporting data
    fundamental_score: Optional[float] = None
    event_count: int = 0
    days_since_last_event: Optional[int] = None

# =============================================================================
# CORE SCRAPING INTERFACES
# =============================================================================

class WebScraperInterface(ABC):
    """Interface for web scraping operations"""
    
    @abstractmethod
    def fetch_page(self, url: str, **kwargs) -> Optional[str]:
        """Fetch HTML content from URL with retry mechanism"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the scraper service is available"""
        pass
    
    @abstractmethod
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limiting status"""
        pass
    
    @abstractmethod
    def clear_cache(self) -> bool:
        """Clear scraper cache"""
        pass

class DataParserInterface(ABC):
    """Interface for parsing scraped data"""
    
    @abstractmethod
    def parse_company_data(self, html_content: str, symbol: str) -> ScrapingResult:
        """Parse company data from HTML content"""
        pass
    
    @abstractmethod
    def validate_parsed_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate parsed data and return validation errors"""
        pass
    
    @abstractmethod
    def calculate_data_quality_score(self, data: Dict[str, Any]) -> float:
        """Calculate data quality score (0.0 to 1.0)"""
        pass
    
    @abstractmethod
    def extract_key_metrics(self, parsed_data: Dict[str, Any]) -> Dict[str, float]:
        """Extract key financial metrics for quick analysis"""
        pass

# =============================================================================
# SPECIALIZED DATA PROCESSING INTERFACES
# =============================================================================

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
    
    @abstractmethod
    def extract_financial_statements(self, xbrl_data: Dict[str, Any]) -> Dict[str, pd.DataFrame]:
        """Extract financial statements as DataFrames"""
        pass
    
    @abstractmethod
    def calculate_financial_ratios(self, xbrl_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate financial ratios from XBRL data"""
        pass
    
    @abstractmethod
    def validate_xbrl_consistency(self, xbrl_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate XBRL data consistency"""
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
    
    @abstractmethod
    def analyze_quarterly_trends(self, results_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze trends across multiple quarters"""
        pass
    
    @abstractmethod
    def calculate_surprise_factors(self, actual: Dict[str, Any], estimates: Dict[str, Any]) -> Dict[str, float]:
        """Calculate earnings surprise factors"""
        pass

class EventMonitorInterface(ABC):
    """Interface for corporate event monitoring"""
    
    @abstractmethod
    def get_upcoming_events(self, days_ahead: int = 30) -> Dict[str, List[str]]:
        """Get upcoming corporate events"""
        pass
    
    @abstractmethod
    def get_recent_announcements(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent corporate announcements"""
        pass
    
    @abstractmethod
    def assess_event_impact(self, event: Dict[str, Any]) -> Tuple[str, float]:
        """Assess potential impact of an event (impact_level, score)"""
        pass
    
    @abstractmethod
    def filter_events_by_type(self, events: List[Dict[str, Any]], event_types: List[EventType]) -> List[Dict[str, Any]]:
        """Filter events by specific types"""
        pass
    
    @abstractmethod
    def get_event_calendar(self, start_date: datetime, end_date: datetime) -> Dict[str, List[Dict[str, Any]]]:
        """Get comprehensive event calendar for date range"""
        pass

# =============================================================================
# DATA STORAGE INTERFACES
# =============================================================================

class DataStorageInterface(ABC):
    """Interface for storing parsed data"""
    
    @abstractmethod
    def store_company_data(self, symbol: str, data: Dict[str, Any], data_source: DataSource) -> bool:
        """Store company data in database"""
        pass
    
    @abstractmethod
    def get_companies_to_scrape(self) -> List[str]:
        """Get list of company symbols to scrape"""
        pass
    
    @abstractmethod
    def update_scraping_status(self, symbol: str, status: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Update scraping status for a company"""
        pass
    
    @abstractmethod
    def store_scraping_result(self, result: ScrapingResult) -> bool:
        """Store scraping result with metadata"""
        pass
    
    @abstractmethod
    def get_last_scrape_time(self, symbol: str, data_source: DataSource) -> Optional[datetime]:
        """Get last successful scrape time for symbol and source"""
        pass
    
    @abstractmethod
    def cleanup_old_data(self, days_to_keep: int = 365) -> int:
        """Cleanup old scraped data and return count of deleted records"""
        pass

class CacheInterface(ABC):
    """Interface for caching scraped data"""
    
    @abstractmethod
    def get_cached_data(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached data by key"""
        pass
    
    @abstractmethod
    def set_cached_data(self, key: str, data: Dict[str, Any], ttl_seconds: int = 3600) -> bool:
        """Set cached data with TTL"""
        pass
    
    @abstractmethod
    def invalidate_cache(self, pattern: str) -> int:
        """Invalidate cache entries matching pattern"""
        pass
    
    @abstractmethod
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        pass

# =============================================================================
# ANALYSIS INTERFACES
# =============================================================================

class FundamentalAnalyzerInterface(ABC):
    """Interface for fundamental analysis"""
    
    @abstractmethod
    def analyze_fundamentals(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform fundamental analysis on company data"""
        pass
    
    @abstractmethod
    def calculate_intrinsic_value(self, financial_data: Dict[str, Any]) -> Optional[float]:
        """Calculate intrinsic value of the company"""
        pass
    
    @abstractmethod
    def assess_financial_health(self, financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall financial health"""
        pass
    
    @abstractmethod
    def compare_with_peers(self, symbol: str, peer_symbols: List[str]) -> Dict[str, Any]:
        """Compare company with industry peers"""
        pass
    
    @abstractmethod
    def generate_fundamental_score(self, analysis_data: Dict[str, Any]) -> float:
        """Generate overall fundamental score (0-100)"""
        pass

class TechnicalAnalyzerInterface(ABC):
    """Interface for technical analysis"""
    
    @abstractmethod
    def calculate_indicators(self, market_data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        pass
    
    @abstractmethod
    def generate_signals(self, market_data: pd.DataFrame) -> List[TradingSignal]:
        """Generate trading signals from market data"""
        pass
    
    @abstractmethod
    def analyze_patterns(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze chart patterns"""
        pass
    
    @abstractmethod
    def calculate_support_resistance(self, market_data: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate support and resistance levels"""
        pass
    
    @abstractmethod
    def assess_trend_strength(self, market_data: pd.DataFrame) -> Dict[str, Any]:
        """Assess trend strength and direction"""
        pass

# =============================================================================
# TRADING SIGNAL GENERATION INTERFACES
# =============================================================================

class TradingSignalGeneratorInterface(ABC):
    """Interface for generating trading signals"""
    
    @abstractmethod
    def generate_signals(self, analysis_data: AnalysisData) -> List[TradingSignal]:
        """Generate trading signals from analysis data"""
        pass
    
    @abstractmethod
    def combine_signals(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """Combine multiple signals into a composite signal"""
        pass
    
    @abstractmethod
    def filter_signals_by_confidence(self, signals: List[TradingSignal], min_confidence: float) -> List[TradingSignal]:
        """Filter signals by minimum confidence threshold"""
        pass
    
    @abstractmethod
    def rank_signals_by_priority(self, signals: List[TradingSignal]) -> List[TradingSignal]:
        """Rank signals by trading priority"""
        pass
    
    @abstractmethod
    def validate_signal_consistency(self, signal: TradingSignal) -> Tuple[bool, List[str]]:
        """Validate signal for consistency and completeness"""
        pass

class RiskManagerInterface(ABC):
    """Interface for risk management"""
    
    @abstractmethod
    def assess_position_risk(self, signal: TradingSignal, portfolio_context: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risk for a potential position"""
        pass
    
    @abstractmethod
    def calculate_position_size(self, signal: TradingSignal, available_capital: float) -> float:
        """Calculate recommended position size"""
        pass
    
    @abstractmethod
    def set_stop_loss_target(self, signal: TradingSignal, market_data: pd.DataFrame) -> Tuple[float, float]:
        """Set stop loss and target prices"""
        pass
    
    @abstractmethod
    def monitor_portfolio_risk(self, current_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Monitor overall portfolio risk"""
        pass

# =============================================================================
# ORCHESTRATION INTERFACES
# =============================================================================

class CompanyPrioritizerInterface(ABC):
    """Interface for intelligent company prioritization"""
    
    @abstractmethod
    def get_priority_companies(self, max_companies: int = 50) -> List[CompanyPriority]:
        """Get prioritized list of companies for analysis"""
        pass
    
    @abstractmethod
    def score_company_priority(self, symbol: str) -> CompanyPriority:
        """Calculate priority score for a single company"""
        pass
    
    @abstractmethod
    def filter_by_criteria(self, companies: List[str], criteria: Dict[str, Any]) -> List[str]:
        """Filter companies by specific criteria"""
        pass
    
    @abstractmethod
    def update_priority_scores(self, symbols: List[str]) -> Dict[str, float]:
        """Update priority scores for given symbols"""
        pass

class ScrapingOrchestratorInterface(ABC):
    """Interface for orchestrating the complete scraping process"""
    
    @abstractmethod
    def scrape_company(self, symbol: str) -> ScrapingResult:
        """Scrape data for a single company"""
        pass
    
    @abstractmethod
    def scrape_all_companies(self) -> Dict[str, Any]:
        """Scrape data for all companies"""
        pass
    
    @abstractmethod
    def scrape_priority_companies(self, max_companies: int = 50) -> Dict[str, Any]:
        """Scrape data for prioritized companies only"""
        pass
    
    @abstractmethod
    def execute_comprehensive_analysis(self) -> Dict[str, Any]:
        """Execute comprehensive analysis pipeline"""
        pass
    
    @abstractmethod
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current status of orchestration process"""
        pass

class TradingWorkflowInterface(ABC):
    """Interface for complete trading workflow"""
    
    @abstractmethod
    def execute_trading_cycle(self) -> Dict[str, Any]:
        """Execute complete trading analysis cycle"""
        pass
    
    @abstractmethod
    def generate_trading_report(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive trading report"""
        pass
    
    @abstractmethod
    def monitor_signal_performance(self, signals: List[TradingSignal]) -> Dict[str, Any]:
        """Monitor performance of generated signals"""
        pass
    
    @abstractmethod
    def update_trading_parameters(self, new_parameters: Dict[str, Any]) -> bool:
        """Update trading system parameters"""
        pass

# =============================================================================
# INTEGRATION INTERFACES
# =============================================================================

class MarketDataProviderInterface(ABC):
    """Interface for market data providers (like Fyers)"""
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data"""
        pass
    
    @abstractmethod
    def get_live_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live market data"""
        pass
    
    @abstractmethod
    def get_batch_data(self, symbols: List[str], timeframe: str = "D") -> Dict[str, pd.DataFrame]:
        """Get batch historical data for multiple symbols"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status"""
        pass
    
    @abstractmethod
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status"""
        pass

class NotificationInterface(ABC):
    """Interface for sending notifications"""
    
    @abstractmethod
    def send_signal_alert(self, signal: TradingSignal) -> bool:
        """Send trading signal alert"""
        pass
    
    @abstractmethod
    def send_system_alert(self, message: str, priority: str = "MEDIUM") -> bool:
        """Send system alert"""
        pass
    
    @abstractmethod
    def send_daily_report(self, report_data: Dict[str, Any]) -> bool:
        """Send daily trading report"""
        pass

# =============================================================================
# PERFORMANCE MONITORING INTERFACES
# =============================================================================

class PerformanceMonitorInterface(ABC):
    """Interface for monitoring system performance"""
    
    @abstractmethod
    def track_scraping_performance(self, symbol: str, duration_ms: int, success: bool) -> None:
        """Track scraping performance metrics"""
        pass
    
    @abstractmethod
    def track_signal_performance(self, signal: TradingSignal, actual_return: Optional[float] = None) -> None:
        """Track trading signal performance"""
        pass
    
    @abstractmethod
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get comprehensive system performance metrics"""
        pass
    
    @abstractmethod
    def generate_performance_report(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate performance report for date range"""
        pass

# =============================================================================
# UTILITY INTERFACES
# =============================================================================

class DataValidatorInterface(ABC):
    """Interface for data validation"""
    
    @abstractmethod
    def validate_financial_data(self, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate financial data consistency"""
        pass
    
    @abstractmethod
    def validate_market_data(self, data: pd.DataFrame) -> Tuple[bool, List[str]]:
        """Validate market data quality"""
        pass
    
    @abstractmethod
    def sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize and clean data"""
        pass

class ConfigurationInterface(ABC):
    """Interface for system configuration management"""
    
    @abstractmethod
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get scraping configuration"""
        pass
    
    @abstractmethod
    def get_trading_config(self) -> Dict[str, Any]:
        """Get trading configuration"""
        pass
    
    @abstractmethod
    def update_config(self, section: str, config: Dict[str, Any]) -> bool:
        """Update configuration section"""
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate configuration parameters"""
        pass

# =============================================================================
# TYPE ALIASES FOR COMPLEX TYPES
# =============================================================================

# Common type aliases used throughout the system
CompanySymbol = str
PriceData = float
ConfidenceScore = float  # 0.0 to 1.0
QualityScore = float     # 0.0 to 1.0
PriorityScore = float    # 0.0 to 100.0
TimeSeriesData = pd.DataFrame
FinancialMetrics = Dict[str, Union[float, int, str]]
EventData = Dict[str, Any]
AnalysisResults = Dict[str, Any]
TradingParameters = Dict[str, Any]
SystemMetrics = Dict[str, Any]

# =============================================================================
# INTERFACE REGISTRY
# =============================================================================

class InterfaceRegistry:
    """Registry to track and validate interface implementations"""
    
    _interfaces = {
        # Core scraping interfaces
        'web_scraper': WebScraperInterface,
        'data_parser': DataParserInterface,
        'xbrl_processor': XBRLProcessorInterface,
        'quarterly_processor': QuarterlyResultsProcessorInterface,
        'event_monitor': EventMonitorInterface,
        
        # Storage interfaces
        'data_storage': DataStorageInterface,
        'cache': CacheInterface,
        
        # Analysis interfaces
        'fundamental_analyzer': FundamentalAnalyzerInterface,
        'technical_analyzer': TechnicalAnalyzerInterface,
        'signal_generator': TradingSignalGeneratorInterface,
        'risk_manager': RiskManagerInterface,
        
        # Orchestration interfaces
        'company_prioritizer': CompanyPrioritizerInterface,
        'scraping_orchestrator': ScrapingOrchestratorInterface,
        'trading_workflow': TradingWorkflowInterface,
        
        # Integration interfaces
        'market_data_provider': MarketDataProviderInterface,
        'notification': NotificationInterface,
        'performance_monitor': PerformanceMonitorInterface,
        
        # Utility interfaces
        'data_validator': DataValidatorInterface,
        'configuration': ConfigurationInterface,
    }
    
    @classmethod
    def get_interface(cls, name: str) -> Optional[type]:
        """Get interface class by name"""
        return cls._interfaces.get(name)
    
    @classmethod
    def list_interfaces(cls) -> List[str]:
        """List all available interface names"""
        return list(cls._interfaces.keys())
    
    @classmethod
    def validate_implementation(cls, name: str, implementation: Any) -> bool:
        """Validate if implementation satisfies the interface"""
        interface_class = cls.get_interface(name)
        if interface_class:
            return isinstance(implementation, interface_class)
        return False
