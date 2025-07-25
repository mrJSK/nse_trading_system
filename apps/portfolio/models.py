# apps/portfolio/models.py
from django.db import models
from django.db.models import JSONField  # ✅ Fixed: Use built-in JSONField instead
from decimal import Decimal
from django.utils import timezone


class TradingAccount(models.Model):
    """Trading account information for NSE trading system"""
    
    account_name = models.CharField(max_length=100)
    broker = models.CharField(max_length=50, default='fyers')
    account_id = models.CharField(max_length=100, unique=True)
    
    # Account status
    is_active = models.BooleanField(default=True)
    is_paper_trading = models.BooleanField(default=True)  # Paper vs Live trading
    
    # ✅ Enhanced: Account type and configuration
    account_type = models.CharField(
        max_length=20,
        choices=[
            ('EQUITY', 'Equity Trading'),
            ('DERIVATIVES', 'Derivatives Trading'),
            ('COMMODITY', 'Commodity Trading'),
            ('MULTI_ASSET', 'Multi-Asset'),
        ],
        default='EQUITY'
    )
    
    # Capital management
    initial_capital = models.DecimalField(max_digits=15, decimal_places=2)
    current_capital = models.DecimalField(max_digits=15, decimal_places=2)
    available_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # ✅ Enhanced: Additional capital tracking
    blocked_margin = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Risk management settings
    max_position_size_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    max_portfolio_risk_pct = models.DecimalField(max_digits=5, decimal_places=2, default=2.0)
    stop_loss_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    
    # ✅ Enhanced: Additional risk settings
    max_daily_trades = models.IntegerField(default=10)
    max_positions = models.IntegerField(default=20)
    leverage_ratio = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    
    # Performance tracking
    total_trades = models.IntegerField(default=0)
    winning_trades = models.IntegerField(default=0)
    losing_trades = models.IntegerField(default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # ✅ Enhanced: Additional performance metrics
    best_trade_pnl = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    worst_trade_pnl = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    average_trade_pnl = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_consecutive_wins = models.IntegerField(default=0)
    max_consecutive_losses = models.IntegerField(default=0)
    current_streak = models.IntegerField(default=0)  # Positive for wins, negative for losses
    
    # ✅ Enhanced: Drawdown tracking
    max_drawdown = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    max_drawdown_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    current_drawdown = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # ✅ Enhanced: Strategy performance
    primary_strategy = models.CharField(max_length=50, default='EFI_CROSSOVER')
    strategy_performance = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'trading_accounts'
        indexes = [
            models.Index(fields=['account_id']),
            models.Index(fields=['is_active', 'account_type']),
            models.Index(fields=['broker']),
            models.Index(fields=['total_pnl']),
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
    
    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.06) -> float:
        """Calculate Sharpe ratio"""
        if self.total_trades < 10:  # Need sufficient trades
            return 0.0
        
        # This is a simplified calculation - in production, use proper time series
        annual_return = self.calculate_return_pct()
        # Simplified volatility calculation
        volatility = 15.0  # This should be calculated from actual trade returns
        
        return (annual_return - risk_free_rate * 100) / volatility
    
    def update_performance_metrics(self, trade_pnl: Decimal, is_winning_trade: bool):
        """Update performance metrics after a trade"""
        self.total_trades += 1
        self.total_pnl += trade_pnl
        
        if is_winning_trade:
            self.winning_trades += 1
            self.current_streak = max(0, self.current_streak) + 1
            self.max_consecutive_wins = max(self.max_consecutive_wins, self.current_streak)
        else:
            self.losing_trades += 1
            self.current_streak = min(0, self.current_streak) - 1
            self.max_consecutive_losses = max(self.max_consecutive_losses, abs(self.current_streak))
        
        # Update best/worst trades
        if self.best_trade_pnl is None or trade_pnl > self.best_trade_pnl:
            self.best_trade_pnl = trade_pnl
        if self.worst_trade_pnl is None or trade_pnl < self.worst_trade_pnl:
            self.worst_trade_pnl = trade_pnl
        
        # Update average trade P&L
        self.average_trade_pnl = self.total_pnl / self.total_trades
        
        self.save()
    
    def __str__(self):
        return f"{self.account_name} ({self.broker})"


class Portfolio(models.Model):
    """Current portfolio positions"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    
    # Position details
    quantity = models.IntegerField()
    average_price = models.DecimalField(max_digits=10, decimal_places=2)
    current_price = models.DecimalField(max_digits=10, decimal_places=2)
    
    # ✅ Enhanced: Additional position details
    market_value = models.DecimalField(max_digits=15, decimal_places=2)  # current_price * quantity
    cost_basis = models.DecimalField(max_digits=15, decimal_places=2)    # average_price * quantity
    
    # P&L tracking
    unrealized_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unrealized_pnl_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # ✅ Enhanced: Realized P&L tracking
    realized_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Position management
    position_type = models.CharField(
        max_length=10,
        choices=[('LONG', 'Long'), ('SHORT', 'Short')],
        default='LONG'
    )
    
    # ✅ Enhanced: Position status
    position_status = models.CharField(
        max_length=15,
        choices=[
            ('OPEN', 'Open'),
            ('PARTIAL_CLOSE', 'Partially Closed'),
            ('CLOSED', 'Closed'),
            ('SUSPENDED', 'Suspended'),
        ],
        default='OPEN'
    )
    
    # Linked trading signal
    entry_signal = models.ForeignKey(
        'market_data_service.TradingSignal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='portfolio_positions'
    )
    
    # ✅ Enhanced: Exit signal tracking
    exit_signal = models.ForeignKey(
        'market_data_service.TradingSignal',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='portfolio_exits'
    )
    
    # Risk management
    stop_loss_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    target_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # ✅ Enhanced: Advanced risk management
    trailing_stop_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    trailing_stop_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_loss_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    
    # Position sizing
    position_value = models.DecimalField(max_digits=15, decimal_places=2)  # quantity * average_price
    portfolio_weight_pct = models.DecimalField(max_digits=5, decimal_places=2)  # % of total portfolio
    
    # ✅ Enhanced: Risk metrics
    position_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    correlation_to_portfolio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Performance tracking
    days_held = models.IntegerField(default=0)
    high_since_entry = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    low_since_entry = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    max_unrealized_gain = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    max_unrealized_loss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    entry_date = models.DateTimeField()
    last_price_update = models.DateTimeField(auto_now=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'portfolio_positions'
        unique_together = ['account', 'company']
        indexes = [
            models.Index(fields=['account', 'position_type', 'position_status']),
            models.Index(fields=['entry_date']),
            models.Index(fields=['unrealized_pnl']),
            models.Index(fields=['portfolio_weight_pct']),
            models.Index(fields=['position_risk_score']),
        ]
    
    def update_current_price(self, new_price: Decimal):
        """Update current price and recalculate P&L"""
        self.current_price = new_price
        self.market_value = new_price * self.quantity
        
        # Update high/low since entry
        if self.high_since_entry is None or new_price > self.high_since_entry:
            self.high_since_entry = new_price
        if self.low_since_entry is None or new_price < self.low_since_entry:
            self.low_since_entry = new_price
        
        # Calculate unrealized P&L
        if self.position_type == 'LONG':
            self.unrealized_pnl = (new_price - self.average_price) * self.quantity
        else:  # SHORT
            self.unrealized_pnl = (self.average_price - new_price) * self.quantity
            
        if self.cost_basis > 0:
            self.unrealized_pnl_pct = (self.unrealized_pnl / self.cost_basis) * 100
        
        # Update max gain/loss tracking
        if self.unrealized_pnl > self.max_unrealized_gain:
            self.max_unrealized_gain = self.unrealized_pnl
        if self.unrealized_pnl < self.max_unrealized_loss:
            self.max_unrealized_loss = self.unrealized_pnl
        
        # Update total P&L
        self.total_pnl = self.realized_pnl + self.unrealized_pnl
        
        # Update days held
        self.days_held = (timezone.now() - self.entry_date).days
        
        # Check for trailing stop
        self._update_trailing_stop(new_price)
        
        self.save()
    
    def _update_trailing_stop(self, current_price: Decimal):
        """Update trailing stop loss price"""
        if not self.trailing_stop_pct:
            return
        
        if self.position_type == 'LONG' and self.trailing_stop_price:
            # For long positions, move stop up as price increases
            new_stop = current_price * (1 - self.trailing_stop_pct / 100)
            if new_stop > self.trailing_stop_price:
                self.trailing_stop_price = new_stop
        elif self.position_type == 'SHORT' and self.trailing_stop_price:
            # For short positions, move stop down as price decreases
            new_stop = current_price * (1 + self.trailing_stop_pct / 100)
            if new_stop < self.trailing_stop_price:
                self.trailing_stop_price = new_stop
    
    def should_trigger_stop_loss(self) -> bool:
        """Check if position should trigger stop loss"""
        if not self.stop_loss_price:
            return False
        
        if self.position_type == 'LONG':
            return self.current_price <= self.stop_loss_price
        else:  # SHORT
            return self.current_price >= self.stop_loss_price
    
    def should_trigger_target(self) -> bool:
        """Check if position should trigger target"""
        if not self.target_price:
            return False
        
        if self.position_type == 'LONG':
            return self.current_price >= self.target_price
        else:  # SHORT
            return self.current_price <= self.target_price
    
    def __str__(self):
        return f"{self.company.symbol} - {self.quantity} @ ₹{self.average_price}"


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
        ('PARTIAL', 'Partially Executed'),
    )
    
    ORDER_TYPES = (
        ('MARKET', 'Market Order'),
        ('LIMIT', 'Limit Order'),
        ('STOP_LOSS', 'Stop Loss'),
        ('STOP_LIMIT', 'Stop Limit'),
    )
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    company = models.ForeignKey('market_data_service.Company', on_delete=models.CASCADE)
    
    # Trade details
    trade_type = models.CharField(max_length=10, choices=TRADE_TYPES)
    order_type = models.CharField(max_length=15, choices=ORDER_TYPES, default='MARKET')
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Order price
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    
    # ✅ Enhanced: Order parameters
    limit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    stop_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    validity = models.CharField(
        max_length=10,
        choices=[('DAY', 'Day'), ('IOC', 'Immediate or Cancel'), ('GTD', 'Good Till Date')],
        default='DAY'
    )
    valid_till = models.DateTimeField(null=True, blank=True)
    
    # Execution details
    order_id = models.CharField(max_length=100, null=True, blank=True)  # Broker order ID
    status = models.CharField(max_length=10, choices=TRADE_STATUS, default='PENDING')
    executed_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    executed_quantity = models.IntegerField(null=True)
    remaining_quantity = models.IntegerField(default=0)
    
    # ✅ Enhanced: Execution tracking
    avg_execution_price = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    execution_count = models.IntegerField(default=0)  # Number of partial executions
    
    # Fees and charges
    brokerage = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxes = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # ✅ Enhanced: Detailed charges
    stt = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Securities Transaction Tax
    stamp_duty = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    exchange_charges = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    gst = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    
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
    
    # ✅ Enhanced: Trade context
    trade_reason = models.CharField(
        max_length=20,
        choices=[
            ('SIGNAL_ENTRY', 'Signal Entry'),
            ('SIGNAL_EXIT', 'Signal Exit'),
            ('STOP_LOSS', 'Stop Loss'),
            ('TARGET_HIT', 'Target Hit'),
            ('RISK_MGMT', 'Risk Management'),
            ('MANUAL', 'Manual Trade'),
        ],
        null=True, blank=True
    )
    
    # ✅ Enhanced: Trade metadata
    trade_metadata = JSONField(default=dict)  # ✅ Fixed JSONField import
    market_condition = models.CharField(max_length=15, blank=True)
    
    # Timestamps
    order_time = models.DateTimeField(auto_now_add=True)
    execution_time = models.DateTimeField(null=True, blank=True)
    cancellation_time = models.DateTimeField(null=True, blank=True)
    
    # ✅ Enhanced: Performance tracking
    slippage = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # Price - Expected Price
    execution_delay_seconds = models.IntegerField(null=True)
    
    class Meta:
        db_table = 'trades'
        indexes = [
            models.Index(fields=['account', 'trade_type']),
            models.Index(fields=['status', 'order_type']),
            models.Index(fields=['order_time']),
            models.Index(fields=['execution_time']),
            models.Index(fields=['company', 'trade_type']),
            models.Index(fields=['trade_reason']),
        ]
    
    def calculate_net_amount(self) -> Decimal:
        """Calculate net amount after all charges"""
        gross_amount = (self.executed_price or self.price) * (self.executed_quantity or self.quantity)
        return gross_amount - self.total_charges
    
    def calculate_slippage(self, expected_price: Decimal):
        """Calculate slippage from expected price"""
        if self.executed_price:
            self.slippage = ((self.executed_price - expected_price) / expected_price) * 100
            self.save()
    
    def __str__(self):
        return f"{self.trade_type} {self.quantity} {self.company.symbol} @ ₹{self.price}"


class PortfolioSnapshot(models.Model):
    """Daily portfolio snapshots for performance tracking"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    snapshot_date = models.DateField()
    
    # Portfolio metrics
    total_value = models.DecimalField(max_digits=15, decimal_places=2)
    cash_balance = models.DecimalField(max_digits=15, decimal_places=2)
    invested_amount = models.DecimalField(max_digits=15, decimal_places=2)
    
    # ✅ Enhanced: Additional portfolio metrics
    margin_used = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    margin_available = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    exposure = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Performance metrics
    day_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    day_pnl_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    total_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_return_pct = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # ✅ Enhanced: Performance metrics
    realized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    unrealized_pnl = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Risk metrics
    portfolio_beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    max_drawdown_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    volatility = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Risk metrics
    var_1d = models.DecimalField(max_digits=15, decimal_places=2, null=True)  # 1-day VaR
    portfolio_concentration = models.DecimalField(max_digits=5, decimal_places=2, null=True)  # HHI
    correlation_risk = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Holdings breakdown
    holdings_data = JSONField(default=dict)  # ✅ Fixed JSONField import
    sector_allocation = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    # ✅ Enhanced: Market context
    market_index_value = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    market_index_change = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portfolio_snapshots'
        unique_together = ['account', 'snapshot_date']
        indexes = [
            models.Index(fields=['snapshot_date']),
            models.Index(fields=['total_return_pct']),
            models.Index(fields=['max_drawdown_pct']),
        ]
    
    def calculate_portfolio_metrics(self):
        """Calculate derived portfolio metrics"""
        if self.invested_amount > 0:
            self.total_return_pct = (self.total_pnl / self.invested_amount) * 100
        
        if self.total_value > 0:
            self.day_pnl_pct = (self.day_pnl / self.total_value) * 100


class RiskManagement(models.Model):
    """Risk management rules and limits"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    
    # Position limits
    max_position_size = models.DecimalField(max_digits=15, decimal_places=2)
    max_sector_exposure_pct = models.DecimalField(max_digits=5, decimal_places=2, default=20.0)
    max_stock_exposure_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    # ✅ Enhanced: Additional limits
    max_correlation = models.DecimalField(max_digits=3, decimal_places=2, default=0.8)
    max_beta = models.DecimalField(max_digits=3, decimal_places=2, default=1.5)
    min_liquidity_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.7)
    
    # Risk limits
    max_daily_loss = models.DecimalField(max_digits=15, decimal_places=2)
    max_drawdown_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.0)
    
    # ✅ Enhanced: Advanced risk limits
    max_var_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)  # Max VaR as % of portfolio
    max_leverage = models.DecimalField(max_digits=3, decimal_places=1, default=2.0)
    concentration_limit_pct = models.DecimalField(max_digits=5, decimal_places=2, default=15.0)
    
    # Auto-exit rules
    auto_stop_loss = models.BooleanField(default=True)
    trailing_stop_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Advanced auto-exit rules
    auto_rebalance = models.BooleanField(default=False)
    rebalance_threshold_pct = models.DecimalField(max_digits=5, decimal_places=2, default=5.0)
    
    # Monitoring
    current_risk_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    last_risk_check = models.DateTimeField(null=True, blank=True)
    
    # ✅ Enhanced: Risk monitoring
    breach_count_daily = models.IntegerField(default=0)
    breach_count_monthly = models.IntegerField(default=0)
    last_breach_date = models.DateField(null=True, blank=True)
    
    # Alerts
    risk_alert_threshold = models.DecimalField(max_digits=5, decimal_places=2, default=80.0)
    send_alerts = models.BooleanField(default=True)
    
    # ✅ Enhanced: Alert configuration
    alert_channels = JSONField(default=list)  # ✅ Fixed JSONField import
    escalation_levels = JSONField(default=dict)  # ✅ Fixed JSONField import
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'risk_management'
        indexes = [
            models.Index(fields=['current_risk_score']),
            models.Index(fields=['last_risk_check']),
            models.Index(fields=['breach_count_daily']),
        ]
    
    def check_position_limits(self, position_value: Decimal, sector: str = None) -> dict:
        """Check if new position violates limits"""
        violations = []
        
        if position_value > self.max_position_size:
            violations.append(f"Position size exceeds limit: ₹{position_value} > ₹{self.max_position_size}")
        
        # Additional checks would go here
        
        return {
            'is_valid': len(violations) == 0,
            'violations': violations
        }


class PortfolioAnalytics(models.Model):
    """Portfolio analytics and performance metrics"""
    
    account = models.ForeignKey(TradingAccount, on_delete=models.CASCADE)
    analysis_date = models.DateField()
    
    # Performance metrics
    sharpe_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    sortino_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    information_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Additional performance ratios
    calmar_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    treynor_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    jensen_alpha = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # Risk metrics
    var_95 = models.DecimalField(max_digits=15, decimal_places=2, null=True)  # Value at Risk
    cvar_95 = models.DecimalField(max_digits=15, decimal_places=2, null=True)  # Conditional VaR
    
    # ✅ Enhanced: Risk metrics
    var_99 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    expected_shortfall = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    max_consecutive_losses = models.IntegerField(null=True)
    
    # Attribution analysis
    sector_attribution = JSONField(default=dict)  # ✅ Fixed JSONField import
    stock_attribution = JSONField(default=dict)   # ✅ Fixed JSONField import
    
    # ✅ Enhanced: Attribution analysis
    factor_attribution = JSONField(default=dict)  # ✅ Fixed JSONField import
    style_attribution = JSONField(default=dict)   # ✅ Fixed JSONField import
    
    # Benchmark comparison
    benchmark_return = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    alpha = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    beta = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Benchmark analysis
    tracking_error = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    correlation_to_benchmark = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    up_capture_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    down_capture_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    
    # ✅ Enhanced: Analysis metadata
    analysis_window_days = models.IntegerField(default=252)  # Analysis period
    benchmark_used = models.CharField(max_length=50, default='NIFTY50')
    confidence_level = models.DecimalField(max_digits=3, decimal_places=2, default=0.95)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'portfolio_analytics'
        unique_together = ['account', 'analysis_date']
        indexes = [
            models.Index(fields=['analysis_date']),
            models.Index(fields=['sharpe_ratio']),
            models.Index(fields=['alpha']),
            models.Index(fields=['max_consecutive_losses']),
        ]
    
    def calculate_risk_adjusted_return(self) -> dict:
        """Calculate various risk-adjusted return metrics"""
        return {
            'sharpe': float(self.sharpe_ratio or 0),
            'sortino': float(self.sortino_ratio or 0),
            'calmar': float(self.calmar_ratio or 0),
            'information': float(self.information_ratio or 0),
        }
    
    def __str__(self):
        return f"Analytics for {self.account.account_name} on {self.analysis_date}"
