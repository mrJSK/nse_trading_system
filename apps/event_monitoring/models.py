# apps/event_monitoring/models.py
from django.db import models
from django.db.models import JSONField  # ✅ Fixed: Use built-in JSONField instead
from django.utils import timezone


class EventSource(models.Model):
    """Track different event data sources for NSE trading system"""
    
    SOURCE_TYPES = (
        ('NSE_RSS', 'NSE RSS Feed'),
        ('NSE_CALENDAR', 'NSE Event Calendar'),
        ('COMPANY_WEBSITE', 'Company Website'),
        ('NEWS_API', 'News API'),
        ('SCREENER_RSS', 'Screener RSS Feed'),
        ('FYERS_API', 'Fyers API Events'),
        ('MANUAL', 'Manual Entry'),
    )
    
    name = models.CharField(max_length=100)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    url = models.URLField(null=True, blank=True)
    
    # Source configuration
    polling_interval_minutes = models.IntegerField(default=30)
    is_active = models.BooleanField(default=True)
    last_check = models.DateTimeField(null=True, blank=True)
    
    # ✅ Enhanced: Additional configuration for NSE trading
    retry_attempts = models.IntegerField(default=3)
    timeout_seconds = models.IntegerField(default=30)
    rate_limit_requests_per_minute = models.IntegerField(default=60)
    
    # ✅ Enhanced: Authentication and headers
    requires_auth = models.BooleanField(default=False)
    auth_token = models.CharField(max_length=500, blank=True)
    custom_headers = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    # Performance metrics
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.0)
    average_response_time_ms = models.IntegerField(null=True)
    total_events_collected = models.IntegerField(default=0)
    last_error_message = models.TextField(blank=True)
    consecutive_failures = models.IntegerField(default=0)
    
    # ✅ Enhanced: Health monitoring
    is_healthy = models.BooleanField(default=True)
    last_successful_check = models.DateTimeField(null=True, blank=True)
    downtime_minutes = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'event_sources'
        indexes = [
            models.Index(fields=['source_type', 'is_active']),
            models.Index(fields=['is_healthy']),
            models.Index(fields=['last_check']),
        ]
    
    def mark_successful_check(self):
        """Mark a successful check and reset failure counters"""
        self.last_check = timezone.now()
        self.last_successful_check = timezone.now()
        self.is_healthy = True
        self.consecutive_failures = 0
        self.save()
    
    def mark_failed_check(self, error_message: str):
        """Mark a failed check and update failure metrics"""
        self.last_check = timezone.now()
        self.last_error_message = error_message
        self.consecutive_failures += 1
        
        # Mark as unhealthy after 3 consecutive failures
        if self.consecutive_failures >= 3:
            self.is_healthy = False
        
        self.save()
    
    def __str__(self):
        return f"{self.name} ({self.source_type})"


