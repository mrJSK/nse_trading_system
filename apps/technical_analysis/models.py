# apps/technical_analysis/models.py
from django.db import models
from django.db.models import JSONField  # ✅ Fixed: Use built-in JSONField instead
import pandas as pd
from django.utils import timezone


class TechnicalIndicator(models.Model):
    """Store calculated technical indicators for companies in NSE trading system"""
    
    INDICATOR_TYPES = (
        ('EFI', 'Ease of Flow Index'),
        ('RSI', 'Relative Strength Index'),
        ('MACD', 'MACD'),
        ('SMA', 'Simple Moving Average'),
        ('EMA', 'Exponential Moving Average'),
        ('BOLLINGER', 'Bollinger Bands'),
        ('VOLUME', 'Volume Analysis'),
        ('ATR', 'Average True Range'),
        ('STOCHASTIC', 'Stochastic Oscillator'),
        ('WILLIAMS_R', 'Williams %R'),
        ('CCI', 'Commodity Channel Index'),
        ('ROC', 'Rate of Change'),
        ('MOMENTUM', 'Momentum'),
        ('OBV', 'On-Balance Volume'),
    )
    
    TIMEFRAMES = (
        ('1M', '1 Minute'),
        ('5M', '5 Minutes'),
        ('15M', '15 Minutes'),
        ('30M', '30 Minutes'),
        ('1H', '1 Hour'),
        ('4H', '4 Hours'),
        ('D', 'Daily'),
        ('W', 'Weekly'),
        ('M', 'Monthly'),
    )
    
    SIGNAL_TYPES = (
        ('BUY', 'Buy Signal'),
        ('SELL', 'Sell Signal'),
        ('STRONG_BUY', 'Strong Buy'),
        ('STRONG_SELL', 'Strong Sell'),
        ('NEUTRAL', 'Neutral'),
        ('HOLD', 'Hold'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    indicator_type = models.CharField(max_length=20, choices=INDICATOR_TYPES)
    timeframe = models.CharField(max_length=10, choices=TIMEFRAMES, default='D')
    
    # ✅ Enhanced: Indicator configuration
    indicator_name = models.CharField(max_length=100)  # Human readable name
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    # Indicator parameters
    parameters = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    # ✅ Enhanced: Multiple value storage for complex indicators
    current_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    previous_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    
    # ✅ Enhanced: Support for multi-line indicators (like MACD)
    secondary_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)  # Signal line, etc.
    tertiary_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)   # Histogram, etc.
    
    # Signal generation
    signal = models.CharField(max_length=15, choices=SIGNAL_TYPES, default='NEUTRAL')
    signal_strength = models.DecimalField(max_digits=5, decimal_places=3, default=0.5)  # 0-1 scale
    confidence = models.DecimalField(max_digits=5, decimal_places=3, default=0.5)       # 0-1 scale
    
    # ✅ Enhanced: Crossover detection
    crossover_detected = models.BooleanField(default=False)
    crossover_direction = models.CharField(
        max_length=10,
        choices=[('UP', 'Upward'), ('DOWN', 'Downward')],
        null=True, blank=True
    )
    crossover_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    
    # ✅ Enhanced: Divergence detection
    divergence_detected = models.BooleanField(default=False)
    divergence_type = models.CharField(
        max_length=20,
        choices=[
            ('BULLISH', 'Bullish Divergence'),
            ('BEARISH', 'Bearish Divergence'),
            ('HIDDEN_BULLISH', 'Hidden Bullish'),
            ('HIDDEN_BEARISH', 'Hidden Bearish'),
        ],
        null=True, blank=True
    )
    
    # ✅ Enhanced: Historical data with metadata
    historical_values = JSONField(default=list)  # ✅ Fixed JSONField import
    historical_signals = JSONField(default=list)  # ✅ Fixed JSONField import
    
    # ✅ Enhanced: Performance tracking
    accuracy_score = models.DecimalField(max_digits=5, decimal_places=3, null=True)  # Historical accuracy
    signals_generated = models.IntegerField(default=0)
    successful_signals = models.IntegerField(default=0)
    
    # ✅ Enhanced: Market context
    market_condition = models.CharField(
        max_length=15,
        choices=[
            ('TRENDING', 'Trending Market'),
            ('RANGING', 'Ranging Market'),
            ('VOLATILE', 'Volatile Market'),
            ('UNKNOWN', 'Unknown'),
        ],
        default='UNKNOWN'
    )
    
    # ✅ Enhanced: Calculation metadata
    calculation_timestamp = models.DateTimeField()
    data_points_used = models.IntegerField(default=0)
    calculation_time_ms = models.IntegerField(null=True)  # Performance tracking
    
    # ✅ Enhanced: Data quality
    data_quality_score = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)  # 0-1
    missing_data_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'technical_indicators'
        unique_together = ['company', 'indicator_type', 'timeframe']
        indexes = [
            models.Index(fields=['company', 'indicator_type']),
            models.Index(fields=['signal', 'crossover_detected']),
            models.Index(fields=['calculation_timestamp']),
            models.Index(fields=['timeframe', 'is_active']),
            models.Index(fields=['signal_strength', 'confidence']),
            models.Index(fields=['divergence_detected', 'divergence_type']),
            models.Index(fields=['market_condition']),
        ]
    
    def calculate_accuracy(self) -> float:
        """Calculate historical accuracy of this indicator"""
        if self.signals_generated > 0:
            return (self.successful_signals / self.signals_generated) * 100
        return 0.0
    
    def update_performance(self, was_successful: bool):
        """Update performance metrics after signal validation"""
        self.signals_generated += 1
        if was_successful:
            self.successful_signals += 1
        self.accuracy_score = self.calculate_accuracy() / 100.0
        self.save()
    
    def is_oversold(self) -> bool:
        """Check if indicator suggests oversold condition"""
        if self.indicator_type == 'RSI':
            return self.current_value <= 30
        elif self.indicator_type == 'STOCHASTIC':
            return self.current_value <= 20
        elif self.indicator_type == 'WILLIAMS_R':
            return self.current_value <= -80
        return False
    
    def is_overbought(self) -> bool:
        """Check if indicator suggests overbought condition"""
        if self.indicator_type == 'RSI':
            return self.current_value >= 70
        elif self.indicator_type == 'STOCHASTIC':
            return self.current_value >= 80
        elif self.indicator_type == 'WILLIAMS_R':
            return self.current_value >= -20
        return False
    
    def get_trend_direction(self) -> str:
        """Determine trend direction based on indicator"""
        if self.indicator_type in ['SMA', 'EMA']:
            # For moving averages, compare current price with MA
            return 'UP' if self.current_value > self.previous_value else 'DOWN'
        elif self.indicator_type == 'MACD':
            # For MACD, check if MACD line is above signal line
            return 'UP' if self.current_value > self.secondary_value else 'DOWN'
        elif self.indicator_type == 'EFI':
            # For EFI, positive values indicate buying pressure
            return 'UP' if self.current_value > 0 else 'DOWN'
        return 'NEUTRAL'
    
    def __str__(self):
        return f"{self.company.symbol} - {self.indicator_type} ({self.timeframe})"


