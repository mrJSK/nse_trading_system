# apps/market_data_service/services/symbol_mapper.py
from typing import Dict, List, Set
import logging
from django.db import transaction
from ...market_data_service.models import Company

logger = logging.getLogger(__name__)

class DynamicSymbolMapper:
    """Single responsibility: Dynamically map NSE symbols to Fyers format"""
    
    def __init__(self):
        self.symbol_cache = {}
        self.last_cache_update = None
    
    def get_fyers_symbols_for_companies(self, company_symbols: List[str]) -> Dict[str, str]:
        """Convert company symbols to Fyers format dynamically"""
        try:
            fyers_mapping = {}
            
            for symbol in company_symbols:
                fyers_symbol = self._convert_to_fyers_format(symbol)
                if fyers_symbol:
                    fyers_mapping[symbol] = fyers_symbol
            
            logger.info(f"Mapped {len(fyers_mapping)} symbols for Fyers API")
            return fyers_mapping
            
        except Exception as e:
            logger.error(f"Error mapping symbols: {e}")
            return {}
    
    def _convert_to_fyers_format(self, nse_symbol: str) -> str:
        """Convert NSE symbol to Fyers format"""
        try:
            # Check cache first
            if nse_symbol in self.symbol_cache:
                return self.symbol_cache[nse_symbol]
            
            # Standard NSE equity format for Fyers
            fyers_symbol = f"NSE:{nse_symbol}-EQ"
            
            # Cache the mapping
            self.symbol_cache[nse_symbol] = fyers_symbol
            
            return fyers_symbol
            
        except Exception as e:
            logger.error(f"Error converting symbol {nse_symbol}: {e}")
            return f"NSE:{nse_symbol}-EQ"  # Fallback
    
    def update_symbol_mappings_from_db(self):
        """Update symbol mappings from database companies"""
        try:
            active_companies = Company.objects.filter(is_active=True).values_list('symbol', flat=True)
            
            for symbol in active_companies:
                self._convert_to_fyers_format(symbol)
            
            logger.info(f"Updated symbol mappings for {len(active_companies)} companies")
            
        except Exception as e:
            logger.error(f"Error updating symbol mappings: {e}")
