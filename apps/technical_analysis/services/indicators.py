# apps/technical_analysis/services/backtrader_indicators.py
import backtrader as bt
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class EFIIndicator(bt.Indicator):
    """Custom EFI Indicator for Backtrader"""
    
    lines = ('efi',)
    params = (('period', 20),)
    
    def __init__(self):
        # Price change from previous close
        price_change = self.data.close - self.data.close(-1)
        
        # High-Low range
        high_low_range = self.data.high - self.data.low
        
        # Avoid division by zero
        high_low_safe = bt.If(high_low_range > 0, high_low_range, 0.01)
        
        # Raw EFI calculation
        raw_efi = (price_change * self.data.volume) / high_low_safe
        
        # Smoothed EFI using moving average
        self.lines.efi = bt.indicators.MovingAverageSimple(raw_efi, period=self.params.period)

class TechnicalAnalysisStrategy(bt.Strategy):
    """Simple strategy just to calculate indicators - no trading logic"""
    
    params = (
        ('efi_period', 20),
        ('rsi_period', 14),
        ('macd_fast', 12),
        ('macd_slow', 26),
        ('macd_signal', 9),
    )
    
    def __init__(self):
        # Initialize all indicators
        self.efi = EFIIndicator(period=self.params.efi_period)
        self.rsi = bt.indicators.RSI(period=self.params.rsi_period)
        self.macd = bt.indicators.MACD(
            fast=self.params.macd_fast,
            slow=self.params.macd_slow,
            signal=self.params.macd_signal
        )
        self.sma_20 = bt.indicators.SMA(period=20)
        self.sma_50 = bt.indicators.SMA(period=50)
        self.sma_200 = bt.indicators.SMA(period=200)
        self.ema_12 = bt.indicators.EMA(period=12)
        self.ema_26 = bt.indicators.EMA(period=26)
        
        # Bollinger Bands
        self.bollinger = bt.indicators.BollingerBands(period=20, devfactor=2.0)
        
        # Volume indicators
        self.volume_sma = bt.indicators.SMA(self.data.volume, period=20)
        
        # ATR for volatility
        self.atr = bt.indicators.ATR(period=14)
        
        # Store indicator values for extraction
        self.indicator_values = {}
    
    def next(self):
        """Store current indicator values - no trading logic"""
        self.indicator_values = {
            'efi': self.efi[0],
            'rsi': self.rsi[0],
            'macd': self.macd.macd[0],
            'macd_signal': self.macd.signal[0],
            'macd_histogram': self.macd.histo[0],
            'sma_20': self.sma_20[0],
            'sma_50': self.sma_50[0],
            'sma_200': self.sma_200[0],
            'ema_12': self.ema_12[0],
            'ema_26': self.ema_26[0],
            'bb_upper': self.bollinger.top[0],
            'bb_middle': self.bollinger.mid[0],
            'bb_lower': self.bollinger.bot[0],
            'volume_sma': self.volume_sma[0],
            'atr': self.atr[0],
            'current_price': self.data.close[0],
            'current_volume': self.data.volume[0]
        }

