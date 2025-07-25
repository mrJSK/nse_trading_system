# apps/trading_engine/services/signal_generator.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd
from decimal import Decimal
import logging
from django.utils import timezone
from django.db.models import Q

from core.interfaces.scraping_interfaces import TradingSignalGeneratorInterface, TradingSignal
from ...technical_analysis.services.indicators import EFIIndicator, SignalGenerator as TechSignalGenerator
from ...market_data_service.models import (
    Company, FundamentalScore, CorporateEvent, ValuationMetrics, 
    ProfitabilityMetrics, GrowthMetrics, FinancialStatement
)

logger = logging.getLogger(__name__)

class ComprehensiveTradingSignalGenerator(TradingSignalGeneratorInterface):
    """Single responsibility: Generate trading signals from multiple data sources"""
    
    def __init__(self):
        self.efi_indicator = EFIIndicator(period=20)
        self.tech_signal_generator = TechSignalGenerator(self.efi_indicator)
        
        # Signal weights for different data sources
        self.signal_weights = {
            'fundamental': 0.4,
            'technical': 0.3,
            'event': 0.2,
            'momentum': 0.1
        }
        
        # Minimum confidence threshold for signals
        self.min_confidence_threshold = 0.6
        
        # EFI crossover threshold
        self.efi_threshold = 0.0
        
        # Risk management parameters
        self.max_portfolio_risk = 0.02  # 2% max risk per trade
        self.max_position_size = 0.05   # 5% max position size
    
    def generate_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate comprehensive trading signals"""
        try:
            symbol = analysis_data.get('symbol')
            if not symbol:
                return []
            
            signals = []
            
            # Generate signals from different sources
            fundamental_signals = self._generate_fundamental_signals(analysis_data)
            technical_signals = self._generate_technical_signals(analysis_data)
            event_signals = self._generate_event_signals(analysis_data)
            momentum_signals = self._generate_momentum_signals(analysis_data)
            
            # Combine all signals
            all_signals = fundamental_signals + technical_signals + event_signals + momentum_signals
            
            # Create composite signals
            composite_signal = self._create_composite_signal(symbol, all_signals, analysis_data)
            
            if composite_signal and composite_signal.confidence >= self.min_confidence_threshold:
                signals.append(composite_signal)
            
            # Generate additional specialized signals
            earnings_signals = self._generate_earnings_signals(analysis_data)
            order_announcement_signals = self._generate_order_announcement_signals(analysis_data)
            
            signals.extend(earnings_signals)
            signals.extend(order_announcement_signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals for {analysis_data.get('symbol', 'unknown')}: {e}")
            return []
    
    def _generate_fundamental_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals based on fundamental analysis"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            analysis = analysis_data.get('analysis', {})
            
            # Check for fundamental strength from value analysis
            if 'value_analysis' in analysis:
                value_score = analysis['value_analysis'].get('overall_score', 0)
                
                if value_score >= 80:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=min(0.9, value_score / 100),
                        reason=f"Strong fundamental value score: {value_score:.1f}/100",
                        data_sources=['fundamental'],
                        timestamp=timezone.now(),
                        metadata={
                            'value_score': value_score,
                            'signal_type': 'fundamental_value',
                            'pe_score': analysis['value_analysis'].get('pe_score', 0),
                            'pb_score': analysis['value_analysis'].get('pb_score', 0)
                        }
                    ))
                elif value_score <= 30:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='SELL',
                        confidence=min(0.8, (100 - value_score) / 100),
                        reason=f"Weak fundamental value score: {value_score:.1f}/100",
                        data_sources=['fundamental'],
                        timestamp=timezone.now(),
                        metadata={
                            'value_score': value_score,
                            'signal_type': 'fundamental_weakness'
                        }
                    ))
            
            # Check growth analysis
            if 'growth_analysis' in analysis:
                growth_score = analysis['growth_analysis'].get('overall_score', 0)
                
                if growth_score >= 75:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=min(0.85, growth_score / 100),
                        reason=f"Strong growth prospects: {growth_score:.1f}/100",
                        data_sources=['fundamental'],
                        timestamp=timezone.now(),
                        metadata={
                            'growth_score': growth_score,
                            'signal_type': 'growth_momentum',
                            'revenue_growth_score': analysis['growth_analysis'].get('revenue_growth_score', 0),
                            'profit_growth_score': analysis['growth_analysis'].get('profit_growth_score', 0)
                        }
                    ))
            
            # Check financial health from XBRL data
            if 'overall_financial_health' in analysis:
                health_score = analysis['overall_financial_health']
                
                if health_score >= 80:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=0.7,
                        reason=f"Excellent financial health: {health_score:.1f}/100",
                        data_sources=['fundamental', 'xbrl'],
                        timestamp=timezone.now(),
                        metadata={
                            'health_score': health_score,
                            'signal_type': 'financial_strength',
                            'liquidity_score': analysis.get('liquidity_score', 0),
                            'leverage_score': analysis.get('leverage_score', 0)
                        }
                    ))
            
            # Check profitability metrics
            profitability_score = analysis.get('profitability_score', 0)
            if profitability_score >= 75:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action='BUY',
                    confidence=0.6,
                    reason=f"Strong profitability: {profitability_score:.1f}/100",
                    data_sources=['fundamental'],
                    timestamp=timezone.now(),
                    metadata={
                        'profitability_score': profitability_score,
                        'signal_type': 'profitability_strength'
                    }
                ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating fundamental signals: {e}")
            return []
    
    def _generate_technical_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals based on technical analysis (EFI crossover)"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            
            # Get market data for technical analysis
            market_data = self._get_market_data(symbol)
            
            if market_data is None or len(market_data) < 20:
                logger.warning(f"Insufficient market data for {symbol}")
                return signals
            
            # Generate EFI crossover signals
            efi_signals = self.tech_signal_generator.generate_efi_crossover_signals(
                market_data, threshold=self.efi_threshold
            )
            
            # Check for recent EFI crossover
            if len(efi_signals) > 0:
                latest_signal = efi_signals.iloc[-1]
                
                if latest_signal == 1:  # Buy signal
                    # Calculate EFI strength
                    efi_values = self.efi_indicator.calculate(market_data)
                    current_efi = efi_values.iloc[-1]
                    
                    # Determine confidence based on EFI strength
                    confidence = min(0.8, max(0.4, abs(current_efi) / 0.1))  # Scale based on EFI magnitude
                    
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=confidence,
                        reason=f"EFI({self.efi_indicator.period}) crossed above {self.efi_threshold}",
                        data_sources=['technical'],
                        timestamp=timezone.now(),
                        metadata={
                            'efi_value': float(current_efi),
                            'efi_threshold': self.efi_threshold,
                            'signal_type': 'efi_crossover_buy',
                            'technical_strength': 'strong' if current_efi > 0.05 else 'moderate'
                        }
                    ))
                
                elif latest_signal == -1:  # Sell signal
                    efi_values = self.efi_indicator.calculate(market_data)
                    current_efi = efi_values.iloc[-1]
                    
                    confidence = min(0.7, max(0.3, abs(current_efi) / 0.1))
                    
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='SELL',
                        confidence=confidence,
                        reason=f"EFI({self.efi_indicator.period}) crossed below {self.efi_threshold}",
                        data_sources=['technical'],
                        timestamp=timezone.now(),
                        metadata={
                            'efi_value': float(current_efi),
                            'efi_threshold': self.efi_threshold,
                            'signal_type': 'efi_crossover_sell',
                            'technical_weakness': 'strong' if current_efi < -0.05 else 'moderate'
                        }
                    ))
            
            # Additional technical analysis
            volume_signals = self._check_volume_patterns(market_data, symbol)
            signals.extend(volume_signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating technical signals for {symbol}: {e}")
            return []
    
    def _generate_event_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals based on corporate events"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            
            # Check for recent high-impact events
            recent_events = CorporateEvent.objects.filter(
                company__symbol=symbol,
                announcement_date__gte=timezone.now() - timedelta(days=7),
                impact_level__in=['HIGH', 'MEDIUM']
            ).order_by('-announcement_date')
            
            for event in recent_events[:3]:  # Check last 3 significant events
                confidence = 0.7 if event.impact_level == 'HIGH' else 0.5
                
                if event.event_type == 'order_received':
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=confidence,
                        reason=f"Major order announcement: {event.title}",
                        data_sources=['event'],
                        timestamp=timezone.now(),
                        metadata={
                            'event_type': event.event_type,
                            'event_date': event.announcement_date.isoformat(),
                            'impact_level': event.impact_level,
                            'signal_type': 'order_announcement',
                            'expected_price_impact': event.expected_price_impact
                        }
                    ))
                
                elif event.event_type == 'results_announcement':
                    # Check if results were positive based on event data
                    if self._assess_results_sentiment(event.event_data):
                        signals.append(TradingSignal(
                            symbol=symbol,
                            action='BUY',
                            confidence=confidence * 0.8,  # Slightly lower confidence
                            reason=f"Positive results announcement: {event.title}",
                            data_sources=['event'],
                            timestamp=timezone.now(),
                            metadata={
                                'event_type': event.event_type,
                                'event_date': event.announcement_date.isoformat(),
                                'signal_type': 'positive_results',
                                'results_sentiment': 'positive'
                            }
                        ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating event signals for {symbol}: {e}")
            return []
    
    def _generate_momentum_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals based on momentum analysis"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            analysis = analysis_data.get('analysis', {})
            
            # Check quarterly momentum
            if 'momentum_score' in analysis:
                momentum_score = analysis['momentum_score']
                
                if momentum_score >= 70:
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=0.6,
                        reason=f"Strong quarterly momentum: {momentum_score:.1f}/100",
                        data_sources=['momentum'],
                        timestamp=timezone.now(),
                        metadata={
                            'momentum_score': momentum_score,
                            'signal_type': 'quarterly_momentum',
                            'qoq_revenue_growth': analysis.get('qoq_revenue_growth', 0),
                            'qoq_profit_growth': analysis.get('qoq_profit_growth', 0)
                        }
                    ))
            
            # Check revenue and profit momentum trends
            revenue_momentum = analysis.get('revenue_momentum', '')
            profit_momentum = analysis.get('profit_momentum', '')
            
            if revenue_momentum == 'STRONG' and profit_momentum in ['STRONG', 'MODERATE']:
                signals.append(TradingSignal(
                    symbol=symbol,
                    action='BUY',
                    confidence=0.65,
                    reason=f"Strong revenue momentum with {profit_momentum.lower()} profit growth",
                    data_sources=['momentum'],
                    timestamp=timezone.now(),
                    metadata={
                        'revenue_momentum': revenue_momentum,
                        'profit_momentum': profit_momentum,
                        'signal_type': 'revenue_profit_momentum'
                    }
                ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating momentum signals for {symbol}: {e}")
            return []
    
    def _generate_earnings_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals based on earnings surprises"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            estimates_comparison = analysis_data.get('estimates_comparison', {})
            
            # Check for earnings surprises
            if 'revenue_surprise_pct' in estimates_comparison:
                revenue_surprise = estimates_comparison['revenue_surprise_pct']
                
                if revenue_surprise >= 15:  # 15% positive surprise
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=0.8,
                        reason=f"Strong revenue surprise: +{revenue_surprise:.1f}% vs estimates",
                        data_sources=['earnings'],
                        timestamp=timezone.now(),
                        metadata={
                            'revenue_surprise_pct': revenue_surprise,
                            'signal_type': 'revenue_surprise',
                            'surprise_magnitude': 'strong' if revenue_surprise >= 20 else 'moderate'
                        }
                    ))
                elif revenue_surprise <= -10:  # 10% negative surprise
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='SELL',
                        confidence=0.7,
                        reason=f"Revenue disappointment: {revenue_surprise:.1f}% vs estimates",
                        data_sources=['earnings'],
                        timestamp=timezone.now(),
                        metadata={
                            'revenue_surprise_pct': revenue_surprise,
                            'signal_type': 'revenue_disappointment'
                        }
                    ))
            
            # Check EPS surprises
            if 'eps_surprise_pct' in estimates_comparison:
                eps_surprise = estimates_comparison['eps_surprise_pct']
                
                if eps_surprise >= 20:  # 20% EPS surprise
                    signals.append(TradingSignal(
                        symbol=symbol,
                        action='BUY',
                        confidence=0.75,
                        reason=f"Strong EPS surprise: +{eps_surprise:.1f}% vs estimates",
                        data_sources=['earnings'],
                        timestamp=timezone.now(),
                        metadata={
                            'eps_surprise_pct': eps_surprise,
                            'signal_type': 'eps_surprise'
                        }
                    ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating earnings signals for {symbol}: {e}")
            return []
    
    def _generate_order_announcement_signals(self, analysis_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals specifically for order announcements"""
        signals = []
        
        try:
            symbol = analysis_data.get('symbol')
            
            # Check for very recent order announcements (last 24 hours)
            recent_orders = CorporateEvent.objects.filter(
                company__symbol=symbol,
                event_type='order_received',
                announcement_date__gte=timezone.now() - timedelta(hours=24),
                is_processed=False  # Not yet processed for trading
            )
            
            for order_event in recent_orders:
                # Extract order value if available
                order_value = self._extract_order_value(order_event.event_data)
                
                if order_value:
                    # Calculate confidence based on order size relative to market cap
                    company_market_cap = self._get_company_market_cap(symbol)
                    
                    if company_market_cap:
                        order_to_mcap_ratio = order_value / company_market_cap
                        
                        if order_to_mcap_ratio >= 0.1:  # Order >= 10% of market cap
                            confidence = 0.9
                            reason = f"Major order worth ₹{order_value/10000000:.0f}Cr ({order_to_mcap_ratio*100:.1f}% of market cap)"
                        elif order_to_mcap_ratio >= 0.05:  # Order >= 5% of market cap
                            confidence = 0.75
                            reason = f"Significant order worth ₹{order_value/10000000:.0f}Cr ({order_to_mcap_ratio*100:.1f}% of market cap)"
                        else:
                            confidence = 0.6
                            reason = f"New order announcement worth ₹{order_value/10000000:.0f}Cr"
                        
                        signals.append(TradingSignal(
                            symbol=symbol,
                            action='BUY',
                            confidence=confidence,
                            reason=reason,
                            data_sources=['event', 'order'],
                            timestamp=timezone.now(),
                            metadata={
                                'order_value': order_value,
                                'order_to_mcap_ratio': order_to_mcap_ratio,
                                'signal_type': 'fresh_order_announcement',
                                'order_announcement_time': order_event.announcement_date.isoformat()
                            }
                        ))
                        
                        # Mark as processed
                        order_event.is_processed = True
                        order_event.save()
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating order announcement signals for {symbol}: {e}")
            return []
    
    def _create_composite_signal(self, symbol: str, all_signals: List[TradingSignal], analysis_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Create a composite signal from multiple signal sources"""
        try:
            if not all_signals:
                return None
            
            # Separate buy and sell signals
            buy_signals = [s for s in all_signals if s.action == 'BUY']
            sell_signals = [s for s in all_signals if s.action == 'SELL']
            
            # Calculate weighted scores
            buy_score = self._calculate_weighted_score(buy_signals)
            sell_score = self._calculate_weighted_score(sell_signals)
            
            # Determine final action
            if buy_score > sell_score and buy_score >= self.min_confidence_threshold:
                action = 'BUY'
                confidence = min(0.95, buy_score)
                reasons = [s.reason for s in buy_signals]
                data_sources = list(set([ds for s in buy_signals for ds in s.data_sources]))
            elif sell_score > buy_score and sell_score >= self.min_confidence_threshold:
                action = 'SELL'
                confidence = min(0.95, sell_score)
                reasons = [s.reason for s in sell_signals]
                data_sources = list(set([ds for s in sell_signals for ds in s.data_sources]))
            else:
                return None  # No clear signal
            
            # Create composite reason
            composite_reason = f"Composite signal ({len(reasons)} factors): " + "; ".join(reasons[:3])
            if len(reasons) > 3:
                composite_reason += f" + {len(reasons) - 3} more factors"
            
            # Add risk management metadata
            risk_metadata = self._calculate_risk_metadata(symbol, confidence, analysis_data)
            
            return TradingSignal(
                symbol=symbol,
                action=action,
                confidence=confidence,
                reason=composite_reason,
                data_sources=data_sources,
                timestamp=timezone.now(),
                metadata={
                    'signal_type': 'composite',
                    'component_signals_count': len(all_signals),
                    'buy_signals_count': len(buy_signals),
                    'sell_signals_count': len(sell_signals),
                    'buy_score': buy_score,
                    'sell_score': sell_score,
                    'risk_management': risk_metadata
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating composite signal for {symbol}: {e}")
            return None
    
    def _calculate_weighted_score(self, signals: List[TradingSignal]) -> float:
        """Calculate weighted score for a list of signals"""
        try:
            if not signals:
                return 0.0
            
            total_weighted_confidence = 0.0
            total_weight = 0.0
            
            for signal in signals:
                # Determine weight based on data sources
                signal_weight = 0.0
                for source in signal.data_sources:
                    signal_weight += self.signal_weights.get(source, 0.1)
                
                # Normalize weight if multiple sources
                if len(signal.data_sources) > 1:
                    signal_weight = signal_weight / len(signal.data_sources)
                
                total_weighted_confidence += signal.confidence * signal_weight
                total_weight += signal_weight
            
            return total_weighted_confidence / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating weighted score: {e}")
            return 0.0
    
    def _calculate_risk_metadata(self, symbol: str, confidence: float, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk management metadata for the signal"""
        try:
            risk_metadata = {
                'max_position_size_pct': self.max_position_size * 100,
                'max_risk_per_trade_pct': self.max_portfolio_risk * 100,
                'suggested_stop_loss_pct': 5.0,  # Default 5% stop loss
                'risk_level': 'MEDIUM'
            }
            
            # Adjust risk based on confidence
            if confidence >= 0.8:
                risk_metadata['suggested_stop_loss_pct'] = 3.0  # Tighter stop for high confidence
                risk_metadata['risk_level'] = 'LOW'
            elif confidence <= 0.6:
                risk_metadata['suggested_stop_loss_pct'] = 7.0  # Wider stop for lower confidence
                risk_metadata['risk_level'] = 'HIGH'
            
            # Adjust based on volatility if available
            volatility = analysis_data.get('volatility', 0)
            if volatility > 0.3:  # High volatility
                risk_metadata['suggested_stop_loss_pct'] *= 1.5
                risk_metadata['risk_level'] = 'HIGH'
            
            return risk_metadata
            
        except Exception as e:
            logger.error(f"Error calculating risk metadata: {e}")
            return {'risk_level': 'MEDIUM'}
    
    def _get_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """Get market data for technical analysis"""
        try:
            # This is a placeholder - you would implement actual market data fetching
            # from your data source (e.g., NSE API, database, etc.)
            
            # For now, return None to indicate data not available
            # In production, this would fetch OHLCV data for the symbol
            logger.warning(f"Market data fetching not implemented for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    def _check_volume_patterns(self, market_data: pd.DataFrame, symbol: str) -> List[TradingSignal]:
        """Check for unusual volume patterns"""
        signals = []
        
        try:
            if 'volume' not in market_data.columns or len(market_data) < 20:
                return signals
            
            # Calculate average volume
            avg_volume = market_data['volume'].rolling(window=20).mean()
            current_volume = market_data['volume'].iloc[-1]
            recent_avg_volume = avg_volume.iloc[-1]
            
            # Check for volume spike
            if current_volume > recent_avg_volume * 2:  # 2x average volume
                signals.append(TradingSignal(
                    symbol=symbol,
                    action='BUY',
                    confidence=0.5,
                    reason=f"Volume spike: {current_volume/recent_avg_volume:.1f}x average volume",
                    data_sources=['technical'],
                    timestamp=timezone.now(),
                    metadata={
                        'volume_ratio': current_volume / recent_avg_volume,
                        'signal_type': 'volume_spike'
                    }
                ))
            
            return signals
            
        except Exception as e:
            logger.error(f"Error checking volume patterns for {symbol}: {e}")
            return []
    
    def _assess_results_sentiment(self, event_data: Dict[str, Any]) -> bool:
        """Assess if results announcement is positive"""
        try:
            # This is a simplified sentiment analysis
            # In production, you would use NLP or structured data analysis
            
            if not event_data:
                return False
            
            # Check for positive keywords in results data
            positive_indicators = [
                'profit growth', 'revenue growth', 'beat estimates', 
                'strong performance', 'record profit', 'record revenue',
                'exceeded expectations', 'positive outlook'
            ]
            
            negative_indicators = [
                'loss', 'decline', 'below estimates', 'disappointing',
                'weak performance', 'reduced guidance', 'challenges'
            ]
            
            text_data = str(event_data).lower()
            
            positive_score = sum(1 for indicator in positive_indicators if indicator in text_data)
            negative_score = sum(1 for indicator in negative_indicators if indicator in text_data)
            
            return positive_score > negative_score
            
        except Exception as e:
            logger.error(f"Error assessing results sentiment: {e}")
            return False
    
    def _extract_order_value(self, event_data: Dict[str, Any]) -> Optional[float]:
        """Extract order value from event data"""
        try:
            if not event_data:
                return None
            
            # Look for order value in various formats
            order_value = event_data.get('order_value')
            if order_value:
                return float(order_value)
            
            # Try to extract from text description
            import re
            description = str(event_data.get('description', ''))
            
            # Look for patterns like "₹100 crore", "Rs. 500 Cr", etc.
            patterns = [
                r'₹\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*crore',
                r'rs\.?\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*cr',
                r'inr\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*crore'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, description.lower())
                if match:
                    value_str = match.group(1).replace(',', '')
                    return float(value_str) * 10000000  # Convert crores to units
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting order value: {e}")
            return None
    
    def _get_company_market_cap(self, symbol: str) -> Optional[float]:
        """Get company market cap"""
        try:
            company = Company.objects.get(symbol=symbol)
            valuation_metrics = getattr(company, 'valuation_metrics', None)
            
            if valuation_metrics and valuation_metrics.market_cap:
                return float(valuation_metrics.market_cap)
            
            return None
            
        except Company.DoesNotExist:
            logger.warning(f"Company {symbol} not found")
            return None
        except Exception as e:
            logger.error(f"Error getting market cap for {symbol}: {e}")
            return None

class RiskManagedSignalGenerator(ComprehensiveTradingSignalGenerator):
    """Extended signal generator with advanced risk management"""
    
    def __init__(self):
        super().__init__()
        self.portfolio_heat = 0.0  # Current portfolio risk
        self.max_portfolio_heat = 6.0  # Maximum total portfolio risk (6%)
        self.correlation_matrix = {}  # For sector/stock correlation analysis
    
    def generate_risk_adjusted_signals(self, analysis_data: Dict[str, Any], current_portfolio: Dict[str, Any] = None) -> List[TradingSignal]:
        """Generate signals with portfolio-level risk management"""
        try:
            # Generate base signals
            base_signals = self.generate_signals(analysis_data)
            
            if not base_signals:
                return []
            
            # Apply portfolio-level risk management
            risk_adjusted_signals = []
            
            for signal in base_signals:
                if signal.action == 'BUY':
                    # Check if we can add more risk to portfolio
                    if self._can_add_position(signal, current_portfolio):
                        # Adjust position size based on portfolio risk
                        adjusted_signal = self._adjust_position_size(signal, current_portfolio)
                        risk_adjusted_signals.append(adjusted_signal)
                    else:
                        logger.info(f"Skipping {signal.symbol} due to portfolio risk limits")
                else:
                    # Sell signals help reduce risk
                    risk_adjusted_signals.append(signal)
            
            return risk_adjusted_signals
            
        except Exception as e:
            logger.error(f"Error generating risk-adjusted signals: {e}")
            return base_signals  # Fallback to base signals
    
    def _can_add_position(self, signal: TradingSignal, current_portfolio: Dict[str, Any] = None) -> bool:
        """Check if we can add a new position given current portfolio risk"""
        try:
            if not current_portfolio:
                return True
            
            # Calculate current portfolio heat
            current_heat = sum(pos.get('risk_amount', 0) for pos in current_portfolio.values())
            
            # Estimate risk for new position
            estimated_risk = self._estimate_position_risk(signal)
            
            return (current_heat + estimated_risk) <= self.max_portfolio_heat
            
        except Exception as e:
            logger.error(f"Error checking portfolio capacity: {e}")
            return True  # Default to allowing position
    
    def _estimate_position_risk(self, signal: TradingSignal) -> float:
        """Estimate risk amount for a new position"""
        try:
            # Base risk from signal metadata
            risk_metadata = signal.metadata.get('risk_management', {})
            base_risk = risk_metadata.get('max_risk_per_trade_pct', 2.0)
            
            # Adjust based on confidence
            confidence_adjustment = 1.0 / signal.confidence if signal.confidence > 0 else 1.0
            
            return base_risk * confidence_adjustment
            
        except Exception as e:
            logger.error(f"Error estimating position risk: {e}")
            return 2.0  # Default 2% risk
    
    def _adjust_position_size(self, signal: TradingSignal, current_portfolio: Dict[str, Any] = None) -> TradingSignal:
        """Adjust position size based on portfolio risk"""
        try:
            # Create a copy of the signal with adjusted metadata
            adjusted_signal = TradingSignal(
                symbol=signal.symbol,
                action=signal.action,
                confidence=signal.confidence,
                reason=signal.reason,
                data_sources=signal.data_sources,
                timestamp=signal.timestamp,
                metadata=signal.metadata.copy()
            )
            
            # Calculate available risk budget
            current_heat = sum(pos.get('risk_amount', 0) for pos in (current_portfolio or {}).values())
            available_risk = self.max_portfolio_heat - current_heat
            
            # Adjust position size to fit available risk
            original_risk = signal.metadata.get('risk_management', {}).get('max_risk_per_trade_pct', 2.0)
            adjusted_risk = min(original_risk, available_risk)
            
            if 'risk_management' not in adjusted_signal.metadata:
                adjusted_signal.metadata['risk_management'] = {}
            
            adjusted_signal.metadata['risk_management']['adjusted_risk_pct'] = adjusted_risk
            adjusted_signal.metadata['risk_management']['position_size_adjustment'] = adjusted_risk / original_risk
            
            return adjusted_signal
            
        except Exception as e:
            logger.error(f"Error adjusting position size: {e}")
            return signal  # Return original signal on error
