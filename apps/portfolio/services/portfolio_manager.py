# apps/portfolio/services/portfolio_manager.py
from typing import Dict, List, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
import logging

from ..models import TradingAccount, Portfolio, Trade, PortfolioSnapshot
from ...market_data_service.models import Company, TradingSignal

logger = logging.getLogger(__name__)

class PortfolioManager:
    """Manage portfolio positions and operations"""
    
    def __init__(self, account_id: str):
        self.account = TradingAccount.objects.get(account_id=account_id)
    
    def get_current_positions(self) -> List[Dict[str, Any]]:
        """Get all current portfolio positions"""
        try:
            positions = Portfolio.objects.filter(account=self.account)
            
            position_data = []
            for position in positions:
                position_data.append({
                    'symbol': position.company.symbol,
                    'company_name': position.company.name,
                    'quantity': position.quantity,
                    'average_price': float(position.average_price),
                    'current_price': float(position.current_price),
                    'unrealized_pnl': float(position.unrealized_pnl),
                    'unrealized_pnl_pct': float(position.unrealized_pnl_pct),
                    'position_value': float(position.position_value),
                    'portfolio_weight_pct': float(position.portfolio_weight_pct),
                    'entry_date': position.entry_date.isoformat(),
                })
            
            return position_data
            
        except Exception as e:
            logger.error(f"Error getting current positions: {e}")
            return []
    
    def calculate_portfolio_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive portfolio metrics"""
        try:
            positions = Portfolio.objects.filter(account=self.account)
            
            total_value = sum(pos.position_value for pos in positions)
            total_unrealized_pnl = sum(pos.unrealized_pnl for pos in positions)
            
            cash_balance = self.account.current_capital - total_value
            
            metrics = {
                'total_portfolio_value': float(total_value + cash_balance),
                'invested_amount': float(total_value),
                'cash_balance': float(cash_balance),
                'total_unrealized_pnl': float(total_unrealized_pnl),
                'total_positions': positions.count(),
                'account_return_pct': self.account.calculate_return_pct(),
                'win_rate_pct': self.account.calculate_win_rate(),
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {e}")
            return {}
    
    @transaction.atomic
    def execute_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Execute a trading signal"""
        try:
            if signal.action in ['BUY', 'STRONG_BUY']:
                return self._execute_buy_signal(signal)
            elif signal.action in ['SELL', 'STRONG_SELL']:
                return self._execute_sell_signal(signal)
            else:
                return {'success': False, 'message': 'Invalid signal action'}
                
        except Exception as e:
            logger.error(f"Error executing signal for {signal.symbol}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_buy_signal(self, signal: TradingSignal) -> Dict[str, Any]:
        """Execute buy signal"""
        try:
            # Calculate position size based on risk management
            position_size = self._calculate_position_size(signal)
            
            if position_size <= 0:
                return {'success': False, 'message': 'Position size too small or risk limits exceeded'}
            
            # Create trade record
            trade = Trade.objects.create(
                account=self.account,
                company=signal.company,
                trade_type='BUY',
                quantity=position_size,
                price=signal.current_price or signal.price_at_signal,
                total_value=position_size * (signal.current_price or signal.price_at_signal),
                trading_signal=signal
            )
            
            # Create or update portfolio position
            portfolio_position, created = Portfolio.objects.get_or_create(
                account=self.account,
                company=signal.company,
                defaults={
                    'quantity': position_size,
                    'average_price': signal.current_price or signal.price_at_signal,
                    'current_price': signal.current_price or signal.price_at_signal,
                    'position_value': position_size * (signal.current_price or signal.price_at_signal),
                    'entry_signal': signal,
                    'stop_loss_price': signal.stop_loss,
                    'target_price': signal.target_price,
                    'entry_date': timezone.now()
                }
            )
            
            if not created:
                # Update existing position (average down/up)
                total_quantity = portfolio_position.quantity + position_size
                total_value = (portfolio_position.quantity * portfolio_position.average_price + 
                              position_size * (signal.current_price or signal.price_at_signal))
                new_average_price = total_value / total_quantity
                
                portfolio_position.quantity = total_quantity
                portfolio_position.average_price = new_average_price
                portfolio_position.position_value = total_quantity * new_average_price
                portfolio_position.save()
            
            return {
                'success': True,
                'trade_id': trade.id,
                'position_size': position_size,
                'price': float(signal.current_price or signal.price_at_signal)
            }
            
        except Exception as e:
            logger.error(f"Error executing buy signal: {e}")
            return {'success': False, 'error': str(e)}
    
    def _calculate_position_size(self, signal: TradingSignal) -> int:
        """Calculate position size based on risk management"""
        try:
            # Use the recommended position size from signal if available
            if signal.position_size_pct:
                portfolio_value = self.account.current_capital
                position_value = portfolio_value * (signal.position_size_pct / 100)
                position_size = int(position_value / (signal.current_price or signal.price_at_signal))
            else:
                # Default to account risk management settings
                max_position_value = self.account.current_capital * (self.account.max_position_size_pct / 100)
                position_size = int(max_position_value / (signal.current_price or signal.price_at_signal))
            
            return max(0, position_size)
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
