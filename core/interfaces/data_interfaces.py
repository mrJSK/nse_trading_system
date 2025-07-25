from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime

class DataCollectorInterface(ABC):
    @abstractmethod
    def collect_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Collect fundamental data for a company"""
        pass
    
    @abstractmethod
    def collect_market_data(self, symbol: str, timeframe: str) -> List[Dict[str, Any]]:
        """Collect OHLCV market data"""
        pass

class AnalyzerInterface(ABC):
    @abstractmethod
    def analyze_fundamentals(self, data: Dict[str, Any]) -> Dict[str, float]:
        """Analyze fundamental data and return scores"""
        pass

class SignalGeneratorInterface(ABC):
    @abstractmethod
    def generate_signals(self, symbol: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate trading signals"""
        pass

class EventMonitorInterface(ABC):
    @abstractmethod
    def monitor_events(self) -> List[Dict[str, Any]]:
        """Monitor NSE events 24x7"""
        pass
