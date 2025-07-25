# apps/market_data_service/models.py
from django.db import models
from django.db.models import JSONField  # ✅ Fixed: Use built-in JSONField instead
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from typing import Dict, Any, Optional
from django.utils import timezone


class Company(models.Model):
    """Single responsibility: Store basic company information only"""
    symbol = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=200)
    about = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bse_code = models.CharField(max_length=20, blank=True, null=True)
    nse_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Foreign key relationships instead of storing data directly
    industry_classification = models.ForeignKey(
        'IndustryClassification', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    
    # ✅ Trading-specific fields
    is_active = models.BooleanField(default=True)
    is_tradeable = models.BooleanField(default=True)  # Can we trade this stock?
    fyers_symbol = models.CharField(max_length=50, null=True, blank=True)  # Cached Fyers symbol
    last_signal_generated = models.DateTimeField(null=True, blank=True)
    signal_frequency = models.CharField(
        max_length=20,
        choices=[
            ('high', 'High Frequency'),  # Multiple signals per day
            ('medium', 'Medium Frequency'),  # Daily signals
            ('low', 'Low Frequency'),  # Weekly signals
        ],
        default='medium'
    )
    
    # ✅ Performance tracking
    successful_trades = models.IntegerField(default=0)
    total_trades = models.IntegerField(default=0)
    average_return = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Success percentage
    
    # ✅ Scraping optimization
    last_scraped = models.DateTimeField(null=True, blank=True)
    scraping_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('event_driven', 'Event Driven'),
        ],
        default='event_driven'
    )
    scraping_priority = models.IntegerField(default=50)  # 0-100, higher = more priority
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_tradeable']),
            models.Index(fields=['last_scraped']),
            models.Index(fields=['scraping_priority']),
            models.Index(fields=['signal_frequency']),
        ]
    
    def get_latest_fundamental_data(self) -> Optional[Dict[str, Any]]:
        """Get latest fundamental data combining all sources"""
        try:
            valuation = getattr(self, 'valuation_metrics', None)
            profitability = getattr(self, 'profitability_metrics', None)
            growth = getattr(self, 'growth_metrics', None)
            
            if not any([valuation, profitability, growth]):
                return None
            
            return {
                'market_cap': valuation.market_cap if valuation else None,
                'pe_ratio': valuation.stock_pe if valuation else None,
                'roe': profitability.roe if profitability else None,
                'roce': profitability.roce if profitability else None,
                'revenue_growth': growth.sales_growth_1y if growth else None,
                'profit_growth': growth.profit_growth_1y if growth else None,
            }
        except Exception:
            return None
    
    def calculate_trading_score(self) -> float:
        """Calculate overall trading attractiveness score"""
        try:
            score = 0.0
            
            # Fundamental score (40%)
            fundamental_score = getattr(self, 'fundamental_score', None)
            if fundamental_score:
                score += float(fundamental_score.overall_score) * 0.4
            
            # Recent performance (30%)
            if self.total_trades > 0:
                score += float(self.win_rate or 0) * 0.3
            else:
                score += 50 * 0.3  # Neutral for new companies
            
            # Event activity (20%)
            recent_events = self.corporateevent_set.filter(
                announcement_date__gte=timezone.now() - timezone.timedelta(days=30)
            ).count()
            score += min(recent_events * 10, 20)  # Max 20 points
            
            # Data freshness (10%)
            if self.last_scraped:
                days_since_scrape = (timezone.now() - self.last_scraped).days
                freshness_score = max(0, 10 - days_since_scrape)
                score += min(freshness_score, 10)
            
            return min(score, 100.0)
            
        except Exception:
            return 50.0  # Default score
    
    def __str__(self):
        return f"{self.symbol} - {self.name}"


class IndustryClassification(models.Model):
    """Single responsibility: Industry hierarchy management"""
    name = models.CharField(max_length=200, unique=True)
    parent = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        related_name='children'
    )
    level = models.PositiveIntegerField(default=0)
    sector_weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)  # For sector analysis
    
    class Meta:
        db_table = 'industry_classifications'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['level']),
        ]
    
    def __str__(self):
        return self.name


