# apps/fundamental_analysis/services/analyzers.py
from typing import Dict, Any, Optional
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)

class ValueAnalyzer:
    """Analyze valuation metrics for value investing"""
    
    def __init__(self):
        self.pe_thresholds = {
            'excellent': 15,
            'good': 20,
            'fair': 25,
            'expensive': 35
        }
        
        self.pb_thresholds = {
            'excellent': 1.5,
            'good': 2.5,
            'fair': 3.5,
            'expensive': 5.0
        }
    
    def analyze_fundamentals(self, fundamental_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive value analysis"""
        try:
            analysis = {
                'pe_analysis': self._analyze_pe_ratio(fundamental_data.get('pe_ratio')),
                'pb_analysis': self._analyze_pb_ratio(fundamental_data.get('pb_ratio')),
                'dividend_analysis': self._analyze_dividend_yield(fundamental_data.get('dividend_yield')),
                'overall_score': 0
            }
            
            # Calculate overall value score
            scores = []
            if analysis['pe_analysis']['score']:
                scores.append(analysis['pe_analysis']['score'])
            if analysis['pb_analysis']['score']:
                scores.append(analysis['pb_analysis']['score'])
            if analysis['dividend_analysis']['score']:
                scores.append(analysis['dividend_analysis']['score'])
            
            if scores:
                analysis['overall_score'] = sum(scores) / len(scores)
            
            # Add recommendation
            if analysis['overall_score'] >= 80:
                analysis['recommendation'] = 'STRONG_BUY'
            elif analysis['overall_score'] >= 60:
                analysis['recommendation'] = 'BUY'
            elif analysis['overall_score'] >= 40:
                analysis['recommendation'] = 'HOLD'
            else:
                analysis['recommendation'] = 'AVOID'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in value analysis: {e}")
            return {'overall_score': 0}
    
    def _analyze_pe_ratio(self, pe_ratio: Optional[float]) -> Dict[str, Any]:
        """Analyze P/E ratio"""
        if not pe_ratio or pe_ratio <= 0:
            return {'score': None, 'rating': 'Unknown', 'comment': 'P/E ratio not available'}
        
        if pe_ratio <= self.pe_thresholds['excellent']:
            return {'score': 90, 'rating': 'Excellent', 'comment': f'Low P/E of {pe_ratio:.1f} indicates undervaluation'}
        elif pe_ratio <= self.pe_thresholds['good']:
            return {'score': 75, 'rating': 'Good', 'comment': f'Reasonable P/E of {pe_ratio:.1f}'}
        elif pe_ratio <= self.pe_thresholds['fair']:
            return {'score': 50, 'rating': 'Fair', 'comment': f'Moderate P/E of {pe_ratio:.1f}'}
        elif pe_ratio <= self.pe_thresholds['expensive']:
            return {'score': 25, 'rating': 'Expensive', 'comment': f'High P/E of {pe_ratio:.1f} suggests overvaluation'}
        else:
            return {'score': 10, 'rating': 'Very Expensive', 'comment': f'Very high P/E of {pe_ratio:.1f}'}
    
    def _analyze_pb_ratio(self, pb_ratio: Optional[float]) -> Dict[str, Any]:
        """Analyze P/B ratio"""
        if not pb_ratio or pb_ratio <= 0:
            return {'score': None, 'rating': 'Unknown', 'comment': 'P/B ratio not available'}
        
        if pb_ratio <= self.pb_thresholds['excellent']:
            return {'score': 85, 'rating': 'Excellent', 'comment': f'Low P/B of {pb_ratio:.1f} indicates good value'}
        elif pb_ratio <= self.pb_thresholds['good']:
            return {'score': 70, 'rating': 'Good', 'comment': f'Reasonable P/B of {pb_ratio:.1f}'}
        elif pb_ratio <= self.pb_thresholds['fair']:
            return {'score': 45, 'rating': 'Fair', 'comment': f'Moderate P/B of {pb_ratio:.1f}'}
        elif pb_ratio <= self.pb_thresholds['expensive']:
            return {'score': 20, 'rating': 'Expensive', 'comment': f'High P/B of {pb_ratio:.1f}'}
        else:
            return {'score': 5, 'rating': 'Very Expensive', 'comment': f'Very high P/B of {pb_ratio:.1f}'}
    
    def _analyze_dividend_yield(self, dividend_yield: Optional[float]) -> Dict[str, Any]:
        """Analyze dividend yield"""
        if not dividend_yield or dividend_yield < 0:
            return {'score': 20, 'rating': 'No Dividend', 'comment': 'Company does not pay dividends'}
        
        if dividend_yield >= 4:
            return {'score': 85, 'rating': 'Excellent', 'comment': f'High dividend yield of {dividend_yield:.1f}%'}
        elif dividend_yield >= 2:
            return {'score': 65, 'rating': 'Good', 'comment': f'Good dividend yield of {dividend_yield:.1f}%'}
        elif dividend_yield >= 1:
            return {'score': 45, 'rating': 'Moderate', 'comment': f'Moderate dividend yield of {dividend_yield:.1f}%'}
        else:
            return {'score': 25, 'rating': 'Low', 'comment': f'Low dividend yield of {dividend_yield:.1f}%'}


class GrowthAnalyzer:
    """Analyze growth metrics for growth investing"""
    
    def __init__(self):
        self.revenue_growth_thresholds = {
            'excellent': 20,
            'good': 15,
            'fair': 10,
            'poor': 5
        }
        
        self.profit_growth_thresholds = {
            'excellent': 25,
            'good': 18,
            'fair': 12,
            'poor': 6
        }
    
    def analyze_fundamentals(self, fundamental_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive growth analysis"""
        try:
            analysis = {
                'revenue_growth_analysis': self._analyze_revenue_growth(fundamental_data.get('revenue_growth')),
                'profit_growth_analysis': self._analyze_profit_growth(fundamental_data.get('profit_growth')),
                'profitability_analysis': self._analyze_profitability(fundamental_data),
                'overall_score': 0
            }
            
            # Calculate overall growth score
            scores = []
            if analysis['revenue_growth_analysis']['score']:
                scores.append(analysis['revenue_growth_analysis']['score'])
            if analysis['profit_growth_analysis']['score']:
                scores.append(analysis['profit_growth_analysis']['score'])
            if analysis['profitability_analysis']['score']:
                scores.append(analysis['profitability_analysis']['score'])
            
            if scores:
                analysis['overall_score'] = sum(scores) / len(scores)
            
            # Add recommendation
            if analysis['overall_score'] >= 80:
                analysis['recommendation'] = 'STRONG_GROWTH'
            elif analysis['overall_score'] >= 60:
                analysis['recommendation'] = 'GOOD_GROWTH'
            elif analysis['overall_score'] >= 40:
                analysis['recommendation'] = 'MODERATE_GROWTH'
            else:
                analysis['recommendation'] = 'POOR_GROWTH'
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in growth analysis: {e}")
            return {'overall_score': 0}
    
    def _analyze_revenue_growth(self, revenue_growth: Optional[float]) -> Dict[str, Any]:
        """Analyze revenue growth"""
        if revenue_growth is None:
            return {'score': None, 'rating': 'Unknown', 'comment': 'Revenue growth data not available'}
        
        if revenue_growth >= self.revenue_growth_thresholds['excellent']:
            return {'score': 90, 'rating': 'Excellent', 'comment': f'Strong revenue growth of {revenue_growth:.1f}%'}
        elif revenue_growth >= self.revenue_growth_thresholds['good']:
            return {'score': 75, 'rating': 'Good', 'comment': f'Good revenue growth of {revenue_growth:.1f}%'}
        elif revenue_growth >= self.revenue_growth_thresholds['fair']:
            return {'score': 50, 'rating': 'Fair', 'comment': f'Moderate revenue growth of {revenue_growth:.1f}%'}
        elif revenue_growth >= self.revenue_growth_thresholds['poor']:
            return {'score': 25, 'rating': 'Poor', 'comment': f'Slow revenue growth of {revenue_growth:.1f}%'}
        elif revenue_growth >= 0:
            return {'score': 15, 'rating': 'Very Poor', 'comment': f'Very slow revenue growth of {revenue_growth:.1f}%'}
        else:
            return {'score': 5, 'rating': 'Declining', 'comment': f'Revenue declining by {abs(revenue_growth):.1f}%'}
    
    def _analyze_profit_growth(self, profit_growth: Optional[float]) -> Dict[str, Any]:
        """Analyze profit growth"""
        if profit_growth is None:
            return {'score': None, 'rating': 'Unknown', 'comment': 'Profit growth data not available'}
        
        if profit_growth >= self.profit_growth_thresholds['excellent']:
            return {'score': 95, 'rating': 'Excellent', 'comment': f'Outstanding profit growth of {profit_growth:.1f}%'}
        elif profit_growth >= self.profit_growth_thresholds['good']:
            return {'score': 80, 'rating': 'Good', 'comment': f'Strong profit growth of {profit_growth:.1f}%'}
        elif profit_growth >= self.profit_growth_thresholds['fair']:
            return {'score': 55, 'rating': 'Fair', 'comment': f'Moderate profit growth of {profit_growth:.1f}%'}
        elif profit_growth >= self.profit_growth_thresholds['poor']:
            return {'score': 30, 'rating': 'Poor', 'comment': f'Slow profit growth of {profit_growth:.1f}%'}
        elif profit_growth >= 0:
            return {'score': 15, 'rating': 'Very Poor', 'comment': f'Very slow profit growth of {profit_growth:.1f}%'}
        else:
            return {'score': 5, 'rating': 'Declining', 'comment': f'Profit declining by {abs(profit_growth):.1f}%'}
    
    def _analyze_profitability(self, fundamental_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze profitability metrics"""
        roe = fundamental_data.get('roe')
        roce = fundamental_data.get('roce')
        margin = fundamental_data.get('net_profit_margin')
        
        scores = []
        comments = []
        
        # ROE analysis
        if roe:
            if roe >= 20:
                scores.append(90)
                comments.append(f'Excellent ROE of {roe:.1f}%')
            elif roe >= 15:
                scores.append(70)
                comments.append(f'Good ROE of {roe:.1f}%')
            elif roe >= 10:
                scores.append(50)
                comments.append(f'Fair ROE of {roe:.1f}%')
            else:
                scores.append(25)
                comments.append(f'Poor ROE of {roe:.1f}%')
        
        # ROCE analysis  
        if roce:
            if roce >= 18:
                scores.append(85)
                comments.append(f'Excellent ROCE of {roce:.1f}%')
            elif roce >= 12:
                scores.append(65)
                comments.append(f'Good ROCE of {roce:.1f}%')
            elif roce >= 8:
                scores.append(45)
                comments.append(f'Fair ROCE of {roce:.1f}%')
            else:
                scores.append(20)
                comments.append(f'Poor ROCE of {roce:.1f}%')
        
        if scores:
            avg_score = sum(scores) / len(scores)
            return {
                'score': avg_score,
                'rating': 'Excellent' if avg_score >= 80 else 'Good' if avg_score >= 60 else 'Fair' if avg_score >= 40 else 'Poor',
                'comment': '; '.join(comments)
            }
        else:
            return {'score': None, 'rating': 'Unknown', 'comment': 'Profitability data not available'}
