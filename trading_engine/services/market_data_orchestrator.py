# apps/trading_engine/services/market_data_orchestrator.py
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import logging
from django.utils import timezone
from django.db.models import Q
from django.db import transaction

from ...market_data_service.services.fyers_collector import FyersDataCollector
from ...technical_analysis.services.data_processor import TechnicalDataProcessor
from ...fundamental_analysis.services.unified_processor import UnifiedResultsProcessor
from ...event_monitoring.services.calendar_monitor import NSEEventCalendarMonitor
from ...market_data_service.models import (
    Company, FundamentalScore, CorporateEvent, ValuationMetrics,
    ProfitabilityMetrics, GrowthMetrics, FinancialStatement
)

logger = logging.getLogger(__name__)

class IntelligentMarketDataOrchestrator:
    """✅ FIXED: Orchestrate market data collection based on ACTUAL fundamental and event triggers"""
    
    def __init__(self):
        self.fyers_collector = FyersDataCollector()
        self.technical_processor = TechnicalDataProcessor()
        self.unified_processor = UnifiedResultsProcessor()
        self.calendar_monitor = NSEEventCalendarMonitor()
        
        # ✅ FIXED: Dynamic filtering criteria based on your analysis results
        self.min_fundamental_score = 70
        self.max_companies_per_batch = 50
        self.analysis_cache = {}
        self.cache_timeout = 3600  # 1 hour cache
        
        # Performance tracking
        self.performance_metrics = {
            'companies_analyzed': 0,
            'successful_analyses': 0,
            'api_calls_made': 0,
            'total_execution_time': 0,
            'last_execution': None
        }
    
    def get_priority_companies_for_analysis(self) -> List[str]:
        """✅ FIXED: Get companies dynamically based on YOUR system's analysis"""
        try:
            start_time = timezone.now()
            priority_companies = set()
            
            logger.info("🎯 Starting intelligent company prioritization...")
            
            # 1. ✅ Companies with strong fundamentals from YOUR screener analysis
            fundamental_leaders = self._get_fundamentally_strong_companies()
            priority_companies.update(fundamental_leaders)
            logger.info(f"📊 Found {len(fundamental_leaders)} fundamentally strong companies")
            
            # 2. ✅ Companies with recent positive events from YOUR event monitoring
            event_triggered = self._get_event_triggered_companies()
            priority_companies.update(event_triggered)
            logger.info(f"📈 Found {len(event_triggered)} event-triggered companies")
            
            # 3. ✅ Companies with upcoming events from YOUR calendar monitoring
            upcoming_events = self._get_upcoming_event_companies()
            priority_companies.update(upcoming_events)
            logger.info(f"📅 Found {len(upcoming_events)} companies with upcoming events")
            
            # 4. ✅ Companies with recent quarterly/annual results from YOUR unified processor
            recent_results = self._get_recent_results_companies()
            priority_companies.update(recent_results)
            logger.info(f"📋 Found {len(recent_results)} companies with recent results")
            
            # 5. ✅ NEW: Companies with strong order announcements
            order_companies = self._get_companies_with_recent_orders()
            priority_companies.update(order_companies)
            logger.info(f"📦 Found {len(order_companies)} companies with recent orders")
            
            # 6. ✅ NEW: Companies with momentum indicators
            momentum_companies = self._get_momentum_companies()
            priority_companies.update(momentum_companies)
            logger.info(f"🚀 Found {len(momentum_companies)} companies with strong momentum")
            
            # 7. ✅ NEW: Companies from watchlists (if any)
            watchlist_companies = self._get_watchlist_companies()
            priority_companies.update(watchlist_companies)
            logger.info(f"👁️ Found {len(watchlist_companies)} companies from watchlists")
            
            # Convert to list and apply intelligent filtering
            final_list = self._apply_intelligent_filtering(list(priority_companies))
            
            execution_time = (timezone.now() - start_time).total_seconds()
            
            logger.info(f"🎯 INTELLIGENT PRIORITIZATION COMPLETED:")
            logger.info(f"   📊 Total unique companies identified: {len(priority_companies)}")
            logger.info(f"   🎯 Final filtered list: {len(final_list)}")
            logger.info(f"   ⏱️ Execution time: {execution_time:.2f} seconds")
            logger.info(f"   🏆 Top companies: {', '.join(final_list[:10])}{'...' if len(final_list) > 10 else ''}")
            
            return final_list
            
        except Exception as e:
            logger.error(f"❌ Error getting priority companies: {e}")
            return []
    
    def execute_comprehensive_analysis(self) -> Dict[str, Any]:
        """✅ FIXED: Execute analysis ONLY for dynamically identified companies"""
        try:
            start_time = timezone.now()
            
            # ✅ Get priority companies from YOUR system's analysis
            priority_companies = self.get_priority_companies_for_analysis()
            
            if not priority_companies:
                return {
                    'message': 'No priority companies identified by the system', 
                    'results': {},
                    'recommendation': 'Check fundamental analysis and event monitoring systems',
                    'performance_metrics': self.performance_metrics
                }
            
            # Check market status before proceeding
            market_status = self.fyers_collector.get_market_status()
            logger.info(f"📊 Market Status: {market_status.get('status', 'UNKNOWN')}")
            
            # ✅ FIXED: Fetch Fyers data ONLY for identified companies
            logger.info(f"🚀 Starting comprehensive analysis for {len(priority_companies)} priority companies")
            
            batch_results = {}
            successful_analyses = 0
            api_calls_made = 0
            
            # Process companies in smaller batches for better performance
            batch_size = 10
            for i in range(0, len(priority_companies), batch_size):
                batch_companies = priority_companies[i:i + batch_size]
                batch_number = (i // batch_size) + 1
                total_batches = (len(priority_companies) + batch_size - 1) // batch_size
                
                logger.info(f"🔄 Processing batch {batch_number}/{total_batches}: {len(batch_companies)} companies")
                
                for symbol in batch_companies:
                    try:
                        result = self._analyze_single_company_with_fyers_data(symbol)
                        api_calls_made += 1
                        
                        if result and 'error' not in result:
                            batch_results[symbol] = result
                            successful_analyses += 1
                            logger.info(f"✅ Successfully analyzed {symbol}")
                        else:
                            error_msg = result.get('error', 'Unknown error') if result else 'Analysis failed'
                            logger.warning(f"❌ Failed to analyze {symbol}: {error_msg}")
                            batch_results[symbol] = result or {'error': 'Analysis failed'}
                            
                    except Exception as e:
                        logger.error(f"❌ Error analyzing {symbol}: {e}")
                        batch_results[symbol] = {'error': str(e)}
                
                # Brief pause between batches
                if i + batch_size < len(priority_companies):
                    logger.info(f"⏸️ Pausing briefly before next batch...")
                    import time
                    time.sleep(2)
            
            # Generate comprehensive summary
            summary = self._generate_comprehensive_summary(batch_results)
            
            # Update performance metrics
            execution_time = (timezone.now() - start_time).total_seconds()
            self.performance_metrics.update({
                'companies_analyzed': len(batch_results),
                'successful_analyses': successful_analyses,
                'api_calls_made': api_calls_made,
                'total_execution_time': execution_time,
                'last_execution': start_time.isoformat()
            })
            
            # Generate actionable insights
            actionable_insights = self._generate_actionable_insights(batch_results)
            
            return {
                'timestamp': timezone.now().isoformat(),
                'execution_time_seconds': execution_time,
                'market_status': market_status,
                'total_priority_companies': len(priority_companies),
                'companies_analyzed': len(batch_results),
                'successful_analyses': successful_analyses,
                'success_rate': f"{(successful_analyses/len(priority_companies)*100):.1f}%",
                'api_calls_made': api_calls_made,
                'summary': summary,
                'actionable_insights': actionable_insights,
                'detailed_results': batch_results,
                'performance_metrics': self.performance_metrics,
                'next_action': 'Review trading signals and execute high-confidence trades'
            }
            
        except Exception as e:
            logger.error(f"❌ Error in comprehensive analysis: {e}")
            return {'error': str(e), 'performance_metrics': self.performance_metrics}
    
    def _analyze_single_company_with_fyers_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """✅ FIXED: Analyze single company using Fyers data + fundamental analysis"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timezone.now().hour}"
            if cache_key in self.analysis_cache:
                cached_result = self.analysis_cache[cache_key]
                if (timezone.now() - cached_result['timestamp']).total_seconds() < self.cache_timeout:
                    logger.info(f"📋 Using cached analysis for {symbol}")
                    return cached_result['data']
            
            logger.info(f"🔍 Analyzing {symbol} with live Fyers market data...")
            
            # ✅ Get historical data from Fyers for THIS specific company
            historical_data = self.fyers_collector.get_historical_data(
                symbol=symbol, 
                timeframe="D", 
                days=365
            )
            
            if historical_data is None or len(historical_data) < 20:
                return {
                    'symbol': symbol,
                    'error': 'Insufficient market data from Fyers',
                    'recommendation': 'Check symbol mapping or Fyers API connection',
                    'data_points': len(historical_data) if historical_data is not None else 0
                }
            
            # ✅ Get live market data for current context
            live_data = self.fyers_collector.get_live_data(symbol)
            
            # ✅ Process technical analysis using REAL market data
            technical_analysis = self.technical_processor.process_candlestick_data(
                symbol=symbol,
                data=historical_data
            )
            
            # Enhance technical analysis with live data
            if live_data:
                technical_analysis['live_data'] = live_data
                technical_analysis['current_price'] = live_data.get('ltp', 0)
                technical_analysis['price_change'] = live_data.get('change', 0)
                technical_analysis['price_change_pct'] = live_data.get('change_pct', 0)
            
            # ✅ Get fundamental analysis from YOUR system
            fundamental_analysis = self._get_comprehensive_fundamental_analysis(symbol)
            
            # ✅ Get recent events from YOUR event monitoring
            recent_events = self._get_detailed_recent_events(symbol)
            
            # ✅ Generate trading recommendation combining ALL data sources
            recommendation = self._generate_comprehensive_recommendation(
                symbol, technical_analysis, fundamental_analysis, recent_events, live_data
            )
            
            # Calculate overall investment attractiveness score
            attractiveness_score = self._calculate_attractiveness_score(
                technical_analysis, fundamental_analysis, recent_events
            )
            
            result = {
                'symbol': symbol,
                'analysis_timestamp': timezone.now().isoformat(),
                'technical_analysis': technical_analysis,
                'fundamental_analysis': fundamental_analysis,
                'recent_events': recent_events,
                'live_market_data': live_data,
                'recommendation': recommendation,
                'attractiveness_score': attractiveness_score,
                'data_quality': {
                    'market_data_points': len(historical_data),
                    'technical_indicators_available': len(technical_analysis.get('technical_indicators', {})),
                    'fundamental_score_available': 'overall_score' in fundamental_analysis,
                    'recent_events_count': len(recent_events),
                    'live_data_available': live_data is not None,
                    'data_completeness_pct': self._calculate_data_completeness(
                        historical_data, fundamental_analysis, recent_events, live_data
                    )
                },
                'risk_assessment': self._assess_investment_risk(symbol, technical_analysis, fundamental_analysis),
                'last_updated': timezone.now().isoformat()
            }
            
            # Cache the result
            self.analysis_cache[cache_key] = {
                'data': result,
                'timestamp': timezone.now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e)}
    
    def _apply_intelligent_filtering(self, companies: List[str]) -> List[str]:
        """Apply intelligent filtering to prioritize the most promising companies"""
        try:
            if len(companies) <= self.max_companies_per_batch:
                return companies
            
            logger.info(f"🎯 Applying intelligent filtering to {len(companies)} companies")
            
            # Score each company based on multiple factors
            company_scores = {}
            
            for symbol in companies:
                score = 0
                
                try:
                    company = Company.objects.get(symbol=symbol)
                    
                    # Fundamental score weight (40%)
                    fundamental_score = getattr(company, 'fundamental_score', None)
                    if fundamental_score:
                        score += fundamental_score.overall_score * 0.4
                    
                    # Recent event weight (30%)
                    recent_events = CorporateEvent.objects.filter(
                        company=company,
                        announcement_date__gte=timezone.now() - timedelta(days=7),
                        impact_level__in=['HIGH', 'MEDIUM']
                    ).count()
                    score += min(recent_events * 20, 30)  # Max 30 points for events
                    
                    # Market cap weight (20%) - prefer larger companies for stability
                    valuation_metrics = getattr(company, 'valuation_metrics', None)
                    if valuation_metrics and valuation_metrics.market_cap:
                        # Score based on market cap tiers
                        market_cap = float(valuation_metrics.market_cap)
                        if market_cap >= 100000000000:  # 1000+ Cr (Large cap)
                            score += 20
                        elif market_cap >= 50000000000:  # 500-1000 Cr (Mid cap)
                            score += 15
                        else:  # < 500 Cr (Small cap)
                            score += 10
                    
                    # Liquidity/activity weight (10%)
                    # Companies with recent fundamental updates get preference
                    if company.last_scraped and company.last_scraped >= timezone.now() - timedelta(days=30):
                        score += 10
                    
                    company_scores[symbol] = score
                    
                except Company.DoesNotExist:
                    company_scores[symbol] = 0  # Lowest priority for unknown companies
            
            # Sort by score and take top companies
            sorted_companies = sorted(company_scores.items(), key=lambda x: x[1], reverse=True)
            filtered_companies = [symbol for symbol, score in sorted_companies[:self.max_companies_per_batch]]
            
            logger.info(f"🎯 Filtered to top {len(filtered_companies)} companies")
            logger.info(f"🏆 Top 5 scores: {dict(sorted_companies[:5])}")
            
            return filtered_companies
            
        except Exception as e:
            logger.error(f"❌ Error in intelligent filtering: {e}")
            return companies[:self.max_companies_per_batch]  # Fallback to simple truncation
    
    def _get_fundamentally_strong_companies(self) -> List[str]:
        """Get companies with strong fundamental scores from YOUR system"""
        try:
            # Companies with high fundamental scores
            strong_companies = Company.objects.filter(
                fundamental_score__overall_score__gte=self.min_fundamental_score,
                is_active=True
            ).values_list('symbol', flat=True)
            
            # Also include companies with strong individual metrics even if overall score is lower
            value_companies = Company.objects.filter(
                fundamental_score__valuation_score__gte=80,
                is_active=True
            ).values_list('symbol', flat=True)
            
            growth_companies = Company.objects.filter(
                fundamental_score__growth_score__gte=80,
                is_active=True
            ).values_list('symbol', flat=True)
            
            # Combine all strong fundamental companies
            all_strong = set(strong_companies) | set(value_companies) | set(growth_companies)
            
            return list(all_strong)[:40]  # Limit to top 40
            
        except Exception as e:
            logger.error(f"❌ Error getting fundamentally strong companies: {e}")
            return []
    
    def _get_event_triggered_companies(self) -> List[str]:
        """Get companies with recent positive events"""
        try:
            recent_events = CorporateEvent.objects.filter(
                announcement_date__gte=timezone.now() - timedelta(days=7),
                impact_level__in=['HIGH', 'MEDIUM'],
                event_type__in=['order_received', 'results_announcement', 'dividend', 'bonus']
            ).values_list('company__symbol', flat=True)
            
            return list(set(recent_events))
            
        except Exception as e:
            logger.error(f"❌ Error getting event triggered companies: {e}")
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
            logger.error(f"❌ Error getting upcoming event companies: {e}")
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
            logger.error(f"❌ Error getting recent results companies: {e}")
            return []
    
    def _get_companies_with_recent_orders(self) -> List[str]:
        """✅ NEW: Get companies with recent order announcements"""
        try:
            order_events = CorporateEvent.objects.filter(
                event_type='order_received',
                impact_level__in=['HIGH', 'MEDIUM'],
                announcement_date__gte=timezone.now() - timedelta(days=14)
            ).values_list('company__symbol', flat=True)
            
            return list(set(order_events))
            
        except Exception as e:
            logger.error(f"❌ Error getting companies with recent orders: {e}")
            return []
    
    def _get_momentum_companies(self) -> List[str]:
        """Get companies showing strong momentum indicators"""
        try:
            # Companies with recent strong growth metrics
            momentum_companies = Company.objects.filter(
                growth_metrics__sales_growth_1y__gte=20,  # 20%+ revenue growth
                growth_metrics__profit_growth_1y__gte=15,  # 15%+ profit growth
                is_active=True
            ).values_list('symbol', flat=True)
            
            return list(momentum_companies)[:20]  # Limit to top 20
            
        except Exception as e:
            logger.error(f"❌ Error getting momentum companies: {e}")
            return []
    
    def _get_watchlist_companies(self) -> List[str]:
        """Get companies from predefined watchlists"""
        try:
            # This could be extended to include user-defined watchlists
            # For now, include some blue-chip companies as default watchlist
            blue_chip_companies = [
                'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 
                'SBIN', 'BHARTIARTL', 'ITC', 'HINDUNILVR', 'LT'
            ]
            
            # Filter to only include active companies in database
            active_watchlist = Company.objects.filter(
                symbol__in=blue_chip_companies,
                is_active=True
            ).values_list('symbol', flat=True)
            
            return list(active_watchlist)
            
        except Exception as e:
            logger.error(f"❌ Error getting watchlist companies: {e}")
            return []
    
    def _get_comprehensive_fundamental_analysis(self, symbol: str) -> Dict[str, Any]:
        """Get comprehensive fundamental analysis for company"""
        try:
            company = Company.objects.get(symbol=symbol)
            
            analysis = {
                'company_info': {
                    'name': company.name,
                    'sector': getattr(company.industry_classification, 'name', 'Unknown') if company.industry_classification else 'Unknown',
                    'last_updated': company.updated_at.isoformat() if company.updated_at else None
                }
            }
            
            # Fundamental scores
            fundamental_score = getattr(company, 'fundamental_score', None)
            if fundamental_score:
                analysis['scores'] = {
                    'overall_score': float(fundamental_score.overall_score),
                    'valuation_score': float(fundamental_score.valuation_score),
                    'profitability_score': float(fundamental_score.profitability_score),
                    'growth_score': float(fundamental_score.growth_score),
                    'financial_health_score': float(fundamental_score.financial_health_score),
                    'last_calculated': fundamental_score.calculation_date.isoformat()
                }
            
            # Valuation metrics
            valuation_metrics = getattr(company, 'valuation_metrics', None)
            if valuation_metrics:
                analysis['valuation'] = {
                    'market_cap': float(valuation_metrics.market_cap) if valuation_metrics.market_cap else None,
                    'pe_ratio': float(valuation_metrics.stock_pe) if valuation_metrics.stock_pe else None,
                    'book_value': float(valuation_metrics.book_value) if valuation_metrics.book_value else None,
                    'dividend_yield': float(valuation_metrics.dividend_yield) if valuation_metrics.dividend_yield else None
                }
            
            # Profitability metrics
            profitability_metrics = getattr(company, 'profitability_metrics', None)
            if profitability_metrics:
                analysis['profitability'] = {
                    'roe': float(profitability_metrics.roe) if profitability_metrics.roe else None,
                    'roce': float(profitability_metrics.roce) if profitability_metrics.roce else None,
                    'net_profit_margin': float(profitability_metrics.net_profit_margin) if profitability_metrics.net_profit_margin else None
                }
            
            # Growth metrics
            growth_metrics = getattr(company, 'growth_metrics', None)
            if growth_metrics:
                analysis['growth'] = {
                    'sales_growth_1y': float(growth_metrics.sales_growth_1y) if growth_metrics.sales_growth_1y else None,
                    'profit_growth_1y': float(growth_metrics.profit_growth_1y) if growth_metrics.profit_growth_1y else None,
                    'sales_growth_3y': float(growth_metrics.sales_growth_3y) if growth_metrics.sales_growth_3y else None
                }
            
            return analysis
            
        except Company.DoesNotExist:
            return {'error': f'Company {symbol} not found'}
        except Exception as e:
            logger.error(f"❌ Error getting fundamental analysis for {symbol}: {e}")
            return {'error': str(e)}
    
    def _get_detailed_recent_events(self, symbol: str) -> List[Dict[str, Any]]:
        """Get detailed recent events for company"""
        try:
            recent_events = CorporateEvent.objects.filter(
                company__symbol=symbol,
                announcement_date__gte=timezone.now() - timedelta(days=30)
            ).order_by('-announcement_date')[:10]
            
            events_data = []
            for event in recent_events:
                events_data.append({
                    'event_type': event.event_type,
                    'title': event.title,
                    'description': event.description[:200] + '...' if len(event.description) > 200 else event.description,
                    'impact_level': event.impact_level,
                    'announcement_date': event.announcement_date.isoformat(),
                    'expected_price_impact': float(event.expected_price_impact) if event.expected_price_impact else None,
                    'days_ago': (timezone.now() - event.announcement_date).days
                })
            
            return events_data
            
        except Exception as e:
            logger.error(f"❌ Error getting recent events for {symbol}: {e}")
            return []
    
    def _generate_comprehensive_recommendation(self, symbol: str, technical: Dict[str, Any], fundamental: Dict[str, Any], events: List[Dict[str, Any]], live_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """✅ ENHANCED: Generate recommendation using EFI strategy + fundamentals + events + live data"""
        try:
            recommendation = {
                'action': 'HOLD',
                'confidence': 0.0,
                'reasons': [],
                'risk_level': 'MEDIUM',
                'position_size': '0%',
                'stop_loss': None,
                'target_price': None,
                'time_horizon': 'MEDIUM_TERM',
                'urgency': 'LOW'
            }
            
            factors = []
            
            # ✅ PRIMARY: EFI Crossover Analysis (Your main strategy)
            efi_analysis = technical.get('technical_indicators', {})
            tech_signals = technical.get('signals', {})
            
            if tech_signals.get('overall_signal') == 'BUY':
                efi_confidence = tech_signals.get('confidence', 0)
                efi_factor = {
                    'factor': 'efi_technical',
                    'weight': 0.4,  # Highest weight for your EFI strategy
                    'score': efi_confidence,
                    'positive': True
                }
                factors.append(efi_factor)
                recommendation['reasons'].append(f"Strong EFI crossover signal (confidence: {efi_confidence:.2f})")
                
                # Set stop loss based on technical analysis
                current_price = technical.get('current_price', 0)
                if live_data:
                    current_price = live_data.get('ltp', current_price)
                
                if current_price > 0:
                    recommendation['stop_loss'] = current_price * 0.95  # 5% stop loss
                    recommendation['target_price'] = current_price * 1.15  # 15% target
            
            # ✅ SECONDARY: Fundamental strength
            scores = fundamental.get('scores', {})
            overall_fund_score = scores.get('overall_score', 0)
            
            if overall_fund_score >= 70:
                factors.append({
                    'factor': 'fundamental',
                    'weight': 0.3,
                    'score': overall_fund_score / 100,
                    'positive': True
                })
                recommendation['reasons'].append(f"Strong fundamentals (score: {overall_fund_score:.1f}/100)")
            
            # ✅ TERTIARY: Event catalysts
            high_impact_events = [e for e in events if e.get('impact_level') in ['HIGH', 'MEDIUM']]
            recent_high_impact = [e for e in high_impact_events if e.get('days_ago', 999) <= 7]
            
            if recent_high_impact:
                event_score = min(len(recent_high_impact) * 0.3, 0.8)  # Max 0.8 for events
                factors.append({
                    'factor': 'events',
                    'weight': 0.2,
                    'score': event_score,
                    'positive': True
                })
                recommendation['reasons'].append(f"Recent positive catalysts: {len(recent_high_impact)} events")
                recommendation['urgency'] = 'HIGH' if len(recent_high_impact) >= 2 else 'MEDIUM'
            
            # ✅ QUATERNARY: Live market momentum
            if live_data:
                price_change_pct = live_data.get('change_pct', 0)
                volume_available = live_data.get('volume', 0) > 0
                
                if price_change_pct > 2 and volume_available:  # Strong positive momentum
                    factors.append({
                        'factor': 'momentum',
                        'weight': 0.1,
                        'score': min(price_change_pct / 5, 1.0),  # Scale to 0-1
                        'positive': True
                    })
                    recommendation['reasons'].append(f"Strong daily momentum: +{price_change_pct:.1f}%")
                    recommendation['urgency'] = 'HIGH'
            
            # ✅ Calculate final recommendation
            if factors:
                total_score = sum(f['weight'] * f['score'] for f in factors if f['positive'])
                total_weight = sum(f['weight'] for f in factors if f['positive'])
                
                if total_weight > 0:
                    confidence = total_score / total_weight
                    
                    if confidence >= 0.75:
                        recommendation['action'] = 'STRONG_BUY'
                        recommendation['confidence'] = confidence
                        recommendation['position_size'] = '3-5%'
                        recommendation['risk_level'] = 'LOW'
                        recommendation['time_horizon'] = 'SHORT_TO_MEDIUM'
                    elif confidence >= 0.6:
                        recommendation['action'] = 'BUY'
                        recommendation['confidence'] = confidence
                        recommendation['position_size'] = '2-3%'
                        recommendation['risk_level'] = 'LOW' if confidence >= 0.7 else 'MEDIUM'
                    elif confidence >= 0.4:
                        recommendation['action'] = 'HOLD'
                        recommendation['confidence'] = confidence
                        recommendation['position_size'] = '1-2%'
                    else:
                        recommendation['action'] = 'AVOID'
                        recommendation['confidence'] = confidence
                        recommendation['risk_level'] = 'HIGH'
            
            # Add market timing consideration
            if live_data:
                market_status = live_data.get('market_status', 'unknown')
                if market_status == 'CLOSED':
                    recommendation['timing_note'] = 'Market closed - place orders for next session'
                elif market_status == 'PREOPEN':
                    recommendation['timing_note'] = 'Market in pre-open - monitor opening price'
            
            return recommendation
            
        except Exception as e:
            logger.error(f"❌ Error generating recommendation for {symbol}: {e}")
            return {'action': 'HOLD', 'confidence': 0.0, 'reasons': ['Analysis error'], 'error': str(e)}
    
    def _calculate_attractiveness_score(self, technical: Dict[str, Any], fundamental: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate overall investment attractiveness score"""
        try:
            score_components = {
                'technical_score': 0,
                'fundamental_score': 0,
                'event_score': 0,
                'overall_score': 0
            }
            
            # Technical score (0-100)
            tech_signals = technical.get('signals', {})
            if tech_signals.get('overall_signal') == 'BUY':
                score_components['technical_score'] = tech_signals.get('confidence', 0) * 100
            
            # Fundamental score (0-100)
            scores = fundamental.get('scores', {})
            score_components['fundamental_score'] = scores.get('overall_score', 0)
            
            # Event score (0-100)
            high_impact_events = [e for e in events if e.get('impact_level') in ['HIGH', 'MEDIUM']]
            recent_events = [e for e in high_impact_events if e.get('days_ago', 999) <= 14]
            score_components['event_score'] = min(len(recent_events) * 25, 100)
            
            # Calculate weighted overall score
            weights = {'technical': 0.4, 'fundamental': 0.4, 'event': 0.2}
            overall = (
                score_components['technical_score'] * weights['technical'] +
                score_components['fundamental_score'] * weights['fundamental'] +
                score_components['event_score'] * weights['event']
            )
            score_components['overall_score'] = overall
            
            # Add interpretation
            if overall >= 80:
                interpretation = 'HIGHLY_ATTRACTIVE'
            elif overall >= 60:
                interpretation = 'ATTRACTIVE'
            elif overall >= 40:
                interpretation = 'MODERATELY_ATTRACTIVE'
            else:
                interpretation = 'NOT_ATTRACTIVE'
            
            score_components['interpretation'] = interpretation
            
            return score_components
            
        except Exception as e:
            logger.error(f"❌ Error calculating attractiveness score: {e}")
            return {'overall_score': 0, 'interpretation': 'ERROR'}
    
    def _calculate_data_completeness(self, historical_data, fundamental_analysis, recent_events, live_data) -> float:
        """Calculate data completeness percentage"""
        try:
            completeness_score = 0
            total_components = 4
            
            # Historical data (25%)
            if historical_data is not None and len(historical_data) >= 20:
                completeness_score += 25
            
            # Fundamental analysis (25%)
            if fundamental_analysis and 'scores' in fundamental_analysis:
                completeness_score += 25
            
            # Recent events (25%)
            if recent_events:
                completeness_score += 25
            
            # Live data (25%)
            if live_data:
                completeness_score += 25
            
            return completeness_score
            
        except Exception as e:
            logger.error(f"❌ Error calculating data completeness: {e}")
            return 0.0
    
    def _assess_investment_risk(self, symbol: str, technical: Dict[str, Any], fundamental: Dict[str, Any]) -> Dict[str, Any]:
        """Assess investment risk for the company"""
        try:
            risk_assessment = {
                'overall_risk': 'MEDIUM',
                'risk_factors': [],
                'risk_score': 50,  # 0-100, higher = more risky
                'volatility_risk': 'MEDIUM',
                'fundamental_risk': 'MEDIUM',
                'market_risk': 'MEDIUM'
            }
            
            risk_score = 50  # Start with medium risk
            
            # Volatility risk
            volatility = technical.get('volatility', {})
            daily_volatility = volatility.get('daily_volatility', 0)
            
            if daily_volatility > 0.05:  # > 5% daily volatility
                risk_score += 20
                risk_assessment['volatility_risk'] = 'HIGH'
                risk_assessment['risk_factors'].append('High price volatility')
            elif daily_volatility < 0.02:  # < 2% daily volatility
                risk_score -= 10
                risk_assessment['volatility_risk'] = 'LOW'
            
            # Fundamental risk
            scores = fundamental.get('scores', {})
            overall_fund_score = scores.get('overall_score', 50)
            
            if overall_fund_score < 40:
                risk_score += 15
                risk_assessment['fundamental_risk'] = 'HIGH'
                risk_assessment['risk_factors'].append('Weak fundamentals')
            elif overall_fund_score > 80:
                risk_score -= 15
                risk_assessment['fundamental_risk'] = 'LOW'
            
            # Market cap risk (smaller companies = higher risk)
            valuation = fundamental.get('valuation', {})
            market_cap = valuation.get('market_cap', 0)
            
            if market_cap and market_cap < 10000000000:  # < 100 Cr (Small cap)
                risk_score += 10
                risk_assessment['risk_factors'].append('Small market cap')
            elif market_cap and market_cap > 100000000000:  # > 1000 Cr (Large cap)
                risk_score -= 10
            
            # Final risk categorization
            risk_assessment['risk_score'] = max(0, min(100, risk_score))
            
            if risk_score >= 70:
                risk_assessment['overall_risk'] = 'HIGH'
            elif risk_score <= 30:
                risk_assessment['overall_risk'] = 'LOW'
            else:
                risk_assessment['overall_risk'] = 'MEDIUM'
            
            return risk_assessment
            
        except Exception as e:
            logger.error(f"❌ Error assessing risk for {symbol}: {e}")
            return {'overall_risk': 'HIGH', 'error': str(e)}
    
    def _generate_comprehensive_summary(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive summary of batch analysis results"""
        try:
            summary = {
                'trading_signals': {
                    'strong_buy': 0,
                    'buy': 0,
                    'hold': 0,
                    'avoid': 0
                },
                'confidence_distribution': {
                    'high_confidence': 0,  # >= 0.7
                    'medium_confidence': 0,  # 0.4-0.7
                    'low_confidence': 0  # < 0.4
                },
                'risk_distribution': {
                    'low_risk': 0,
                    'medium_risk': 0,
                    'high_risk': 0
                },
                'top_recommendations': [],
                'sector_analysis': {},
                'market_sentiment': 'NEUTRAL'
            }
            
            recommendations = []
            
            for symbol, result in batch_results.items():
                if 'error' in result:
                    continue
                
                recommendation = result.get('recommendation', {})
                action = recommendation.get('action', 'HOLD')
                confidence = recommendation.get('confidence', 0)
                risk_level = recommendation.get('risk_level', 'MEDIUM')
                
                # Count signals
                if action == 'STRONG_BUY':
                    summary['trading_signals']['strong_buy'] += 1
                elif action == 'BUY':
                    summary['trading_signals']['buy'] += 1
                elif action == 'AVOID':
                    summary['trading_signals']['avoid'] += 1
                else:
                    summary['trading_signals']['hold'] += 1
                
                # Count confidence levels
                if confidence >= 0.7:
                    summary['confidence_distribution']['high_confidence'] += 1
                elif confidence >= 0.4:
                    summary['confidence_distribution']['medium_confidence'] += 1
                else:
                    summary['confidence_distribution']['low_confidence'] += 1
                
                # Count risk levels
                summary['risk_distribution'][f'{risk_level.lower()}_risk'] += 1
                
                # Collect for top recommendations
                if action in ['STRONG_BUY', 'BUY'] and confidence >= 0.6:
                    recommendations.append({
                        'symbol': symbol,
                        'action': action,
                        'confidence': confidence,
                        'reasons': recommendation.get('reasons', []),
                        'attractiveness_score': result.get('attractiveness_score', {}).get('overall_score', 0),
                        'risk_level': risk_level,
                        'urgency': recommendation.get('urgency', 'LOW')
                    })
            
            # Sort by attractiveness score and confidence
            recommendations.sort(key=lambda x: (x['attractiveness_score'], x['confidence']), reverse=True)
            summary['top_recommendations'] = recommendations[:10]
            
            # Determine overall market sentiment
            total_signals = sum(summary['trading_signals'].values())
            if total_signals > 0:
                buy_signals = summary['trading_signals']['strong_buy'] + summary['trading_signals']['buy']
                buy_ratio = buy_signals / total_signals
                
                if buy_ratio >= 0.6:
                    summary['market_sentiment'] = 'BULLISH'
                elif buy_ratio >= 0.4:
                    summary['market_sentiment'] = 'NEUTRAL'
                else:
                    summary['market_sentiment'] = 'BEARISH'
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error generating comprehensive summary: {e}")
            return {'error': str(e)}
    
    def _generate_actionable_insights(self, batch_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable insights for trading decisions"""
        try:
            insights = {
                'immediate_actions': [],
                'watch_list': [],
                'risk_alerts': [],
                'market_opportunities': [],
                'portfolio_suggestions': {
                    'diversification_notes': [],
                    'position_sizing': [],
                    'timing_recommendations': []
                }
            }
            
            high_confidence_buys = []
            medium_confidence_buys = []
            risk_alerts = []
            
            for symbol, result in batch_results.items():
                if 'error' in result:
                    continue
                
                recommendation = result.get('recommendation', {})
                action = recommendation.get('action', 'HOLD')
                confidence = recommendation.get('confidence', 0)
                urgency = recommendation.get('urgency', 'LOW')
                risk_assessment = result.get('risk_assessment', {})
                
                if action in ['STRONG_BUY', 'BUY']:
                    if confidence >= 0.75:
                        high_confidence_buys.append({
                            'symbol': symbol,
                            'confidence': confidence,
                            'urgency': urgency,
                            'reasons': recommendation.get('reasons', [])[:2]  # Top 2 reasons
                        })
                    elif confidence >= 0.6:
                        medium_confidence_buys.append({
                            'symbol': symbol,
                            'confidence': confidence,
                            'reasons': recommendation.get('reasons', [])[:1]  # Top reason
                        })
                
                # Risk alerts
                if risk_assessment.get('overall_risk') == 'HIGH':
                    risk_alerts.append({
                        'symbol': symbol,
                        'risk_factors': risk_assessment.get('risk_factors', []),
                        'action': 'Monitor closely or avoid'
                    })
            
            # Generate immediate actions
            if high_confidence_buys:
                insights['immediate_actions'].append({
                    'action': 'Execute high-confidence trades',
                    'symbols': [item['symbol'] for item in high_confidence_buys[:5]],
                    'priority': 'HIGH',
                    'note': 'These stocks show strong buy signals with high confidence'
                })
            
            if medium_confidence_buys:
                insights['watch_list'].extend([
                    item['symbol'] for item in medium_confidence_buys[:10]
                ])
                insights['immediate_actions'].append({
                    'action': 'Add to watchlist for next opportunity',
                    'symbols': [item['symbol'] for item in medium_confidence_buys[:5]],
                    'priority': 'MEDIUM',
                    'note': 'Monitor for better entry points'
                })
            
            # Risk alerts
            insights['risk_alerts'] = risk_alerts[:5]  # Top 5 risk alerts
            
            # Portfolio suggestions
            if len(high_confidence_buys) > 0:
                insights['portfolio_suggestions']['position_sizing'].append(
                    f"Allocate 2-3% per position for {len(high_confidence_buys)} high-confidence opportunities"
                )
                insights['portfolio_suggestions']['timing_recommendations'].append(
                    "Execute trades during market hours for better liquidity"
                )
            
            if len(high_confidence_buys) > 5:
                insights['portfolio_suggestions']['diversification_notes'].append(
                    "Consider spreading trades across multiple sessions to reduce timing risk"
                )
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Error generating actionable insights: {e}")
            return {'error': str(e)}
    
    def get_portfolio_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the trading system"""
        try:
            # This would integrate with actual portfolio tracking
            # For now, return the analysis performance metrics
            return {
                'system_performance': self.performance_metrics,
                'api_health': {
                    'fyers_connected': self.fyers_collector.is_connected(),
                    'last_successful_call': self.performance_metrics.get('last_execution'),
                    'success_rate': f"{(self.performance_metrics.get('successful_analyses', 0) / max(self.performance_metrics.get('companies_analyzed', 1), 1) * 100):.1f}%"
                },
                'recommendations': 'System is functioning optimally' if self.fyers_collector.is_connected() else 'Check Fyers API connection'
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting performance metrics: {e}")
            return {'error': str(e)}