class BacktraderTechnicalAnalyzer:
    """Use Backtrader only for technical indicator calculations"""
    
    def __init__(self):
        self.cerebro = None
    
    def calculate_indicators(self, data: pd.DataFrame, symbol: str = "UNKNOWN") -> Dict[str, Any]:
        """Calculate technical indicators using Backtrader"""
        try:
            if data is None or len(data) < 50:
                return {'error': 'Insufficient data for technical analysis'}
            
            # Create fresh Cerebro instance
            cerebro = bt.Cerebro()
            
            # Add strategy (just for indicator calculations)
            cerebro.addstrategy(TechnicalAnalysisStrategy)
            
            # Prepare and add data
            bt_data = self._prepare_backtrader_data(data)
            cerebro.adddata(bt_data)
            
            # Run without any trading
            cerebro.broker.setcash(1000000)  # Dummy cash
            results = cerebro.run()
            
            # Extract indicator values
            strategy_result = results[0]
            indicators = strategy_result.indicator_values
            
            # Generate signals based on indicators
            signals = self._generate_technical_signals(indicators)
            
            # Calculate additional metrics
            additional_metrics = self._calculate_additional_metrics(data, indicators)
            
            return {
                'symbol': symbol,
                'data_points': len(data),
                'last_updated': data.index[-1].isoformat(),
                'current_price': float(data['close'].iloc[-1]),
                'technical_indicators': indicators,
                'signals': signals,
                'support_resistance': self._calculate_support_resistance(data),
                'volatility': additional_metrics['volatility'],
                'trend_analysis': additional_metrics['trend'],
                'volume_analysis': additional_metrics['volume']
            }
            
        except Exception as e:
            logger.error(f"Error calculating indicators with Backtrader for {symbol}: {e}")
            return {'error': str(e)}
    
    def _prepare_backtrader_data(self, data: pd.DataFrame) -> bt.feeds.PandasData:
        """Convert pandas DataFrame to Backtrader data feed"""
        try:
            # Ensure proper column names
            df = data.copy()
            df.columns = [col.lower() for col in df.columns]
            
            # Ensure datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Create Backtrader data feed
            bt_data = bt.feeds.PandasData(
                dataname=df,
                datetime=None,  # Use index
                open='open',
                high='high',
                low='low', 
                close='close',
                volume='volume',
                openinterest=-1
            )
            
            return bt_data
            
        except Exception as e:
            logger.error(f"Error preparing Backtrader data: {e}")
            raise
    
    def _generate_technical_signals(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Generate trading signals from calculated indicators"""
        try:
            signals = {
                'overall_signal': 'HOLD',
                'confidence': 0.0,
                'individual_signals': {}
            }
            
            signal_scores = []
            
            # EFI Signal (Primary - your main strategy)
            efi = indicators.get('efi', 0)
            if efi > 0.001:  # EFI positive
                signals['individual_signals']['efi'] = {
                    'signal': 'BUY',
                    'strength': min(abs(efi) * 100, 1.0),
                    'reason': f'EFI positive ({efi:.4f})'
                }
                signal_scores.append(0.8)
            elif efi < -0.001:  # EFI negative
                signals['individual_signals']['efi'] = {
                    'signal': 'SELL',
                    'strength': min(abs(efi) * 100, 1.0),
                    'reason': f'EFI negative ({efi:.4f})'
                }
                signal_scores.append(-0.8)
            else:
                signal_scores.append(0.0)
            
            # RSI Signal
            rsi = indicators.get('rsi', 50)
            if rsi <= 30:
                signals['individual_signals']['rsi'] = {
                    'signal': 'BUY',
                    'strength': (30 - rsi) / 30,
                    'reason': f'RSI oversold ({rsi:.1f})'
                }
                signal_scores.append(0.6)
            elif rsi >= 70:
                signals['individual_signals']['rsi'] = {
                    'signal': 'SELL', 
                    'strength': (rsi - 70) / 30,
                    'reason': f'RSI overbought ({rsi:.1f})'
                }
                signal_scores.append(-0.6)
            else:
                signal_scores.append(0.0)
            
            # MACD Signal
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            if macd > macd_signal:
                signals['individual_signals']['macd'] = {
                    'signal': 'BUY',
                    'strength': 0.5,
                    'reason': 'MACD above signal line'
                }
                signal_scores.append(0.5)
            elif macd < macd_signal:
                signals['individual_signals']['macd'] = {
                    'signal': 'SELL',
                    'strength': 0.5,
                    'reason': 'MACD below signal line'
                }
                signal_scores.append(-0.5)
            else:
                signal_scores.append(0.0)
            
            # Moving Average Trend
            current_price = indicators.get('current_price', 0)
            sma_20 = indicators.get('sma_20', 0)
            sma_50 = indicators.get('sma_50', 0)
            
            if current_price > sma_20 > sma_50:
                signals['individual_signals']['trend'] = {
                    'signal': 'BUY',
                    'strength': 0.4,
                    'reason': 'Price above moving averages'
                }
                signal_scores.append(0.4)
            elif current_price < sma_20 < sma_50:
                signals['individual_signals']['trend'] = {
                    'signal': 'SELL',
                    'strength': 0.4,
                    'reason': 'Price below moving averages'
                }
                signal_scores.append(-0.4)
            else:
                signal_scores.append(0.0)
            
            # Calculate overall signal
            avg_score = sum(signal_scores) / len(signal_scores) if signal_scores else 0.0
            
            if avg_score >= 0.3:
                signals['overall_signal'] = 'BUY'
                signals['confidence'] = min(avg_score, 1.0)
            elif avg_score <= -0.3:
                signals['overall_signal'] = 'SELL'
                signals['confidence'] = min(abs(avg_score), 1.0)
            else:
                signals['overall_signal'] = 'HOLD'
                signals['confidence'] = abs(avg_score)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating signals: {e}")
            return {'overall_signal': 'HOLD', 'confidence': 0.0}
    
    def _calculate_support_resistance(self, data: pd.DataFrame) -> Dict[str, list]:
        """Calculate support and resistance levels"""
        try:
            recent_data = data.tail(50)
            
            # Simple pivot point calculation
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            
            resistance_levels = []
            support_levels = []
            
            # Find local maxima and minima
            for i in range(2, len(highs) - 2):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    resistance_levels.append(float(highs[i]))
            
            for i in range(2, len(lows) - 2):
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    support_levels.append(float(lows[i]))
            
            return {
                'resistance': sorted(resistance_levels, reverse=True)[:3],
                'support': sorted(support_levels)[:3]
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {'resistance': [], 'support': []}
    
    def _calculate_additional_metrics(self, data: pd.DataFrame, indicators: Dict[str, float]) -> Dict[str, Any]:
        """Calculate additional technical metrics"""
        try:
            # Volatility
            returns = data['close'].pct_change().dropna()
            volatility = {
                'daily_volatility': float(returns.std()),
                'annualized_volatility': float(returns.std() * np.sqrt(252)),
                'atr': indicators.get('atr', 0.0)
            }
            
            # Trend analysis
            sma_20 = indicators.get('sma_20', 0)
            sma_50 = indicators.get('sma_50', 0)
            current_price = indicators.get('current_price', 0)
            
            if current_price > sma_20 > sma_50:
                trend_direction = 'UPTREND'
            elif current_price < sma_20 < sma_50:
                trend_direction = 'DOWNTREND' 
            else:
                trend_direction = 'SIDEWAYS'
            
            trend = {
                'direction': trend_direction,
                'strength': abs(current_price - sma_20) / sma_20 * 100 if sma_20 > 0 else 0
            }
            
            # Volume analysis
            current_volume = indicators.get('current_volume', 0)
            avg_volume = indicators.get('volume_sma', 0)
            
            volume = {
                'current_volume': current_volume,
                'average_volume': avg_volume,
                'volume_ratio': current_volume / avg_volume if avg_volume > 0 else 1.0,
                'volume_trend': 'HIGH' if current_volume > avg_volume * 1.5 else 'NORMAL' if current_volume > avg_volume * 0.8 else 'LOW'
            }
            
            return {
                'volatility': volatility,
                'trend': trend,
                'volume': volume
            }
            
        except Exception as e:
            logger.error(f"Error calculating additional metrics: {e}")
            return {'volatility': {}, 'trend': {}, 'volume': {}}