class EventCalendar(models.Model):
    """Store upcoming events from NSE calendar for trading system"""
    
    CALENDAR_CATEGORIES = (
        ('EQUITY', 'Equity'),
        ('SME', 'SME'),
        ('DEBT', 'Debt'),
        ('DERIVATIVES', 'Derivatives'),
    )
    
    EVENT_CATEGORIES = (
        ('RESULTS', 'Financial Results'),
        ('DIVIDEND', 'Dividend'),
        ('BONUS', 'Bonus Issue'),
        ('RIGHTS', 'Rights Issue'),
        ('AGM', 'Annual General Meeting'),
        ('BOARD_MEETING', 'Board Meeting'),
        ('BUYBACK', 'Share Buyback'),
        ('SPLIT', 'Stock Split'),
        ('MERGER', 'Merger & Acquisition'),
        ('LISTING', 'New Listing'),
        ('DELISTING', 'Delisting'),
        ('OTHER', 'Other Events'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    event_date = models.DateField()
    event_type = models.CharField(max_length=50)
    event_category = models.CharField(max_length=20, choices=EVENT_CATEGORIES, default='OTHER')
    description = models.TextField()
    
    # Calendar-specific fields
    calendar_category = models.CharField(max_length=20, choices=CALENDAR_CATEGORIES)
    
    # ✅ Enhanced: Event timing and scheduling
    event_time = models.TimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, default='Asia/Kolkata')
    is_market_hours = models.BooleanField(default=True)
    
    # ✅ Enhanced: Impact assessment
    expected_impact = models.CharField(
        max_length=10,
        choices=[('HIGH', 'High'), ('MEDIUM', 'Medium'), ('LOW', 'Low')],
        default='LOW'
    )
    impact_reason = models.CharField(max_length=200, blank=True)
    
    # ✅ Enhanced: Trading relevance
    affects_trading = models.BooleanField(default=True)
    trading_action_required = models.CharField(
        max_length=20,
        choices=[
            ('MONITOR', 'Monitor Only'),
            ('PREPARE_SIGNAL', 'Prepare Trading Signal'),
            ('IMMEDIATE_ACTION', 'Immediate Action Required'),
            ('NONE', 'No Action'),
        ],
        default='MONITOR'
    )
    
    # Processing status
    is_processed = models.BooleanField(default=False)
    has_generated_alert = models.BooleanField(default=False)
    processing_notes = models.TextField(blank=True)
    
    # ✅ Enhanced: Notification settings
    notification_sent = models.BooleanField(default=False)
    notification_channels = JSONField(default=list)  # ✅ Fixed JSONField import
    reminder_set = models.BooleanField(default=False)
    reminder_minutes_before = models.IntegerField(default=60)
    
    # Link to actual event when it occurs
    actual_event = models.ForeignKey(
        'market_data_service.CorporateEvent',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        help_text="Link to the actual corporate event when it occurs"
    )
    
    # ✅ Enhanced: Event outcome tracking
    event_occurred = models.BooleanField(default=False)
    outcome_recorded = models.BooleanField(default=False)
    outcome_notes = models.TextField(blank=True)
    
    # ✅ Enhanced: Price impact tracking
    price_before_event = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    price_after_event = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    volume_before_event = models.BigIntegerField(null=True)
    volume_after_event = models.BigIntegerField(null=True)
    
    # Source tracking
    source = models.ForeignKey(EventSource, on_delete=models.CASCADE)
    source_url = models.URLField(null=True, blank=True)
    external_id = models.CharField(max_length=100, null=True, blank=True)  # ID from external source
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'event_calendar'
        unique_together = ['company', 'event_date', 'event_type', 'source']
        indexes = [
            models.Index(fields=['event_date', 'calendar_category']),
            models.Index(fields=['is_processed', 'affects_trading']),
            models.Index(fields=['expected_impact']),
            models.Index(fields=['trading_action_required']),
            models.Index(fields=['event_occurred']),
            models.Index(fields=['company', 'event_date']),
        ]
    
    def is_due_soon(self, hours: int = 24) -> bool:
        """Check if event is due within specified hours"""
        from datetime import datetime, timedelta
        now = datetime.now().date()
        due_date = now + timedelta(hours=hours/24)
        return self.event_date <= due_date
    
    def needs_reminder(self) -> bool:
        """Check if reminder should be sent"""
        if not self.reminder_set or self.notification_sent:
            return False
        
        from datetime import datetime, timedelta
        now = datetime.now()
        reminder_time = datetime.combine(self.event_date, self.event_time or datetime.min.time())
        reminder_time -= timedelta(minutes=self.reminder_minutes_before)
        
        return now >= reminder_time
    
    def calculate_price_impact(self) -> float:
        """Calculate percentage price impact after event"""
        if self.price_before_event and self.price_after_event:
            return float((self.price_after_event - self.price_before_event) / self.price_before_event * 100)
        return 0.0
    
    def __str__(self):
        return f"{self.company.symbol} - {self.event_type} on {self.event_date}"


class TradingAlert(models.Model):
    """Store trading alerts and notifications generated by the system"""
    
    ALERT_TYPES = (
        ('EVENT_DRIVEN', 'Event Driven Alert'),
        ('HIGH_CONFIDENCE_SIGNAL', 'High Confidence Signal'),
        ('SYSTEM_ALERT', 'System Alert'),
        ('CALENDAR_REMINDER', 'Calendar Reminder'),
        ('PRICE_MOVEMENT', 'Significant Price Movement'),
        ('VOLUME_SPIKE', 'Volume Spike'),
        ('NEWS_IMPACT', 'News Impact Alert'),
        ('TECHNICAL_BREAKOUT', 'Technical Breakout'),
        ('FUNDAMENTAL_CHANGE', 'Fundamental Change'),
    )
    
    URGENCY_LEVELS = (
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical - Immediate Action'),
    )
    
    ALERT_STATUS = (
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('ACKNOWLEDGED', 'Acknowledged'),
        ('DISMISSED', 'Dismissed'),
        ('ACTED_UPON', 'Acted Upon'),
    )
    
    # Alert identification
    symbol = models.CharField(max_length=20, db_index=True)
    company = models.ForeignKey(
        'market_data_service.Company', 
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    
    # Alert classification
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='MEDIUM')
    
    # Alert content
    title = models.CharField(max_length=200)
    message = models.TextField()
    detailed_analysis = models.TextField(blank=True)
    
    # ✅ Enhanced: Alert metadata
    alert_data = JSONField(default=dict)  # ✅ Fixed JSONField import
    context_data = JSONField(default=dict)  # ✅ Fixed JSONField import
    recommended_actions = JSONField(default=list)  # ✅ Fixed JSONField import
    
    # ✅ Enhanced: Market context
    market_price_at_alert = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    market_volume_at_alert = models.BigIntegerField(null=True)
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
    
    # Alert lifecycle
    status = models.CharField(max_length=15, choices=ALERT_STATUS, default='PENDING')
    is_processed = models.BooleanField(default=False)
    
    # ✅ Enhanced: Delivery tracking
    delivery_channels = JSONField(default=list)  # ✅ Fixed JSONField import
    delivery_status = JSONField(default=dict)  # ✅ Fixed JSONField import
    delivery_attempts = models.IntegerField(default=0)
    last_delivery_attempt = models.DateTimeField(null=True, blank=True)
    
    # Related objects
    related_signal = models.ForeignKey(
        'market_data_service.TradingSignal',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    related_event = models.ForeignKey(
        'market_data_service.CorporateEvent',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    calendar_event = models.ForeignKey(
        EventCalendar,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # ✅ Enhanced: User interaction
    acknowledged_by = models.CharField(max_length=100, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)
    outcome_notes = models.TextField(blank=True)
    
    # ✅ Enhanced: Alert effectiveness tracking
    was_accurate = models.BooleanField(null=True)
    accuracy_notes = models.TextField(blank=True)
    follow_up_required = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'trading_alerts'
        indexes = [
            models.Index(fields=['symbol', 'alert_type']),
            models.Index(fields=['urgency', 'status']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_processed']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['market_condition']),
        ]
    
    def is_expired(self) -> bool:
        """Check if alert has expired"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def mark_acknowledged(self, user: str = None):
        """Mark alert as acknowledged"""
        self.status = 'ACKNOWLEDGED'
        self.acknowledged_at = timezone.now()
        if user:
            self.acknowledged_by = user
        self.save()
    
    def mark_acted_upon(self, action_description: str):
        """Mark alert as acted upon"""
        self.status = 'ACTED_UPON'
        self.action_taken = action_description
        self.save()
    
    def calculate_effectiveness(self) -> dict:
        """Calculate alert effectiveness metrics"""
        time_to_acknowledge = None
        if self.acknowledged_at:
            time_to_acknowledge = (self.acknowledged_at - self.created_at).total_seconds() / 60
        
        return {
            'time_to_acknowledge_minutes': time_to_acknowledge,
            'was_acted_upon': self.status == 'ACTED_UPON',
            'was_accurate': self.was_accurate,
            'delivery_success_rate': self._calculate_delivery_success_rate(),
        }
    
    def _calculate_delivery_success_rate(self) -> float:
        """Calculate delivery success rate across channels"""
        if not self.delivery_status:
            return 0.0
        
        successful = sum(1 for status in self.delivery_status.values() if status == 'SUCCESS')
        total = len(self.delivery_status)
        
        return (successful / total * 100) if total > 0 else 0.0
    
    def __str__(self):
        return f"{self.symbol} - {self.alert_type} ({self.urgency})"


class EventProcessingLog(models.Model):
    """Log all event processing activities for debugging and monitoring"""
    
    PROCESSING_TYPES = (
        ('CALENDAR_SYNC', 'Calendar Synchronization'),
        ('RSS_FETCH', 'RSS Feed Fetch'),
        ('EVENT_ANALYSIS', 'Event Analysis'),
        ('ALERT_GENERATION', 'Alert Generation'),
        ('SIGNAL_GENERATION', 'Signal Generation'),
        ('NOTIFICATION_DISPATCH', 'Notification Dispatch'),
    )
    
    LOG_LEVELS = (
        ('DEBUG', 'Debug'),
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('ERROR', 'Error'),
        ('CRITICAL', 'Critical'),
    )
    
    # Processing identification
    processing_type = models.CharField(max_length=30, choices=PROCESSING_TYPES)
    source = models.ForeignKey(EventSource, on_delete=models.CASCADE, null=True, blank=True)
    
    # Log details
    log_level = models.CharField(max_length=10, choices=LOG_LEVELS, default='INFO')
    message = models.TextField()
    details = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    # Processing metrics
    processing_time_ms = models.IntegerField(null=True)
    items_processed = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    
    # Related objects
    related_company = models.ForeignKey(
        'market_data_service.Company',
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    related_alert = models.ForeignKey(
        TradingAlert,
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    
    # Exception details
    exception_type = models.CharField(max_length=100, blank=True)
    exception_message = models.TextField(blank=True)
    stack_trace = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'event_processing_logs'
        indexes = [
            models.Index(fields=['processing_type', 'log_level']),
            models.Index(fields=['created_at']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"{self.processing_type} - {self.log_level} at {self.created_at}"