class ValuationMetrics(models.Model):
    """Single responsibility: Store valuation-related metrics"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='valuation_metrics'
    )
    
    # Price metrics
    market_cap = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    current_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    high_52_week = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    low_52_week = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Valuation ratios
    stock_pe = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    book_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_to_book = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    dividend_yield = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    face_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Additional ratios
    ev_ebitda = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_to_sales = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_to_earnings_growth = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # PEG ratio
    
    # ✅ Market sentiment indicators
    beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    volatility_30d = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    relative_strength = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'valuation_metrics'
        indexes = [
            models.Index(fields=['market_cap']),
            models.Index(fields=['stock_pe']),
            models.Index(fields=['updated_at']),
        ]


class ProfitabilityMetrics(models.Model):
    """Single responsibility: Store profitability metrics"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='profitability_metrics'
    )
    
    # Return ratios
    roce = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    roe = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    roa = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    roic = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Return on Invested Capital
    
    # Margin ratios
    net_profit_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    operating_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    gross_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ebitda_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Additional profitability metrics
    asset_turnover = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    inventory_turnover = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    receivables_turnover = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profitability_metrics'
        indexes = [
            models.Index(fields=['roe']),
            models.Index(fields=['roce']),
            models.Index(fields=['net_profit_margin']),
        ]


class FinancialStatement(models.Model):
    """Single responsibility: Store financial statement data"""
    STATEMENT_TYPES = (
        ('quarterly_results', 'Quarterly Results'),
        ('annual_xbrl', 'Annual Results (XBRL)'),
        ('profit_loss', 'Profit & Loss'),
        ('balance_sheet', 'Balance Sheet'),
        ('cash_flow', 'Cash Flow'),
        ('ratios', 'Financial Ratios'),
    )
    
    DATA_SOURCES = (
        ('xbrl', 'XBRL File'),
        ('nse_scrape', 'NSE Website'),
        ('screener', 'Screener.in'),
        ('rss', 'RSS Feed'),
        ('manual', 'Manual Entry'),
    )
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    data_source = models.CharField(max_length=20, choices=DATA_SOURCES)
    period = models.CharField(max_length=20, null=True, blank=True)  # Q1FY24, FY2024, etc.
    year = models.IntegerField(null=True, blank=True)
    quarter = models.CharField(max_length=10, null=True, blank=True)
    
    # ✅ Fixed JSONField imports
    raw_data = JSONField(default=dict)
    processed_metrics = JSONField(default=dict)
    validation_errors = JSONField(default=list)
    
    # ✅ Quality and validation
    data_quality_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.0)  # 0-1
    is_validated = models.BooleanField(default=False)
    
    # Metadata
    filing_date = models.DateTimeField(null=True, blank=True)
    announcement_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'financial_statements'
        unique_together = ['company', 'statement_type', 'data_source', 'period']
        indexes = [
            models.Index(fields=['company', 'statement_type']),
            models.Index(fields=['announcement_date']),
            models.Index(fields=['filing_date']),
            models.Index(fields=['data_quality_score']),
            models.Index(fields=['is_validated']),
        ]


class GrowthMetrics(models.Model):
    """Single responsibility: Store growth-related data"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='growth_metrics'
    )
    
    # Sales Growth (CAGR)
    sales_growth_10y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    sales_growth_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    sales_growth_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    sales_growth_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    sales_growth_ttm = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # Profit Growth (CAGR)
    profit_growth_10y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    profit_growth_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    profit_growth_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    profit_growth_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    profit_growth_ttm = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # Stock Price Growth (CAGR)
    stock_cagr_10y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    stock_cagr_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    stock_cagr_3y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    stock_cagr_1y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # ✅ Additional growth metrics
    book_value_growth_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    dividend_growth_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    eps_growth_5y = models.DecimalField(max_digits=8, decimal_places=2, null=True)
    
    # ✅ Fixed JSONField imports
    quarterly_revenue_growth = JSONField(default=dict)  # {"Q1FY24": 15.2, "Q2FY24": 12.5}
    quarterly_profit_growth = JSONField(default=dict)
    
    # ✅ Growth consistency metrics
    revenue_growth_consistency = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # 0-100
    profit_growth_consistency = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # 0-100
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'growth_metrics'
        indexes = [
            models.Index(fields=['sales_growth_1y']),
            models.Index(fields=['profit_growth_1y']),
            models.Index(fields=['revenue_growth_consistency']),
        ]


class QualitativeAnalysis(models.Model):
    """Single responsibility: Store qualitative analysis data"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='qualitative_analysis'
    )
    
    # ✅ Fixed JSONField imports
    pros = JSONField(default=list)
    cons = JSONField(default=list)
    
    # Additional qualitative metrics
    management_quality_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    business_model_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    competitive_advantage_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    
    # ✅ ESG and governance metrics
    esg_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    governance_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    sustainability_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'qualitative_analysis'


