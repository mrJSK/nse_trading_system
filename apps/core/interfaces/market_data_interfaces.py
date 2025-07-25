# core/interfaces/market_data_interfaces.py
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd

class MarketDataProviderInterface(ABC):
    """Interface for market data providers"""
    
    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data"""
        pass
    
    @abstractmethod
    def get_live_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live market data"""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check connection status"""
        pass

class TechnicalDataProcessorInterface(ABC):
    """Interface for processing technical data"""
    
    @abstractmethod
    def process_candlestick_data(self, symbol: str, data: pd.DataFrame) -> Dict[str, Any]:
        """Process candlestick data for technical analysis"""
        pass
    
    @abstractmethod
    def calculate_indicators(self, data: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        pass