class MarketData(models.Model):
    """Store OHLCV market data from Fyers for technical analysis"""
    
    DATA_SOURCES = (
        ('FYERS', 'Fyers API'),
        ('NSE', 'NSE Direct'),
        ('YAHOO', 'Yahoo Finance'),
        ('MANUAL', 'Manual Entry'),
    )
    
    TIMEFRAMES = (
        ('1M', '1 Minute'),
        ('5M', '5 Minutes'),
        ('15M', '15 Minutes'),
        ('30M', '30 Minutes'),
        ('1H', '1 Hour'),
        ('4H', '4 Hours'),
        ('D', 'Daily'),
        ('W', 'Weekly'),
        ('M', 'Monthly'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    timeframe = models.CharField(max_length=10, choices=TIMEFRAMES)
    
    # OHLCV data
    timestamp = models.DateTimeField(db_index=True)
    open_price = models.DecimalField(max_digits=12, decimal_places=4)
    high_price = models.DecimalField(max_digits=12, decimal_places=4)
    low_price = models.DecimalField(max_digits=12, decimal_places=4)
    close_price = models.DecimalField(max_digits=12, decimal_places=4)
    volume = models.BigIntegerField()
    
    # ✅ Enhanced: Additional market data
    vwap = models.DecimalField(max_digits=12, decimal_places=4, null=True)  # Volume Weighted Average Price
    open_interest = models.BigIntegerField(null=True)  # For F&O
    
    # ✅ Enhanced: Price movement analysis
    price_change = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    price_change_pct = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    
    # ✅ Enhanced: Volume analysis
    volume_sma = models.BigIntegerField(null=True)      # Volume moving average
    volume_ratio = models.DecimalField(max_digits=8, decimal_places=4, null=True)  # Current/Average
    
    # ✅ Enhanced: Volatility measures
    true_range = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    daily_volatility = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    
    # ✅ Enhanced: Gap analysis
    gap_size = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    gap_type = models.CharField(
        max_length=15,
        choices=[
            ('NO_GAP', 'No Gap'),
            ('GAP_UP', 'Gap Up'),
            ('GAP_DOWN', 'Gap Down'),
            ('ISLAND_TOP', 'Island Top'),
            ('ISLAND_BOTTOM', 'Island Bottom'),
        ],
        default='NO_GAP'
    )
    
    # ✅ Enhanced: Market microstructure
    bid_price = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    ask_price = models.DecimalField(max_digits=12, decimal_places=4, null=True)
    bid_size = models.BigIntegerField(null=True)
    ask_size = models.BigIntegerField(null=True)
    spread = models.DecimalField(max_digits=8, decimal_places=4, null=True)
    
    # ✅ Enhanced: Data quality and metadata
    data_source = models.CharField(max_length=20, choices=DATA_SOURCES, default='FYERS')
    is_validated = models.BooleanField(default=True)
    data_quality_score = models.DecimalField(max_digits=3, decimal_places=2, default=1.0)
    
    # ✅ Enhanced: Session information
    is_pre_market = models.BooleanField(default=False)
    is_post_market = models.BooleanField(default=False)
    session_type = models.CharField(
        max_length=15,
        choices=[
            ('REGULAR', 'Regular Session'),
            ('PRE_MARKET', 'Pre-Market'),
            ('POST_MARKET', 'Post-Market'),
            ('EXTENDED', 'Extended Hours'),
        ],
        default='REGULAR'
    )
    
    # ✅ Enhanced: Corporate action flags
    is_ex_dividend = models.BooleanField(default=False)
    is_split_adjusted = models.BooleanField(default=False)
    is_bonus_adjusted = models.BooleanField(default=False)
    adjustment_factor = models.DecimalField(max_digits=8, decimal_places=6, default=1.0)
    
    # ✅ Enhanced: Technical analysis flags
    is_doji = models.BooleanField(default=False)
    is_hammer = models.BooleanField(default=False)
    is_shooting_star = models.BooleanField(default=False)
    candlestick_pattern = models.CharField(max_length=50, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'market_data'
        unique_together = ['company', 'timeframe', 'timestamp']
        indexes = [
            models.Index(fields=['company', 'timeframe', 'timestamp']),
            models.Index(fields=['timestamp', 'timeframe']),
            models.Index(fields=['volume', 'timestamp']),
            models.Index(fields=['close_price', 'timestamp']),
            models.Index(fields=['data_source', 'is_validated']),
            models.Index(fields=['session_type']),
            models.Index(fields=['gap_type']),
            models.Index(fields=['candlestick_pattern']),
        ]
    
    def calculate_price_change(self, previous_close: float):
        """Calculate price change from previous close"""
        self.price_change = self.close_price - previous_close
        if previous_close > 0:
            self.price_change_pct = (self.price_change / previous_close) * 100
    
    def calculate_true_range(self, previous_close: float):
        """Calculate True Range for ATR calculation"""
        high_low = self.high_price - self.low_price
        high_close = abs(self.high_price - previous_close)
        low_close = abs(self.low_price - previous_close)
        self.true_range = max(high_low, high_close, low_close)
    
    def identify_candlestick_pattern(self):
        """Identify basic candlestick patterns"""
        body_size = abs(self.close_price - self.open_price)
        total_range = self.high_price - self.low_price
        
        if total_range == 0:
            return
        
        body_ratio = body_size / total_range
        
        # Doji pattern
        if body_ratio <= 0.1:
            self.is_doji = True
            self.candlestick_pattern = 'DOJI'
        
        # Hammer pattern (bullish reversal)
        elif (self.close_price > self.open_price and 
              (self.low_price - min(self.open_price, self.close_price)) >= 2 * body_size and
              (self.high_price - max(self.open_price, self.close_price)) <= body_size):
            self.is_hammer = True
            self.candlestick_pattern = 'HAMMER'
        
        # Shooting star pattern (bearish reversal)
        elif (self.close_price < self.open_price and
              (max(self.open_price, self.close_price) - self.low_price) <= body_size and
              (self.high_price - max(self.open_price, self.close_price)) >= 2 * body_size):
            self.is_shooting_star = True
            self.candlestick_pattern = 'SHOOTING_STAR'
        
        # Add more patterns as needed
    
    def is_bullish_candle(self) -> bool:
        """Check if candle is bullish (close > open)"""
        return self.close_price > self.open_price
    
    def is_bearish_candle(self) -> bool:
        """Check if candle is bearish (close < open)"""
        return self.close_price < self.open_price
    
    def get_body_size(self) -> float:
        """Get the size of the candle body"""
        return abs(float(self.close_price - self.open_price))
    
    def get_upper_shadow(self) -> float:
        """Get the size of upper shadow"""
        return float(self.high_price - max(self.open_price, self.close_price))
    
    def get_lower_shadow(self) -> float:
        """Get the size of lower shadow"""
        return float(min(self.open_price, self.close_price) - self.low_price)
    
    def __str__(self):
        return f"{self.company.symbol} {self.timeframe} - {self.timestamp}"


class IndicatorAlert(models.Model):
    """Store alerts generated by technical indicators"""
    
    ALERT_TYPES = (
        ('CROSSOVER', 'Crossover Alert'),
        ('THRESHOLD', 'Threshold Breach'),
        ('DIVERGENCE', 'Divergence Alert'),
        ('PATTERN', 'Pattern Alert'),
        ('VOLUME', 'Volume Alert'),
    )
    
    URGENCY_LEVELS = (
        ('LOW', 'Low Priority'),
        ('MEDIUM', 'Medium Priority'),
        ('HIGH', 'High Priority'),
        ('CRITICAL', 'Critical'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    indicator = models.ForeignKey(TechnicalIndicator, on_delete=models.CASCADE)
    
    alert_type = models.CharField(max_length=15, choices=ALERT_TYPES)
    urgency = models.CharField(max_length=10, choices=URGENCY_LEVELS, default='MEDIUM')
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    
    # Alert conditions
    trigger_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    threshold_value = models.DecimalField(max_digits=15, decimal_places=6, null=True)
    
    # ✅ Alert metadata
    alert_data = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    # Alert status
    is_active = models.BooleanField(default=True)
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Performance tracking
    was_accurate = models.BooleanField(null=True)
    accuracy_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'indicator_alerts'
        indexes = [
            models.Index(fields=['company', 'alert_type']),
            models.Index(fields=['urgency', 'is_active']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_sent']),
        ]
    
    def mark_as_sent(self):
        """Mark alert as sent"""
        self.is_sent = True
        self.sent_at = timezone.now()
        self.save()
    
    def __str__(self):
        return f"{self.company.symbol} - {self.alert_type} Alert"


class BacktestResult(models.Model):
    """Store backtesting results for technical indicators and strategies"""
    
    STRATEGY_TYPES = (
        ('SINGLE_INDICATOR', 'Single Indicator'),
        ('MULTI_INDICATOR', 'Multiple Indicators'),
        ('EFI_STRATEGY', 'EFI Crossover Strategy'),
        ('MEAN_REVERSION', 'Mean Reversion'),
        ('MOMENTUM', 'Momentum Strategy'),
        ('CUSTOM', 'Custom Strategy'),
    )
    
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    strategy_type = models.CharField(max_length=20, choices=STRATEGY_TYPES)
    strategy_name = models.CharField(max_length=100)
    timeframe = models.CharField(max_length=10)
    
    # Backtest parameters
    start_date = models.DateField()
    end_date = models.DateField()
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2, default=100000)
    
    # ✅ Strategy configuration
    strategy_parameters = JSONField(default=dict)  # ✅ Fixed JSONField import
    indicators_used = JSONField(default=list)      # ✅ Fixed JSONField import
    
    # Performance metrics
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    win_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Returns
    total_return = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_return_pct = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    annualized_return = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    # Risk metrics
    max_drawdown = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    volatility = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    sharpe_ratio = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    sortino_ratio = models.DecimalField(max_digits=6, decimal_places=4, null=True)
    
    # Additional metrics
    avg_trade_return = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    best_trade = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    worst_trade = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    
    # ✅ Detailed results
    trade_log = JSONField(default=list)       # ✅ Fixed JSONField import
    equity_curve = JSONField(default=list)    # ✅ Fixed JSONField import
    drawdown_curve = JSONField(default=list)  # ✅ Fixed JSONField import
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'backtest_results'
        indexes = [
            models.Index(fields=['company', 'strategy_type']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['total_return_pct']),
            models.Index(fields=['sharpe_ratio']),
            models.Index(fields=['win_rate']),
        ]
    
    def calculate_metrics(self):
        """Calculate performance metrics from trade log"""
        if self.total_trades > 0:
            self.win_rate = (self.winning_trades / self.total_trades) * 100
            self.avg_trade_return = self.total_return / self.total_trades
    
    def __str__(self):
        return f"{self.company.symbol} - {self.strategy_name} Backtest"
