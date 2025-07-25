# apps/fundamental_analysis/services/xbrl_processor.py
import os
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from core.interfaces.scraping_interfaces import ScrapingResult
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class NSEXBRLProcessor:
    """Single responsibility: Process XBRL data from NSE and other sources"""
    
    def __init__(self):
        self.nse_xbrl_base_url = "https://www.nseindia.com/api/corporates-xbrl"
        self.download_dir = "data/xbrl_files"
        
        # Ensure download directory exists
        os.makedirs(self.download_dir, exist_ok=True)
        
        # Standard XBRL tags mapping
        self.xbrl_tag_mapping = {
            # Income Statement
            'RevenueFromOperations': 'revenue',
            'TotalRevenue': 'total_revenue',
            'CostOfGoodsSold': 'cost_of_goods_sold',
            'GrossProfit': 'gross_profit',
            'OperatingProfit': 'operating_profit',
            'ProfitBeforeTax': 'profit_before_tax',
            'ProfitAfterTax': 'net_profit',
            'EarningsPerShare': 'eps',
            
            # Balance Sheet - Assets
            'TotalAssets': 'total_assets',
            'CurrentAssets': 'current_assets',
            'CashAndCashEquivalents': 'cash_and_equivalents',
            'ShareholdersEquity': 'shareholders_equity',
            'TotalLiabilities': 'total_liabilities',
            'CurrentLiabilities': 'current_liabilities',
            'TotalBorrowings': 'total_debt',
        }
    
    def download_xbrl_data(self, symbol: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Download XBRL data for a company"""
        try:
            if year is None:
                year = datetime.now().year
            
            logger.info(f"Attempting to download XBRL data for {symbol} for year {year}")
            
            # For now, return mock data since actual XBRL API endpoints may not be available
            # In production, you would implement actual XBRL downloading logic
            return self._get_mock_xbrl_data(symbol, year)
            
        except Exception as e:
            logger.error(f"Error downloading XBRL data for {symbol}: {e}")
            return None
    
    def parse_xbrl_data(self, xbrl_data: Dict[str, Any]) -> ScrapingResult:
        """Parse XBRL data into structured format"""
        try:
            if not xbrl_data:
                return ScrapingResult(
                    success=False,
                    error="No XBRL data provided",
                    data_source="xbrl"
                )
            
            # Parse different statement types
            parsed_data = {
                'income_statement': self._parse_income_statement(xbrl_data),
                'balance_sheet': self._parse_balance_sheet(xbrl_data),
                'cash_flow': self._parse_cash_flow_statement(xbrl_data),
                'financial_ratios': self._calculate_ratios_from_xbrl(xbrl_data),
                'metadata': self._extract_metadata(xbrl_data)
            }
            
            return ScrapingResult(
                success=True,
                data=parsed_data,
                data_source="xbrl",
                timestamp=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error parsing XBRL data: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                data_source="xbrl"
            )
    
    def _get_mock_xbrl_data(self, symbol: str, year: int) -> Dict[str, Any]:
        """Return mock XBRL data for testing purposes"""
        return {
            'facts': {
                'RevenueFromOperations': [{'value': 100000000, 'period': f'FY{year}'}],
                'ProfitAfterTax': [{'value': 15000000, 'period': f'FY{year}'}],
                'TotalAssets': [{'value': 200000000, 'period': f'FY{year}'}],
                'ShareholdersEquity': [{'value': 120000000, 'period': f'FY{year}'}],
                'CurrentAssets': [{'value': 80000000, 'period': f'FY{year}'}],
                'CurrentLiabilities': [{'value': 40000000, 'period': f'FY{year}'}],
            },
            'filingDate': f'{year}-07-15',
            'fiscalYear': year,
            'currency': 'INR'
        }
    
    def _parse_income_statement(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse income statement from XBRL data"""
        income_statement = {}
        
        try:
            facts = xbrl_data.get('facts', {})
            
            for xbrl_tag, standard_name in self.xbrl_tag_mapping.items():
                if xbrl_tag in facts:
                    fact_data = facts[xbrl_tag]
                    
                    if isinstance(fact_data, list) and fact_data:
                        # Get most recent data
                        income_statement[standard_name] = self._parse_xbrl_value(fact_data[0])
                    else:
                        income_statement[standard_name] = self._parse_xbrl_value(fact_data)
            
            return income_statement
            
        except Exception as e:
            logger.error(f"Error parsing income statement from XBRL: {e}")
            return {}
    
    def _parse_balance_sheet(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance sheet from XBRL data"""
        balance_sheet = {}
        
        try:
            facts = xbrl_data.get('facts', {})
            
            balance_sheet_tags = [
                'TotalAssets', 'CurrentAssets', 'CashAndCashEquivalents',
                'ShareholdersEquity', 'TotalLiabilities', 'CurrentLiabilities', 'TotalBorrowings'
            ]
            
            for tag in balance_sheet_tags:
                if tag in facts:
                    standard_name = self.xbrl_tag_mapping.get(tag, tag.lower())
                    fact_data = facts[tag]
                    
                    if isinstance(fact_data, list) and fact_data:
                        balance_sheet[standard_name] = self._parse_xbrl_value(fact_data[0])
                    else:
                        balance_sheet[standard_name] = self._parse_xbrl_value(fact_data)
            
            return balance_sheet
            
        except Exception as e:
            logger.error(f"Error parsing balance sheet from XBRL: {e}")
            return {}
    
    def _parse_cash_flow_statement(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse cash flow statement from XBRL data"""
        return {}  # Placeholder implementation
    
    def _calculate_ratios_from_xbrl(self, xbrl_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate financial ratios from XBRL data"""
        ratios = {}
        
        try:
            facts = xbrl_data.get('facts', {})
            
            # Calculate current ratio
            if 'CurrentAssets' in facts and 'CurrentLiabilities' in facts:
                current_assets = self._parse_xbrl_value(facts['CurrentAssets'][0] if isinstance(facts['CurrentAssets'], list) else facts['CurrentAssets'])
                current_liabilities = self._parse_xbrl_value(facts['CurrentLiabilities'][0] if isinstance(facts['CurrentLiabilities'], list) else facts['CurrentLiabilities'])
                
                if current_liabilities and current_liabilities > 0:
                    ratios['current_ratio'] = current_assets / current_liabilities
            
            # Calculate debt to equity
            if 'TotalBorrowings' in facts and 'ShareholdersEquity' in facts:
                total_debt = self._parse_xbrl_value(facts['TotalBorrowings'][0] if isinstance(facts['TotalBorrowings'], list) else facts['TotalBorrowings'])
                equity = self._parse_xbrl_value(facts['ShareholdersEquity'][0] if isinstance(facts['ShareholdersEquity'], list) else facts['ShareholdersEquity'])
                
                if equity and equity > 0:
                    ratios['debt_to_equity'] = total_debt / equity
            
            return ratios
            
        except Exception as e:
            logger.error(f"Error calculating ratios from XBRL: {e}")
            return {}
    
    def _extract_metadata(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from XBRL data"""
        metadata = {}
        
        try:
            if 'filingDate' in xbrl_data:
                metadata['filing_date'] = xbrl_data['filingDate']
            
            if 'fiscalYear' in xbrl_data:
                metadata['fiscal_year'] = str(xbrl_data['fiscalYear'])
            
            if 'currency' in xbrl_data:
                metadata['currency'] = xbrl_data['currency']
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting XBRL metadata: {e}")
            return {}
    
    def _parse_xbrl_value(self, fact_data: Any) -> Optional[float]:
        """Parse XBRL fact value"""
        try:
            if isinstance(fact_data, dict):
                value = fact_data.get('value', 0)
            else:
                value = fact_data
            
            if value is None:
                return None
            
            return float(value)
            
        except (ValueError, TypeError):
            return None