class ShareholdingPattern(models.Model):
    """Single responsibility: Store shareholding data"""
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    pattern_type = models.CharField(max_length=20, default='quarterly')
    period = models.CharField(max_length=20)  # Q1FY24, Q2FY24, etc.
    
    # Shareholding data
    promoter_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    public_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    institutional_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Detailed shareholding breakdown
    fii_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    dii_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    mutual_fund_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    retail_holding = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Fixed JSONField import
    raw_data = JSONField(default=dict)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shareholding_patterns'
        unique_together = ['company', 'pattern_type', 'period']
        indexes = [
            models.Index(fields=['period']),
            models.Index(fields=['promoter_holding']),
            models.Index(fields=['institutional_holding']),
        ]


class CorporateEvent(models.Model):
    """✅ ENHANCED: Store corporate events and announcements"""
    EVENT_TYPES = (
        ('results_announcement', 'Results Announcement'),
        ('order_received', 'Order/Contract Received'), 
        ('dividend', 'Dividend Declaration'),
        ('bonus', 'Bonus Issue'),
        ('rights', 'Rights Issue'),
        ('buyback', 'Share Buyback'),
        ('merger', 'Merger & Acquisition'),
        ('delisting', 'Delisting'),
        ('agm', 'Annual General Meeting'),
        ('board_meeting', 'Board Meeting'),
        ('other', 'Other'),
    )
    
    IMPACT_LEVELS = (
        ('HIGH', 'High Impact'),
        ('MEDIUM', 'Medium Impact'),
        ('LOW', 'Low Impact'),
    )
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPES)
    title = models.CharField(max_length=500)
    description = models.TextField()
    
    # Event timing
    announcement_date = models.DateTimeField()
    event_date = models.DateField(null=True, blank=True)  # When the event will happen
    
    # Impact assessment
    impact_level = models.CharField(max_length=10, choices=IMPACT_LEVELS, default='LOW')
    expected_price_impact = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Trading integration fields
    signal_generated = models.BooleanField(default=False)  # Has this event generated a signal?
    signal_action = models.CharField(
        max_length=10, 
        choices=[('BUY', 'Buy'), ('SELL', 'Sell'), ('HOLD', 'Hold')],
        null=True, blank=True
    )
    price_before_event = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_after_event = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    actual_price_impact = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Event outcome tracking
    event_outcome = models.CharField(
        max_length=20,
        choices=[
            ('positive', 'Positive'),
            ('negative', 'Negative'),
            ('neutral', 'Neutral'),
            ('pending', 'Pending'),
        ],
        default='pending'
    )
    outcome_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True)  # 0-1
    
    # ✅ Fixed JSONField import
    event_data = JSONField(default=dict)  # Store event-specific data
    
    # Data source tracking
    data_source = models.CharField(max_length=20)  # rss, calendar, scraper
    source_url = models.URLField(null=True, blank=True)
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    processing_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'corporate_events'
        indexes = [
            models.Index(fields=['company', 'event_type']),
            models.Index(fields=['announcement_date']),
            models.Index(fields=['event_date']),
            models.Index(fields=['impact_level']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['signal_generated']),
            models.Index(fields=['event_outcome']),
        ]


