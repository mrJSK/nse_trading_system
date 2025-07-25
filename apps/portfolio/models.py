# apps/portfolio/models.py
from django.db import models
from django.contrib.postgres.fields import JSONField
from decimal import Decimal
from django.utils import timezone

class TradingAccount(models.Model):
    """Trading account information"""
    
    account_name = models.CharField(max_length=100)
    broker = models.CharField(max_length=50, default='fyers')
    account_id = models.CharField(max_length=100, unique=True)
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_paper_trading = models.BooleanField(default=True)  # Paper vs Live trading
    
    # Capital management
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2)
    current_capital = models.DecimalField(max_digits=15, decimal_places=2)
    available_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Risk management settings
    max_position_size_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    max_portfolio_risk_pct = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    stop_loss_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    
    # Performance tracking
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_accounts'
        indexes = [
            models.Index(fields=['account_id']),
            models.Index(fields=['is_active']),
        ]
    
    def calculate_win_rate(self) -> float:
        """Calculate win rate percentage"""
        if self.total_trades > 0:
            return (self.winning_trades / self.total_trades) * 100
        return 0.0
    
    def calculate_return_pct(self) -> float:
        """Calculate overall return percentage"""
        if self.initial_capital > 0:
            return ((self.current_capital - self.initial_capital) / self.initial_capital) * 100
        return 0.0

class Portfolio(models.Model):
    """Current portfolio positions"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    
    # Position details
    quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # P&L tracking
    unrealized_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unrealized_pnl_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Position management
    position_type = models.CharField(
        max_length=10,
        choices=[('LONG', 'Long'), ('SHORT', 'Short')],
        default='LONG'
    )
    
    # Linked trading signal
    entry_signal = models.ForeignKey(
        'market_data_service.TradingSignal',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Risk management
    stop_loss_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Position sizing
    position_value = models.DecimalField(max_digits=15, decimal_places=2)  # quantity * average_price
    portfolio_weight_pct = models.DecimalField(max_digits=5, decimal_places=2)  # % of total portfolio
    
    entry_date = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portfolio_positions'
        unique_together = ['account', 'company']
        indexes = [
            models.Index(fields=['account', 'position_type']),
            models.Index(fields=['entry_date']),
            models.Index(fields=['unrealized_pnl']),
        ]
    
    def update_current_price(self, new_price: Decimal):
        """Update current price and recalculate P&L"""
        self.current_price = new_price
        
        if self.position_type == 'LONG':
            self.unrealized_pnl = (new_price - self.average_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.average_price - new_price) * self.quantity
            
        if self.position_value > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.position_value) * 100
        
        self.save()

class Trade(models.Model):
    """Historical trade records"""
    
    TRADE_TYPES = (
        ('BUY', 'Buy'),
        ('SELL', 'Sell'),
    )
    
    TRADE_STATUS = (
        ('PENDING', 'Pending'),
        ('EXECUTED', 'Executed'),
        ('CANCELLED', 'Cancelled'),
        ('REJECTED', 'Rejected'),
    )
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    
    # Trade details
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Execution details
    order_id = models.CharField(max_length=100, null=True, blank=True)  # Broker order ID
    status = models.CharField(max_length=10, choices=TRADE_STATUS, default='PENDING')
    executed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    executed_quantity = models.IntegerField(null=True)
    
    # Fees and charges
    brokerage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Linked data
    trading_signal = models.ForeignKey(
        'market_data_service.TradingSignal',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    portfolio_position = models.ForeignKey(
        Portfolio,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Timestamps
    order_time = models.DateTimeField(auto_now_add=True)
    execution_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'trades'
        indexes = [
            models.Index(fields=['account', 'trade_type']),
            models.Index(fields=['status']),
            models.Index(fields=['order_time']),
            models.Index(fields=['execution_time']),
        ]

class PortfolioSnapshot(models.Model):
    """Daily portfolio snapshots for performance tracking"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    snapshot_date = models.DateField()
    
    # Portfolio metrics
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    cash_balance = models.DecimalField(max_digits=15, decimal_places=2)
    invested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Performance metrics
    day_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    day_pnl_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_return_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Risk metrics
    portfolio_beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_drawdown_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    volatility = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Holdings breakdown
    holdings_data = JSONField(default=dict)  # Store detailed holdings
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portfolio_snapshots'
        unique_together = ['account', 'snapshot_date']
        indexes = [
            models.Index(fields=['snapshot_date']),
            models.Index(fields=['total_return_pct']),
        ]

class RiskManagement(models.Model):
    """Risk management rules and limits"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    
    # Position limits
    max_position_size = models.DecimalField(max_digits=15, decimal_places=2)
    max_sector_exposure_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.0)
    max_stock_exposure_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    # Risk limits
    max_daily_loss = models.DecimalField(max_digits=15, decimal_places=2)
    max_drawdown_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    # Auto-exit rules
    auto_stop_loss = models.BooleanField(default=True)
    trailing_stop_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Monitoring
    current_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_risk_check = models.DateTimeField(null=True, blank=True)
    
    # Alerts
    risk_alert_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    send_alerts = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'risk_management'
        indexes = [
            models.Index(fields=['current_risk_score']),
            models.Index(fields=['last_risk_check']),
        ]

class PortfolioAnalytics(models.Model):
    """Portfolio analytics and performance metrics"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    analysis_date = models.DateField()
    
    # Performance metrics
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    sortino_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    information_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Risk metrics
    var_95 = models.DecimalField(max_digits=15, decimal_places=2, null=True)  # Value at Risk
    cvar_95 = models.DecimalField(max_digits=15, decimal_places=2, null=True)  # Conditional VaR
    
    # Attribution analysis
    sector_attribution = JSONField(default=dict)
    stock_attribution = JSONField(default=dict)
    
    # Benchmark comparison
    benchmark_return = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    alpha = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portfolio_analytics'
        unique_together = ['account', 'analysis_date']
