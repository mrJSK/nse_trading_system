# apps/technical_analysis/services/data_processor.py
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from decimal import Decimal
import logging
from core.interfaces.market_data_interfaces import TechnicalDataProcessorInterface
from .indicators import EFIIndicator, RSIIndicator, MACDIndicator

logger = logging.getLogger(__name__)

class TechnicalDataProcessor(TechnicalDataProcessorInterface):
    """Single responsibility: Process technical market data"""
    
    def __init__(self):
        self.efi_indicator = EFIIndicator(period=20)
        self.rsi_indicator = RSIIndicator(period=14)
        self.macd_indicator = MACDIndicator()
        
        # Technical analysis parameters
        self.sma_periods = [20, 50, 200]
        self.ema_periods = [12, 26]
    
    def process_candlestick_data(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Process candlestick data for comprehensive technical analysis"""
        try:
            if data is None or len(data) < 20:
                return {'error': 'Insufficient data for analysis'}
            
            # Calculate all technical indicators
            processed_data = self.calculate_indicators(data)
            
            # Generate technical signals
            signals = self._generate_technical_signals(processed_data)
            
            # Calculate support and resistance levels
            support_resistance = self._calculate_support_resistance(processed_data)
            
            # Analyze price patterns
            patterns = self._identify_patterns(processed_data)
            
            # Calculate volatility metrics
            volatility = self._calculate_volatility(processed_data)
            
            return {
                'symbol': symbol,
                'data_points': len(processed_data),
                'last_updated': processed_data.index[-1].isoformat(),
                'current_price': float(processed_data['close'].iloc[-1]),
                'technical_indicators': {
                    'efi': float(processed_data['efi'].iloc[-1]) if 'efi' in processed_data.columns else None,
                    'rsi': float(processed_data['rsi'].iloc[-1]) if 'rsi' in processed_data.columns else None,
                    'macd': float(processed_data['macd'].iloc[-1]) if 'macd' in processed_data.columns else None,
                    'sma_20': float(processed_data['sma_20'].iloc[-1]) if 'sma_20' in processed_data.columns else None,
                    'sma_50': float(processed_data['sma_50'].iloc[-1]) if 'sma_50' in processed_data.columns else None,
                },
                'signals': signals,
                'support_resistance': support_resistance,
                'patterns': patterns,
                'volatility': volatility,
                'trend_analysis': self._analyze_trend(processed_data)
            }
            
        except Exception as e:
            logger.error(f"Error processing candlestick data for {symbol}: {e}")
            return {'error': str(e)}
    
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate comprehensive technical indicators"""
        try:
            df = data.copy()
            
            # Moving averages
            for period in self.sma_periods:
                df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            
            for period in self.ema_periods:
                df[f'ema_{period}'] = df['close'].ewm(span=period).mean()
            
            # EFI (Ease of Movement)
            df['efi'] = self.efi_indicator.calculate(df)
            
            # RSI
            df['rsi'] = self.rsi_indicator.calculate(df)
            
            # MACD
            macd_data = self.macd_indicator.calculate(df)
            df['macd'] = macd_data['macd']
            df['macd_signal'] = macd_data['signal']
            df['macd_histogram'] = macd_data['histogram']
            
            # Bollinger Bands
            bb_data = self._calculate_bollinger_bands(df)
            df['bb_upper'] = bb_data['upper']
            df['bb_middle'] = bb_data['middle']
            df['bb_lower'] = bb_data['lower']
            
            # Volume indicators
            df['volume_sma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma']
            
            # Price change indicators
            df['price_change'] = df['close'].pct_change()
            df['price_change_5d'] = df['close'].pct_change(periods=5)
            df['price_change_20d'] = df['close'].pct_change(periods=20)
            
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return data
    
    def _generate_technical_signals(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Generate technical trading signals"""
        try:
            signals = {
                'overall_signal': 'HOLD',
                'confidence': 0.0,
                'individual_signals': {}
            }
            
            latest = data.iloc[-1]
            
            # EFI Signal (your primary strategy)
            if 'efi' in data.columns:
                efi_current = latest['efi']
                efi_previous = data['efi'].iloc[-2] if len(data) > 1 else 0
                
                if efi_current > 0 and efi_previous <= 0:
                    signals['individual_signals']['efi'] = {
                        'signal': 'BUY',
                        'strength': min(abs(efi_current) * 10, 1.0),
                        'reason': f'EFI crossed above 0 ({efi_current:.4f})'
                    }
                elif efi_current < 0 and efi_previous >= 0:
                    signals['individual_signals']['efi'] = {
                        'signal': 'SELL',
                        'strength': min(abs(efi_current) * 10, 1.0),
                        'reason': f'EFI crossed below 0 ({efi_current:.4f})'
                    }
            
            # RSI Signal
            if 'rsi' in data.columns:
                rsi = latest['rsi']
                if rsi <= 30:
                    signals['individual_signals']['rsi'] = {
                        'signal': 'BUY',
                        'strength': (30 - rsi) / 30,
                        'reason': f'RSI oversold ({rsi:.1f})'
                    }
                elif rsi >= 70:
                    signals['individual_signals']['rsi'] = {
                        'signal': 'SELL',
                        'strength': (rsi - 70) / 30,
                        'reason': f'RSI overbought ({rsi:.1f})'
                    }
            
            # MACD Signal
            if 'macd' in data.columns and 'macd_signal' in data.columns:
                macd = latest['macd']
                macd_signal = latest['macd_signal']
                macd_prev = data['macd'].iloc[-2] if len(data) > 1 else 0
                signal_prev = data['macd_signal'].iloc[-2] if len(data) > 1 else 0
                
                if macd > macd_signal and macd_prev <= signal_prev:
                    signals['individual_signals']['macd'] = {
                        'signal': 'BUY',
                        'strength': 0.6,
                        'reason': 'MACD bullish crossover'
                    }
                elif macd < macd_signal and macd_prev >= signal_prev:
                    signals['individual_signals']['macd'] = {
                        'signal': 'SELL',
                        'strength': 0.6,
                        'reason': 'MACD bearish crossover'
                    }
            
            # Moving Average Signal
            if 'sma_20' in data.columns and 'sma_50' in data.columns:
                price = latest['close']
                sma_20 = latest['sma_20']
                sma_50 = latest['sma_50']
                
                if price > sma_20 > sma_50:
                    signals['individual_signals']['trend'] = {
                        'signal': 'BUY',
                        'strength': 0.5,
                        'reason': 'Price above short and long term averages'
                    }
                elif price < sma_20 < sma_50:
                    signals['individual_signals']['trend'] = {
                        'signal': 'SELL',
                        'strength': 0.5,
                        'reason': 'Price below short and long term averages'
                    }
            
            # Calculate overall signal
            signals = self._calculate_overall_signal(signals)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating technical signals: {e}")
            return {'overall_signal': 'HOLD', 'confidence': 0.0}
    
    def _calculate_overall_signal(self, signals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall signal from individual signals"""
        try:
            individual_signals = signals.get('individual_signals', {})
            
            if not individual_signals:
                return signals
            
            buy_score = 0.0
            sell_score = 0.0
            total_weight = 0.0
            
            # Weight different signals
            signal_weights = {
                'efi': 0.4,  # Highest weight for your primary strategy
                'rsi': 0.2,
                'macd': 0.2,
                'trend': 0.2
            }
            
            for signal_name, signal_data in individual_signals.items():
                weight = signal_weights.get(signal_name, 0.1)
                strength = signal_data.get('strength', 0.0)
                
                if signal_data.get('signal') == 'BUY':
                    buy_score += weight * strength
                elif signal_data.get('signal') == 'SELL':
                    sell_score += weight * strength
                
                total_weight += weight
            
            # Determine overall signal
            if buy_score > sell_score and buy_score > 0.3:
                signals['overall_signal'] = 'BUY'
                signals['confidence'] = min(buy_score / total_weight, 1.0)
            elif sell_score > buy_score and sell_score > 0.3:
                signals['overall_signal'] = 'SELL'
                signals['confidence'] = min(sell_score / total_weight, 1.0)
            else:
                signals['overall_signal'] = 'HOLD'
                signals['confidence'] = abs(buy_score - sell_score) / total_weight
            
            return signals
            
        except Exception as e:
            logger.error(f"Error calculating overall signal: {e}")
            return signals
    
    def _calculate_support_resistance(self, data: pd.DataFrame) -> Dict[str, List[float]]:
        """Calculate support and resistance levels"""
        try:
            # Use recent 50 periods for S&R calculation
            recent_data = data.tail(50)
            
            # Find local maxima and minima
            highs = recent_data['high'].values
            lows = recent_data['low'].values
            
            # Simple S&R calculation using pivot points
            resistance_levels = []
            support_levels = []
            
            # Find resistance levels (local highs)
            for i in range(2, len(highs) - 2):
                if (highs[i] > highs[i-1] and highs[i] > highs[i-2] and 
                    highs[i] > highs[i+1] and highs[i] > highs[i+2]):
                    resistance_levels.append(float(highs[i]))
            
            # Find support levels (local lows)
            for i in range(2, len(lows) - 2):
                if (lows[i] < lows[i-1] and lows[i] < lows[i-2] and 
                    lows[i] < lows[i+1] and lows[i] < lows[i+2]):
                    support_levels.append(float(lows[i]))
            
            # Sort and take strongest levels
            resistance_levels = sorted(resistance_levels, reverse=True)[:3]
            support_levels = sorted(support_levels)[:3]
            
            return {
                'resistance': resistance_levels,
                'support': support_levels
            }
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {e}")
            return {'resistance': [], 'support': []}
    
    def _identify_patterns(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Identify chart patterns"""
        try:
            patterns = {
                'doji': False,
                'hammer': False,
                'shooting_star': False,
                'bullish_engulfing': False,
                'bearish_engulfing': False
            }
            
            if len(data) < 2:
                return patterns
            
            # Get last two candles
            current = data.iloc[-1]
            previous = data.iloc[-2]
            
            # Doji pattern
            body_size = abs(current['close'] - current['open'])
            candle_range = current['high'] - current['low']
            
            if candle_range > 0 and body_size / candle_range < 0.1:
                patterns['doji'] = True
            
            # Hammer pattern
            lower_shadow = current['open'] - current['low'] if current['close'] > current['open'] else current['close'] - current['low']
            upper_shadow = current['high'] - current['close'] if current['close'] > current['open'] else current['high'] - current['open']
            
            if candle_range > 0 and lower_shadow / candle_range > 0.6 and upper_shadow / candle_range < 0.1:
                patterns['hammer'] = True
            
            # Shooting star
            if candle_range > 0 and upper_shadow / candle_range > 0.6 and lower_shadow / candle_range < 0.1:
                patterns['shooting_star'] = True
            
            # Engulfing patterns
            current_body = abs(current['close'] - current['open'])
            previous_body = abs(previous['close'] - previous['open'])
            
            if (current['close'] > current['open'] and previous['close'] < previous['open'] and
                current['open'] < previous['close'] and current['close'] > previous['open']):
                patterns['bullish_engulfing'] = True
            
            if (current['close'] < current['open'] and previous['close'] > previous['open'] and
                current['open'] > previous['close'] and current['close'] < previous['open']):
                patterns['bearish_engulfing'] = True
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error identifying patterns: {e}")
            return {}
    
    def _calculate_volatility(self, data: pd.DataFrame) -> Dict[str, float]:
        """Calculate volatility metrics"""
        try:
            if len(data) < 20:
                return {}
            
            # Calculate returns
            returns = data['close'].pct_change().dropna()
            
            # Different volatility measures
            volatility = {
                'daily_volatility': float(returns.std()),
                'annualized_volatility': float(returns.std() * np.sqrt(252)),
                'avg_true_range': float(self._calculate_atr(data)),
                'volatility_percentile': float(np.percentile(returns.abs().tail(50), 80))
            }
            
            return volatility
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return {}
    
    def _analyze_trend(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Analyze price trend"""
        try:
            if len(data) < 20:
                return {}
            
            # Short-term trend (5 days)
            short_term = data['close'].tail(5)
            short_slope = (short_term.iloc[-1] - short_term.iloc[0]) / len(short_term)
            
            # Medium-term trend (20 days)
            medium_term = data['close'].tail(20)
            medium_slope = (medium_term.iloc[-1] - medium_term.iloc[0]) / len(medium_term)
            
            # Determine trend direction
            def classify_trend(slope):
                if slope > 0.01:
                    return 'STRONG_UP'
                elif slope > 0.005:
                    return 'UP'
                elif slope > -0.005:
                    return 'SIDEWAYS'
                elif slope > -0.01:
                    return 'DOWN'
                else:
                    return 'STRONG_DOWN'
            
            return {
                'short_term_trend': classify_trend(short_slope),
                'medium_term_trend': classify_trend(medium_slope),
                'short_term_slope': float(short_slope),
                'medium_term_slope': float(medium_slope)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return {}
    
    def _calculate_bollinger_bands(self, data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands"""
        sma = data['close'].rolling(window=period).mean()
        std = data['close'].rolling(window=period).std()
        
        return {
            'upper': sma + (std * std_dev),
            'middle': sma,
            'lower': sma - (std * std_dev)
        }
    
    def _calculate_atr(self, data: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        try:
            high_low = data['high'] - data['low']
            high_close = np.abs(data['high'] - data['close'].shift())
            low_close = np.abs(data['low'] - data['close'].shift())
            
            true_range = np.maximum(high_low, np.maximum(high_close, low_close))
            atr = true_range.rolling(window=period).mean()
            
            return atr.iloc[-1] if not atr.empty else 0.0
            
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return 0.0
