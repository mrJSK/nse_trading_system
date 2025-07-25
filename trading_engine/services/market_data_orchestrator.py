# apps/trading_engine/services/market_data_orchestrator.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from django.utils import timezone
from django.db.models import Q

from ..services.fyers_collector import FyersDataCollector
from ..services.data_processor import TechnicalDataProcessor
from ...fundamental_analysis.services.unified_processor import UnifiedResultsProcessor
from ...event_monitoring.services.calendar_monitor import NSEEventCalendarMonitor
from ...market_data_service.models import Company, FundamentalScore, CorporateEvent

logger = logging.getLogger(__name__)

class IntelligentMarketDataOrchestrator:
    """Orchestrate market data collection based on fundamental and event triggers"""
    
    def __init__(self):
        self.fyers_collector = FyersDataCollector()
        self.technical_processor = TechnicalDataProcessor()
        self.unified_processor = UnifiedResultsProcessor()
        self.calendar_monitor = NSEEventCalendarMonitor()
        
        # Filtering criteria
        self.min_fundamental_score = 70  # Minimum fundamental score
        self.max_companies_per_batch = 50  # API rate limiting
        
    def get_priority_companies_for_analysis(self) -> List[str]:
        """Get companies that need technical analysis based on fundamental/event triggers"""
        try:
            priority_companies = set()
            
            # 1. Companies with strong fundamentals
            fundamental_leaders = self._get_fundamentally_strong_companies()
            priority_companies.update(fundamental_leaders)
            
            # 2. Companies with recent positive events
            event_triggered = self._get_event_triggered_companies()
            priority_companies.update(event_triggered)
            
            # 3. Companies with upcoming events (next 7 days)
            upcoming_events = self._get_upcoming_event_companies()
            priority_companies.update(upcoming_events)
            
            # 4. Companies with recent quarterly/annual results
            recent_results = self._get_recent_results_companies()
            priority_companies.update(recent_results)
            
            # Convert to list and limit
            final_list = list(priority_companies)[:self.max_companies_per_batch]
            
            logger.info(f"Identified {len(final_list)} priority companies for technical analysis")
            logger.info(f"Companies: {', '.join(final_list[:10])}{'...' if len(final_list) > 10 else ''}")
            
            return final_list
            
        except Exception as e:
            logger.error(f"Error getting priority companies: {e}")
            return []
    
    def execute_comprehensive_analysis(self) -> Dict[str, Any]:
        """Execute comprehensive analysis for priority companies"""
        try:
            # Get priority companies
            priority_companies = self.get_priority_companies_for_analysis()
            
            if not priority_companies:
                return {'message': 'No priority companies identified', 'results': {}}
            
            # Batch fetch technical data
            batch_results = {}
            
            for symbol in priority_companies:
                try:
                    result = self._analyze_single_company(symbol)
                    if result:
                        batch_results[symbol] = result
                        
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    batch_results[symbol] = {'error': str(e)}
            
            # Generate summary
            summary = self._generate_analysis_summary(batch_results)
            
            return {
                'timestamp': timezone.now().isoformat(),
                'companies_analyzed': len(batch_results),
                'successful_analyses': len([r for r in batch_results.values() if 'error' not in r]),
                'summary': summary,
                'detailed_results': batch_results
            }
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return {'error': str(e)}
    
    def _analyze_single_company(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Analyze single company with technical data"""
        try:
            # Get historical data from Fyers
            historical_data = self.fyers_collector.get_historical_data(
                symbol=symbol, 
                timeframe="D", 
                days=365
            )
            
            if historical_data is None:
                return {'error': 'Failed to fetch market data'}
            
            # Process technical analysis
            technical_analysis = self.technical_processor.process_candlestick_data(
                symbol=symbol,
                data=historical_data
            )
            
            # Get fundamental analysis
            fundamental_analysis = self._get_fundamental_analysis(symbol)
            
            # Get recent events
            recent_events = self._get_recent_events(symbol)
            
            # Combine all analyses
            combined_analysis = {
                'symbol': symbol,
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'recent_events': recent_events,
                'recommendation': self._generate_recommendation(
                    technical_analysis, fundamental_analysis, recent_events
                ),
                'last_updated': timezone.now().isoformat()
            }
            
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return {'error': str(e)}
    
    def _get_fundamentally_strong_companies(self) -> List[str]:
        """Get companies with strong fundamental scores"""
        try:
            strong_companies = Company.objects.filter(
                fundamental_score__overall_score__gte=self.min_fundamental_score,
                is_active=True
            ).values_list('symbol', flat=True)
            
            return list(strong_companies)[:30]  # Top 30
            
        except Exception as e:
            logger.error(f"Error getting fundamentally strong companies: {e}")
            return []
    
    def _get_event_triggered_companies(self) -> List[str]:
        """Get companies with recent positive events"""
        try:
            recent_events = CorporateEvent.objects.filter(
                announcement_date__gte=timezone.now() - timedelta(days=7),
                impact_level__in=['HIGH', 'MEDIUM'],
                event_type__in=['order_received', 'results_announcement']
            ).values_list('company__symbol', flat=True)
            
            return list(set(recent_events))
            
        except Exception as e:
            logger.error(f"Error getting event triggered companies: {e}")
            return []
    
    def _get_upcoming_event_companies(self) -> List[str]:
        """Get companies with upcoming events"""
        try:
            upcoming_events = self.calendar_monitor.get_upcoming_events(days_ahead=7)
            
            companies = []
            companies.extend(upcoming_events.get('equity_companies', []))
            companies.extend(upcoming_events.get('sme_companies', []))
            
            return list(set(companies))
            
        except Exception as e:
            logger.error(f"Error getting upcoming event companies: {e}")
            return []
    
    def _get_recent_results_companies(self) -> List[str]:
        """Get companies with recent quarterly/annual results"""
        try:
            recent_results = CorporateEvent.objects.filter(
                event_type='results_announcement',
                announcement_date__gte=timezone.now() - timedelta(days=30)
            ).values_list('company__symbol', flat=True)
            
            return list(set(recent_results))
            
        except Exception as e:
            logger.error(f"Error getting recent results companies: {e}")
            return []
    
    def _get_fundamental_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get latest fundamental analysis for company"""
        try:
            company = Company.objects.get(symbol=symbol)
            fundamental_data = company.get_latest_fundamental_data()
            
            fundamental_score = getattr(company, 'fundamental_score', None)
            if fundamental_score:
                return {
                    'overall_score': float(fundamental_score.overall_score),
                    'valuation_score': float(fundamental_score.valuation_score),
                    'profitability_score': float(fundamental_score.profitability_score),
                    'growth_score': float(fundamental_score.growth_score),
                    'last_updated': fundamental_score.calculation_date.isoformat()
                }
            
            return {'error': 'No fundamental analysis available'}
            
        except Company.DoesNotExist:
            return {'error': f'Company {symbol} not found'}
        except Exception as e:
            logger.error(f"Error getting fundamental analysis for {symbol}: {e}")
            return {'error': str(e)}
    
    def _get_recent_events(self, symbol: str) -> List[Dict[str, Any]]:
        """Get recent events for company"""
        try:
            recent_events = CorporateEvent.objects.filter(
                company__symbol=symbol,
                announcement_date__gte=timezone.now() - timedelta(days=30)
            ).order_by('-announcement_date')[:5]
            
            events_data = []
            for event in recent_events:
                events_data.append({
                    'event_type': event.event_type,
                    'title': event.title,
                    'description': event.description,
                    'impact_level': event.impact_level,
                    'announcement_date': event.announcement_date.isoformat()
                })
            
            return events_data
            
        except Exception as e:
            logger.error(f"Error getting recent events for {symbol}: {e}")
            return []
    
    def _generate_recommendation(self, technical: Dict[str, Any], fundamental: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate overall recommendation combining all factors"""
        try:
            recommendation = {
                'action': 'HOLD',
                'confidence': 0.0,
                'reasons': [],
                'risk_level': 'MEDIUM'
            }
            
            factors = []
            
            # Technical factor
            tech_signals = technical.get('signals', {})
            if tech_signals.get('overall_signal') == 'BUY':
                factors.append({
                    'factor': 'technical',
                    'weight': 0.4,
                    'score': tech_signals.get('confidence', 0),
                    'positive': True
                })
                recommendation['reasons'].append(f"Technical analysis: {tech_signals.get('overall_signal')}")
            
            # Fundamental factor
            fund_score = fundamental.get('overall_score', 0)
            if fund_score >= 70:
                factors.append({
                    'factor': 'fundamental',
                    'weight': 0.4,
                    'score': fund_score / 100,
                    'positive': True
                })
                recommendation['reasons'].append(f"Strong fundamentals: {fund_score:.1f}/100")
            
            # Event factor
            recent_positive_events = [e for e in events if e.get('impact_level') in ['HIGH', 'MEDIUM']]
            if recent_positive_events:
                factors.append({
                    'factor': 'events',
                    'weight': 0.2,
                    'score': 0.8,
                    'positive': True
                })
                recommendation['reasons'].append(f"Recent positive events: {len(recent_positive_events)}")
            
            # Calculate overall score
            if factors:
                total_score = sum(f['weight'] * f['score'] for f in factors if f['positive'])
                total_weight = sum(f['weight'] for f in factors if f['positive'])
                
                if total_weight > 0:
                    confidence = total_score / total_weight
                    
                    if confidence >= 0.7:
                        recommendation['action'] = 'BUY'
                        recommendation['confidence'] = confidence
                        recommendation['risk_level'] = 'LOW' if confidence >= 0.8 else 'MEDIUM'
                    elif confidence >= 0.3:
                        recommendation['action'] = 'HOLD'
                        recommendation['confidence'] = confidence
                    else:
                        recommendation['action'] = 'SELL'
                        recommendation['confidence'] = 1 - confidence
                        recommendation['risk_level'] = 'HIGH'
            
            return recommendation
            
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reasons': ['Analysis error']}
    
    def _generate_analysis_summary(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate summary of batch analysis results"""
        try:
            summary = {
                'buy_signals': 0,
                'hold_signals': 0,
                'sell_signals': 0,
                'high_confidence_signals': 0,
                'top_recommendations': []
            }
            
            recommendations = []
            
            for symbol, result in batch_results.items():
                if 'error' in result:
                    continue
                
                recommendation = result.get('recommendation', {})
                action = recommendation.get('action', 'HOLD')
                confidence = recommendation.get('confidence', 0)
                
                if action == 'BUY':
                    summary['buy_signals'] += 1
                elif action == 'SELL':
                    summary['sell_signals'] += 1
                else:
                    summary['hold_signals'] += 1
                
                if confidence >= 0.7:
                    summary['high_confidence_signals'] += 1
                
                recommendations.append({
                    'symbol': symbol,
                    'action': action,
                    'confidence': confidence,
                    'reasons': recommendation.get('reasons', [])
                })
            
            # Sort by confidence and get top recommendations
            recommendations.sort(key=lambda x: x['confidence'], reverse=True)
            summary['top_recommendations'] = recommendations[:10]
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return {}

# Celery task for automated execution
from celery import shared_task

@shared_task
def execute_intelligent_market_analysis():
    """Automated task to run intelligent market analysis"""
    try:
        orchestrator = IntelligentMarketDataOrchestrator()
        results = orchestrator.execute_comprehensive_analysis()
        
        logger.info(f"Market analysis completed: {results.get('companies_analyzed', 0)} companies analyzed")
        return results
        
    except Exception as e:
        logger.error(f"Error in automated market analysis: {e}")
        return {'error': str(e)}
