# apps/market_data_service/models.py
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from typing import Dict, Any, Optional

class Company(models.Model):
    """Single responsibility: Store basic company information only"""
    symbol = models.CharField(max_length=20, primary_key=True)
    name = models.CharField(max_length=200)
    about = models.TextField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    bse_code = models.CharField(max_length=20, blank=True, null=True)
    nse_code = models.CharField(max_length=20, blank=True, null=True)
    
    # Industry classification
    industry_classification = models.ForeignKey(
        'IndustryClassification', 
        on_delete=models.SET_NULL, 
        null=True, blank=True
    )
    
    # Operational fields
    is_active = models.BooleanField(default=True)
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
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'companies'
        indexes = [
            models.Index(fields=['symbol']),
            models.Index(fields=['is_active']),
            models.Index(fields=['last_scraped']),
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
    
    class Meta:
        db_table = 'industry_classifications'
    
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
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'valuation_metrics'

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
    
    # Margin ratios
    net_profit_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    operating_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    gross_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    ebitda_margin = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'profitability_metrics'

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
    )
    
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    statement_type = models.CharField(max_length=20, choices=STATEMENT_TYPES)
    data_source = models.CharField(max_length=20, choices=DATA_SOURCES)
    period = models.CharField(max_length=20, null=True, blank=True)  # Q1FY24, FY2024, etc.
    year = models.IntegerField(null=True, blank=True)
    quarter = models.CharField(max_length=10, null=True, blank=True)
    
    # Raw data storage
    raw_data = JSONField(default=dict)
    
    # Processed metrics
    processed_metrics = JSONField(default=dict)
    
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
    
    # Quarterly growth rates
    quarterly_revenue_growth = JSONField(default=dict)  # {"Q1FY24": 15.2, "Q2FY24": 12.5}
    quarterly_profit_growth = JSONField(default=dict)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'growth_metrics'

class QualitativeAnalysis(models.Model):
    """Single responsibility: Store qualitative analysis data"""
    company = models.OneToOneField(
        Company, 
        on_delete=models.CASCADE, 
        related_name='qualitative_analysis'
    )
    pros = JSONField(default=list)
    cons = JSONField(default=list)
    
    # Additional qualitative metrics
    management_quality_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    business_model_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    competitive_advantage_score = models.DecimalField(max_digits=3, decimal_places=1, null=True)
    
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
    
    # Raw shareholding data
    raw_data = JSONField(default=dict)
    
    data_source = models.CharField(max_length=20, default='screener')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'shareholding_patterns'
        unique_together = ['company', 'pattern_type', 'period']

class CorporateEvent(models.Model):
    """Single responsibility: Store corporate events and announcements"""
    EVENT_TYPES = (
        ('results_announcement', 'Results Announcement'),
        ('order_received', 'Order/Contract Received'), 
        ('dividend', 'Dividend Declaration'),
        ('bonus', 'Bonus Issue'),
        ('rights', 'Rights Issue'),
        ('buyback', 'Share Buyback'),
        ('merger', 'Merger & Acquisition'),
        ('delisting', 'Delisting'),
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
    
    # Additional data
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
    
    # Overall composite score (0-100)
    overall_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Score metadata
    calculation_date = models.DateTimeField(auto_now=True)
    data_freshness_days = models.IntegerField(default=0)  # How old is the underlying data
    confidence_level = models.DecimalField(max_digits=3, decimal_places=2, default=0)  # 0-1
    
    # Score breakdown for transparency
    score_breakdown = JSONField(default=dict)
    
    class Meta:
        db_table = 'fundamental_scores'
        indexes = [
            models.Index(fields=['overall_score']),
            models.Index(fields=['calculation_date']),
        ]