class FundamentalScore(models.Model):
    """Single responsibility: Store computed fundamental scores"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='fundamental_score'
    )
    
    # Component scores (0-100)
    valuation_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    profitability_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    growth_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    financial_health_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    qualitative_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # ✅ Additional scoring dimensions
    momentum_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    quality_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    dividend_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Overall composite score (0-100)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # ✅ Score trends
    score_trend_30d = models.CharField(
        max_length=10,
        choices=[('UP', 'Improving'), ('DOWN', 'Declining'), ('STABLE', 'Stable')],
        default='STABLE'
    )
    previous_score = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    score_change = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Score metadata
    calculation_date = models.DateTimeField(auto_now=True)
    data_freshness_days = models.IntegerField(default=0)  # How old is the underlying data
    confidence_level = models.DecimalField(max_digits=3, decimal_places=2, default=0)  # 0-1
    
    # ✅ Fixed JSONField import
    score_breakdown = JSONField(default=dict)
    
    class Meta:
        db_table = 'fundamental_scores'
        indexes = [
            models.Index(fields=['overall_score']),
            models.Index(fields=['calculation_date']),
            models.Index(fields=['score_trend_30d']),
            models.Index(fields=['confidence_level']),
        ]


class TradingSignal(models.Model):
    """Store generated trading signals for tracking and analysis"""
    
    SIGNAL_TYPES = (
        ('efi_crossover', 'EFI Crossover'),
        ('fundamental', 'Fundamental Analysis'),
        ('event_driven', 'Event Driven'),
        ('composite', 'Composite Signal'),
        ('momentum', 'Momentum Signal'),
        ('breakout', 'Technical Breakout'),
        ('reversal', 'Trend Reversal'),
    )
    
    ACTIONS = (
        ('BUY', 'Buy'),
        ('SELL', 'Sell'), 
        ('HOLD', 'Hold'),
        ('STRONG_BUY', 'Strong Buy'),
        ('STRONG_SELL', 'Strong Sell'),
        ('AVOID', 'Avoid'),
    )
    
    RISK_LEVELS = (
        ('LOW', 'Low Risk'),
        ('MEDIUM', 'Medium Risk'),
        ('HIGH', 'High Risk'),
        ('VERY_HIGH', 'Very High Risk'),
    )
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    signal_type = models.CharField(max_length=20, choices=SIGNAL_TYPES)
    action = models.CharField(max_length=15, choices=ACTIONS)
    
    # Signal strength metrics
    confidence = models.DecimalField(max_digits=3, decimal_places=2)  # 0.00 to 1.00
    signal_strength = models.DecimalField(max_digits=3, decimal_places=2, default=0.5)  # 0.00 to 1.00
    urgency = models.CharField(
        max_length=10,
        choices=[('LOW', 'Low'), ('MEDIUM', 'Medium'), ('HIGH', 'High')],
        default='MEDIUM'
    )
    
    # Price information
    price_at_signal = models.DecimalField(max_digits=10, decimal_places=2)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stop_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Risk management
    risk_level = models.CharField(max_length=10, choices=RISK_LEVELS, default='MEDIUM')
    position_size_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Recommended %
    max_loss_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Max acceptable loss %
    
    # ✅ Fixed JSONField imports
    data_sources = JSONField(default=list)  # ['fundamental', 'technical', 'event']
    signal_reasons = JSONField(default=list)
    component_signals = JSONField(default=dict)  # Breakdown of contributing signals
    
    # Market context
    market_condition = models.CharField(
        max_length=15,
        choices=[
            ('BULLISH', 'Bullish'),
            ('BEARISH', 'Bearish'),
            ('SIDEWAYS', 'Sideways'),
            ('VOLATILE', 'Volatile'),
        ],
        null=True, blank=True
    )
    sector_sentiment = models.CharField(max_length=15, null=True, blank=True)
    
    # Execution tracking
    is_executed = models.BooleanField(default=False)
    execution_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    execution_date = models.DateTimeField(null=True, blank=True)
    execution_notes = models.TextField(blank=True)
    
    # Performance tracking
    is_closed = models.BooleanField(default=False)
    close_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    close_date = models.DateTimeField(null=True, blank=True)
    close_reason = models.CharField(
        max_length=20,
        choices=[
            ('TARGET_HIT', 'Target Hit'),
            ('STOP_LOSS', 'Stop Loss'),
            ('TIME_DECAY', 'Time Decay'),
            ('SIGNAL_CHANGE', 'Signal Change'),
            ('MANUAL', 'Manual Close'),
        ],
        null=True, blank=True
    )
    
    # P&L tracking
    profit_loss = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    profit_loss_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    holding_period_days = models.IntegerField(null=True)
    
    # Signal validation
    signal_accuracy = models.DecimalField(max_digits=3, decimal_places=2, null=True)  # Post-analysis accuracy
    validation_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_signals'
        indexes = [
            models.Index(fields=['company', 'created_at']),
            models.Index(fields=['action', 'confidence']),
            models.Index(fields=['is_executed', 'is_closed']),
            models.Index(fields=['signal_type', 'action']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['urgency']),
            models.Index(fields=['profit_loss_pct']),
        ]
    
    def calculate_return(self) -> Optional[float]:
        """Calculate return percentage"""
        if self.execution_price and self.close_price:
            if self.action in ['BUY', 'STRONG_BUY']:
                return float((self.close_price - self.execution_price) / self.execution_price * 100)
            elif self.action in ['SELL', 'STRONG_SELL']:
                return float((self.execution_price - self.close_price) / self.execution_price * 100)
        return None
    
    def update_performance_metrics(self):
        """Update performance metrics after position close"""
        if self.is_closed and self.execution_price and self.close_price:
            self.profit_loss_pct = self.calculate_return()
            if self.execution_date and self.close_date:
                self.holding_period_days = (self.close_date - self.execution_date).days
            self.save()


class MarketDataCache(models.Model):
    """Cache market data for performance optimization"""
    
    symbol = models.CharField(max_length=20)
    data_type = models.CharField(
        max_length=20,
        choices=[
            ('HISTORICAL', 'Historical OHLCV'),
            ('LIVE', 'Live Quote'),
            ('TECHNICAL', 'Technical Indicators'),
            ('VOLUME', 'Volume Analysis'),
        ]
    )
    timeframe = models.CharField(max_length=10, default='D')  # D, H, 5M, etc.
    
    # ✅ Fixed JSONField import
    data = JSONField(default=dict)
    data_quality = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    
    # Cache metadata
    cache_key = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    hit_count = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'market_data_cache'
        indexes = [
            models.Index(fields=['symbol', 'data_type']),
            models.Index(fields=['cache_key']),
            models.Index(fields=['expires_at']),
        ]


class SystemPerformanceMetrics(models.Model):
    """Track system performance and health metrics"""
    
    metric_type = models.CharField(
        max_length=30,
        choices=[
            ('SCRAPING_PERFORMANCE', 'Scraping Performance'),
            ('SIGNAL_ACCURACY', 'Signal Accuracy'),
            ('API_PERFORMANCE', 'API Performance'),
            ('SYSTEM_HEALTH', 'System Health'),
            ('TRADING_PERFORMANCE', 'Trading Performance'),
        ]
    )
    
    metric_name = models.CharField(max_length=50)
    metric_value = models.DecimalField(max_digits=10, decimal_places=4)
    metric_unit = models.CharField(max_length=20, null=True, blank=True)  # %, ms, count, etc.
    
    # ✅ Fixed JSONField import
    context_data = JSONField(default=dict)
    
    # Aggregation period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_performance_metrics'
        indexes = [
            models.Index(fields=['metric_type', 'metric_name']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['created_at']),
        ]


class Watchlist(models.Model):
    """Manage custom watchlists for focused analysis"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    # Watchlist settings
    is_active = models.BooleanField(default=True)
    auto_update = models.BooleanField(default=True)
    priority = models.IntegerField(default=50)  # 0-100
    
    # ✅ Fixed JSONField import
    filter_criteria = JSONField(default=dict)  # Dynamic filtering rules
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'watchlists'


class WatchlistItem(models.Model):
    """Individual items in watchlists"""
    
    watchlist = models.ForeignKey(Watchlist, on_delete=models.CASCADE)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    
    # Item-specific settings
    weight = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    notes = models.TextField(blank=True)
    
    # ✅ Fixed JSONField import
    auto_remove_criteria = JSONField(default=dict)
    
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'watchlist_items'
        unique_together = ['watchlist', 'company']
