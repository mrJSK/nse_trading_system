from django.db import models

# Create your models here.
# apps/technical_analysis/models.py - CREATE THIS FILE

from django.db import models
from django.contrib.postgres.fields import JSONField
import pandas as pd

class TechnicalIndicator(models.Model):
    """Store calculated technical indicators for companies"""
    
    INDICATOR_TYPES = (
        ('EFI', 'Ease of Flow Index'),
        ('RSI', 'Relative Strength Index'),
        ('MACD', 'MACD'),
        ('SMA', 'Simple Moving Average'),
        ('EMA', 'Exponential Moving Average'),
        ('BOLLINGER', 'Bollinger Bands'),
        ('VOLUME', 'Volume Analysis'),
        ('ATR', 'Average True Range'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    timeframe = models.CharField(max_length=10, default='D')  # D, H, 15M, etc.
    
    # Indicator parameters
    parameters = JSONField(default=dict)  # {"period": 20, "threshold": 0.0}
    
    # Calculated values
    current_value = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    previous_value = models.DecimalField(max_digits=10, decimal_places=6, null=True)
    signal = models.CharField(
        max_length=10,
        choices=[('BUY', 'Buy'), ('SELL', 'Sell'), ('NEUTRAL', 'Neutral')],
        default='NEUTRAL'
    )
    
    # Historical data (last 50 values for trend analysis)
    historical_values = JSONField(default=list)
    
    # Signal generation
    crossover_detected = models.BooleanField(default=False)
    crossover_direction = models.CharField(
        max_length=10,
        choices=[('UP', 'Upward'), ('DOWN', 'Downward')],
        null=True, blank=True
    )
    signal_strength = models.DecimalField(max_digits=3, decimal_places=2, default=0.5)
    
    calculation_timestamp = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'technical_indicators'
        unique_together = ['company', 'indicator_type', 'timeframe']
        indexes = [
            models.Index(fields=['company', 'indicator_type']),
            models.Index(fields=['signal', 'crossover_detected']),
            models.Index(fields=['calculation_timestamp']),
        ]

class MarketData(models.Model):
    """Store OHLCV market data from Fyers"""
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    timeframe = models.CharField(max_length=10)  # D, H, 15M, 5M, 1M
    
    # OHLCV data
    timestamp = models.DateTimeField()
    open_price = models.DecimalField(max_digits=10, decimal_places=2)
    high_price = models.DecimalField(max_digits=10, decimal_places=2)
    low_price = models.DecimalField(max_digits=10, decimal_places=2)
    close_price = models.DecimalField(max_digits=10, decimal_places=2)
    volume = models.BigIntegerField()
    
    # Additional market data
    vwap = models.DecimalField(max_digits=10, decimal_places=2, null=True)  # Volume Weighted Average Price
    open_interest = models.BigIntegerField(null=True)  # For F&O
    
    # Data quality
    data_source = models.CharField(max_length=20, default='fyers')
    is_validated = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'market_data'
        unique_together = ['company', 'timeframe', 'timestamp']
        indexes = [
            models.Index(fields=['company', 'timeframe', 'timestamp']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['volume']),
        ]
