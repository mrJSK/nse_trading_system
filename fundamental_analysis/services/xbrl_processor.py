# apps/fundamental_analysis/services/xbrl_processor.py
import os
import requests
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import logging
from core.interfaces.scraping_interfaces import XBRLProcessorInterface, ScrapingResult
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class NSEXBRLProcessor(XBRLProcessorInterface):
    """Single responsibility: Process XBRL data from NSE and other sources"""
    
    def __init__(self):
        self.nse_xbrl_base_url = "https://www.nseindia.com/api/corporates-xbrl"
        self.download_dir = "data/xbrl_files"
        self.session = requests.Session()
        
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
            'NonCurrentAssets': 'non_current_assets',
            'CashAndCashEquivalents': 'cash_and_equivalents',
            'Inventories': 'inventories',
            'TradeReceivables': 'trade_receivables',
            'PropertyPlantAndEquipment': 'ppe',
            
            # Balance Sheet - Liabilities
            'TotalEquityAndLiabilities': 'total_equity_liabilities',
            'ShareholdersEquity': 'shareholders_equity',
            'TotalLiabilities': 'total_liabilities',
            'CurrentLiabilities': 'current_liabilities',
            'NonCurrentLiabilities': 'non_current_liabilities',
            'TradePayables': 'trade_payables',
            'TotalBorrowings': 'total_debt',
            
            # Cash Flow
            'CashFlowFromOperatingActivities': 'operating_cash_flow',
            'CashFlowFromInvestingActivities': 'investing_cash_flow',
            'CashFlowFromFinancingActivities': 'financing_cash_flow',
            'NetCashFlow': 'net_cash_flow',
        }
    
    def download_xbrl_data(self, symbol: str, year: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Download XBRL data for a company"""
        try:
            if year is None:
                year = datetime.now().year
            
            # Try multiple approaches to get XBRL data
            xbrl_data = self._download_from_nse(symbol, year)
            
            if not xbrl_data:
                xbrl_data = self._download_from_company_website(symbol, year)
            
            if not xbrl_data:
                logger.warning(f"Could not download XBRL data for {symbol} for year {year}")
                return None
            
            return xbrl_data
            
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
    
    def _download_from_nse(self, symbol: str, year: int) -> Optional[Dict[str, Any]]:
        """Download XBRL from NSE APIs"""
        try:
            # NSE XBRL API endpoint (this is a placeholder - actual endpoint may vary)
            url = f"{self.nse_xbrl_base_url}/{symbol}/{year}"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"NSE XBRL API returned status {response.status_code} for {symbol}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading from NSE XBRL API: {e}")
            return None
    
    def _download_from_company_website(self, symbol: str, year: int) -> Optional[Dict[str, Any]]:
        """Download XBRL from company's investor relations page"""
        try:
            # This would implement company-specific XBRL download logic
            # For now, return None as this requires company-specific implementations
            logger.info(f"Company website XBRL download not implemented for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Error downloading from company website: {e}")
            return None
    
    def _parse_income_statement(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse income statement from XBRL data"""
        income_statement = {}
        
        try:
            # Extract income statement facts
            facts = xbrl_data.get('facts', {})
            
            for xbrl_tag, standard_name in self.xbrl_tag_mapping.items():
                if xbrl_tag in facts:
                    fact_data = facts[xbrl_tag]
                    
                    # Get most recent annual data
                    if isinstance(fact_data, list):
                        # Sort by period and get latest
                        sorted_facts = sorted(fact_data, key=lambda x: x.get('period', ''), reverse=True)
                        if sorted_facts:
                            income_statement[standard_name] = self._parse_xbrl_value(sorted_facts[0])
                    else:
                        income_statement[standard_name] = self._parse_xbrl_value(fact_data)
            
            # Calculate derived metrics
            if 'revenue' in income_statement and 'net_profit' in income_statement:
                try:
                    revenue = Decimal(str(income_statement['revenue']))
                    net_profit = Decimal(str(income_statement['net_profit']))
                    if revenue > 0:
                        income_statement['net_profit_margin'] = float((net_profit / revenue) * 100)
                except:
                    pass
            
            return income_statement
            
        except Exception as e:
            logger.error(f"Error parsing income statement from XBRL: {e}")
            return {}
    
    def _parse_balance_sheet(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse balance sheet from XBRL data"""
        balance_sheet = {}
        
        try:
            facts = xbrl_data.get('facts', {})
            
            # Extract balance sheet items
            balance_sheet_tags = [
                'TotalAssets', 'CurrentAssets', 'NonCurrentAssets', 'CashAndCashEquivalents',
                'Inventories', 'TradeReceivables', 'PropertyPlantAndEquipment',
                'ShareholdersEquity', 'TotalLiabilities', 'CurrentLiabilities', 
                'NonCurrentLiabilities', 'TradePayables', 'TotalBorrowings'
            ]
            
            for tag in balance_sheet_tags:
                if tag in facts:
                    standard_name = self.xbrl_tag_mapping.get(tag, tag.lower())
                    fact_data = facts[tag]
                    
                    if isinstance(fact_data, list):
                        sorted_facts = sorted(fact_data, key=lambda x: x.get('period', ''), reverse=True)
                        if sorted_facts:
                            balance_sheet[standard_name] = self._parse_xbrl_value(sorted_facts[0])
                    else:
                        balance_sheet[standard_name] = self._parse_xbrl_value(fact_data)
            
            return balance_sheet
            
        except Exception as e:
            logger.error(f"Error parsing balance sheet from XBRL: {e}")
            return {}
    
    def _parse_cash_flow_statement(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse cash flow statement from XBRL data"""
        cash_flow = {}
        
        try:
            facts = xbrl_data.get('facts', {})
            
            cash_flow_tags = [
                'CashFlowFromOperatingActivities', 'CashFlowFromInvestingActivities',
                'CashFlowFromFinancingActivities', 'NetCashFlow'
            ]
            
            for tag in cash_flow_tags:
                if tag in facts:
                    standard_name = self.xbrl_tag_mapping.get(tag, tag.lower())
                    fact_data = facts[tag]
                    
                    if isinstance(fact_data, list):
                        sorted_facts = sorted(fact_data, key=lambda x: x.get('period', ''), reverse=True)
                        if sorted_facts:
                            cash_flow[standard_name] = self._parse_xbrl_value(sorted_facts[0])
                    else:
                        cash_flow[standard_name] = self._parse_xbrl_value(fact_data)
            
            return cash_flow
            
        except Exception as e:
            logger.error(f"Error parsing cash flow from XBRL: {e}")
            return {}
    
    def _calculate_ratios_from_xbrl(self, xbrl_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate financial ratios from XBRL data"""
        ratios = {}
        
        try:
            # Get parsed statements
            income_statement = self._parse_income_statement(xbrl_data)
            balance_sheet = self._parse_balance_sheet(xbrl_data)
            
            # Calculate ratios
            if 'net_profit' in income_statement and 'shareholders_equity' in balance_sheet:
                try:
                    net_profit = Decimal(str(income_statement['net_profit']))
                    equity = Decimal(str(balance_sheet['shareholders_equity']))
                    if equity > 0:
                        ratios['roe'] = float((net_profit / equity) * 100)
                except:
                    pass
            
            if 'operating_profit' in income_statement and 'total_assets' in balance_sheet:
                try:
                    operating_profit = Decimal(str(income_statement['operating_profit']))
                    total_assets = Decimal(str(balance_sheet['total_assets']))
                    if total_assets > 0:
                        ratios['roa'] = float((operating_profit / total_assets) * 100)
                except:
                    pass
            
            if 'current_assets' in balance_sheet and 'current_liabilities' in balance_sheet:
                try:
                    current_assets = Decimal(str(balance_sheet['current_assets']))
                    current_liabilities = Decimal(str(balance_sheet['current_liabilities']))
                    if current_liabilities > 0:
                        ratios['current_ratio'] = float(current_assets / current_liabilities)
                except:
                    pass
            
            if 'total_debt' in balance_sheet and 'shareholders_equity' in balance_sheet:
                try:
                    total_debt = Decimal(str(balance_sheet['total_debt']))
                    equity = Decimal(str(balance_sheet['shareholders_equity']))
                    if equity > 0:
                        ratios['debt_to_equity'] = float(total_debt / equity)
                except:
                    pass
            
            return ratios
            
        except Exception as e:
            logger.error(f"Error calculating ratios from XBRL: {e}")
            return {}
    
    def _extract_metadata(self, xbrl_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract metadata from XBRL data"""
        metadata = {}
        
        try:
            # Extract filing information
            if 'filingDate' in xbrl_data:
                metadata['filing_date'] = xbrl_data['filingDate']
            
            if 'reportDate' in xbrl_data:
                metadata['report_date'] = xbrl_data['reportDate']
            
            if 'fiscalYear' in xbrl_data:
                metadata['fiscal_year'] = xbrl_data['fiscalYear']
            
            if 'fiscalPeriod' in xbrl_data:
                metadata['fiscal_period'] = xbrl_data['fiscalPeriod']
            
            if 'currency' in xbrl_data:
                metadata['currency'] = xbrl_data['currency']
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting XBRL metadata: {e}")
            return {}
    
    def _parse_xbrl_value(self, fact_data: Dict[str, Any]) -> Optional[float]:
        """Parse XBRL fact value"""
        try:
            if isinstance(fact_data, dict):
                value = fact_data.get('value', fact_data.get('val', 0))
            else:
                value = fact_data
            
            if value is None:
                return None
            
            # Convert to float
            if isinstance(value, str):
                # Remove commas and convert
                value = value.replace(',', '')
                return float(value)
            
            return float(value)
            
        except (ValueError, TypeError):
            return None
