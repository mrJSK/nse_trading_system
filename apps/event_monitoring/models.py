# apps/event_monitoring/models.py - CREATE THIS FILE

from django.db import models
from django.contrib.postgres.fields import JSONField

class EventSource(models.Model):
    """Track different event data sources"""
    
    SOURCE_TYPES = (
        ('NSE_RSS', 'NSE RSS Feed'),
        ('NSE_CALENDAR', 'NSE Event Calendar'),
        ('COMPANY_WEBSITE', 'Company Website'),
        ('NEWS_API', 'News API'),
        ('MANUAL', 'Manual Entry'),
    )
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    url = models.URLField(null=True, blank=True)
    
    # Source configuration
    polling_interval_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    last_check = models.DateTimeField(null=True, blank=True)
    
    # Performance metrics
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    average_response_time_ms = models.IntegerField(null=True)
    total_events_collected = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'event_sources'

class EventCalendar(models.Model):
    """Store upcoming events from NSE calendar"""
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    event_date = models.DateField()
    event_type = models.CharField(max_length=50)
    description = models.TextField()
    
    # Calendar-specific fields
    calendar_category = models.CharField(
        max_length=20,
        choices=[('EQUITY', 'Equity'), ('SME', 'SME')]
    )
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    has_generated_alert = models.BooleanField(default=False)
    
    # Link to actual event when it occurs
    actual_event = models.ForeignKey(
        'market_data_service.CorporateEvent',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    source = models.ForeignKey(EventSource, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_calendar'
        unique_together = ['company', 'event_date', 'event_type']
        indexes = [
            models.Index(fields=['event_date']),
            models.Index(fields=['is_processed']),
        ]
