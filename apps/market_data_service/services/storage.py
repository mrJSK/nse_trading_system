# apps/market_data_service/services/storage.py
from typing import Dict, List, Any
from django.db import transaction
from django.utils import timezone
from core.interfaces.scraping_interfaces import DataStorageInterface
from ..models import (
    Company, IndustryClassification, ValuationMetrics, 
    ProfitabilityMetrics, FinancialStatement, GrowthMetrics,
    QualitativeAnalysis, ShareholdingPattern
)
import logging

logger = logging.getLogger(__name__)

class DatabaseStorageService(DataStorageInterface):
    """Single responsibility: Store scraped data in database"""
    
    def store_company_data(self, symbol: str, data: Dict[str, Any]) -> bool:
        """Store complete company data in database"""
        try:
            with transaction.atomic():
                # Store basic company info
                company = self._store_basic_info(symbol, data.get('basic_info', {}))
                
                # Store valuation metrics
                self._store_valuation_metrics(company, data.get('valuation_metrics', {}))
                
                # Store profitability metrics
                self._store_profitability_metrics(company, data.get('profitability_metrics', {}))
                
                # Store growth metrics
                self._store_growth_metrics(company, data.get('growth_metrics', {}))
                
                # Store financial statements
                self._store_financial_statements(company, data.get('financial_statements', {}))
                
                # Store qualitative analysis
                self._store_qualitative_analysis(company, data.get('qualitative_analysis', {}))
                
                # Store shareholding patterns
                self._store_shareholding_patterns(company, data.get('shareholding_patterns', {}))
                
                # Store industry classification
                self._store_industry_classification(company, data.get('industry_classification'))
                
                logger.info(f"Successfully stored data for {symbol}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to store data for {symbol}: {e}")
            return False
    
    def get_companies_to_scrape(self) -> List[str]:
        """Get list of active company symbols"""
        return list(Company.objects.filter(is_active=True).values_list('symbol', flat=True))
    
    def _store_basic_info(self, symbol: str, basic_info: Dict[str, Any]) -> Company:
        """Store or update basic company information"""
        defaults = {
            'name': basic_info.get('name', symbol),
            'about': basic_info.get('about'),
            'website': basic_info.get('website'),
            'bse_code': basic_info.get('bse_code'),
            'nse_code': basic_info.get('nse_code'),
            'updated_at': timezone.now()
        }
        
        company, created = Company.objects.update_or_create(
            symbol=symbol,
            defaults=defaults
        )
        
        return company
    
    def _store_valuation_metrics(self, company: Company, valuation_data: Dict[str, Any]):
        """Store valuation metrics"""
        if not valuation_data:
            return
        
        defaults = {
            'market_cap': valuation_data.get('market_cap'),
            'current_price': valuation_data.get('current_price'),
            'high_52_week': valuation_data.get('high_52_week'),
            'low_52_week': valuation_data.get('low_52_week'),
            'stock_pe': valuation_data.get('stock_pe'),
            'book_value': valuation_data.get('book_value'),
            'dividend_yield': valuation_data.get('dividend_yield'),
            'face_value': valuation_data.get('face_value'),
            'updated_at': timezone.now()
        }
        
        ValuationMetrics.objects.update_or_create(
            company=company,
            defaults=defaults
        )
    
    def _store_profitability_metrics(self, company: Company, profitability_data: Dict[str, Any]):
        """Store profitability metrics"""
        if not profitability_data:
            return
        
        defaults = {
            'roce': profitability_data.get('roce'),
            'roe': profitability_data.get('roe'),
            'updated_at': timezone.now()
        }
        
        ProfitabilityMetrics.objects.update_or_create(
            company=company,
            defaults=defaults
        )
    
    def _store_growth_metrics(self, company: Company, growth_data: Dict[str, Any]):
        """Store growth metrics"""
        if not growth_data:
            return
        
        # Extract sales growth data
        sales_growth = growth_data.get('Compounded Sales Growth', {})
        profit_growth = growth_data.get('Compounded Profit Growth', {})
        
        defaults = {
            'sales_growth_10y': sales_growth.get('10 Years'),
            'sales_growth_5y': sales_growth.get('5 Years'),
            'sales_growth_3y': sales_growth.get('3 Years'),
            'sales_growth_1y': sales_growth.get('TTM'),
            'profit_growth_10y': profit_growth.get('10 Years'),
            'profit_growth_5y': profit_growth.get('5 Years'),
            'profit_growth_3y': profit_growth.get('3 Years'),
            'profit_growth_1y': profit_growth.get('TTM'),
            'updated_at': timezone.now()
        }
        
        GrowthMetrics.objects.update_or_create(
            company=company,
            defaults=defaults
        )
    
    def _store_financial_statements(self, company: Company, statements_data: Dict[str, Any]):
        """Store financial statements data"""
        for statement_type, statement_data in statements_data.items():
            if statement_data:
                FinancialStatement.objects.update_or_create(
                    company=company,
                    statement_type=statement_type,
                    defaults={
                        'data': statement_data,
                        'updated_at': timezone.now()
                    }
                )
    
    def _store_qualitative_analysis(self, company: Company, qualitative_data: Dict[str, Any]):
        """Store qualitative analysis data"""
        if not qualitative_data:
            return
        
        defaults = {
            'pros': qualitative_data.get('pros', []),
            'cons': qualitative_data.get('cons', []),
            'updated_at': timezone.now()
        }
        
        QualitativeAnalysis.objects.update_or_create(
            company=company,
            defaults=defaults
        )
    
    def _store_shareholding_patterns(self, company: Company, shareholding_data: Dict[str, Any]):
        """Store shareholding patterns"""
        for pattern_type, pattern_data in shareholding_data.items():
            if pattern_data:
                ShareholdingPattern.objects.update_or_create(
                    company=company,
                    pattern_type=pattern_type,
                    defaults={
                        'data': pattern_data,
                        'updated_at': timezone.now()
                    }
                )
    
    def _store_industry_classification(self, company: Company, industry_name: str):
        """Store industry classification"""
        if not industry_name:
            return
        
        try:
            industry, created = IndustryClassification.objects.get_or_create(
                name=industry_name
            )
            company.industry_classification = industry
            company.save()
        except Exception as e:
            logger.error(f"Failed to store industry classification: {e}")
