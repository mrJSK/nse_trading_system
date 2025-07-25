# apps/market_data_service/services/fyers_collector.py
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd
import logging
from fyers_api import fyersModel
from fyers_api.Websocket import ws

from core.interfaces.market_data_interfaces import MarketDataProviderInterface
from django.conf import settings

logger = logging.getLogger(__name__)

class FyersDataCollector(MarketDataProviderInterface):
    """Single responsibility: Collect market data from Fyers API"""
    
    def __init__(self):
        self.client_id = settings.FYERS_APP_ID
        self.secret_key = settings.FYERS_SECRET_KEY
        self.redirect_uri = settings.FYERS_REDIRECT_URI
        self.token_file = "data/fyers_token.json"
        
        self.fyers = None
        self.access_token = None
        
        # NSE symbol mapping
        self.symbol_mapping = {
            'RELIANCE': 'NSE:RELIANCE-EQ',
            'TCS': 'NSE:TCS-EQ',
            'INFY': 'NSE:INFY-EQ',
            'HDFCBANK': 'NSE:HDFCBANK-EQ',
            'ICICIBANK': 'NSE:ICICIBANK-EQ',
            'SBIN': 'NSE:SBIN-EQ',
            'BHARTIARTL': 'NSE:BHARTIARTL-EQ',
            'ITC': 'NSE:ITC-EQ',
            'HINDUNILVR': 'NSE:HINDUNILVR-EQ',
            'LT': 'NSE:LT-EQ'
        }
        
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Fyers API connection"""
        try:
            # Load existing token or generate new one
            if os.path.exists(self.token_file):
                self._load_token()
            else:
                self._generate_new_token()
            
            if self.access_token:
                self.fyers = fyersModel.FyersModel(
                    client_id=self.client_id,
                    token=self.access_token,
                    log_path=os.getcwd()
                )
                logger.info("Fyers API connection initialized successfully")
            else:
                logger.error("Failed to initialize Fyers API connection")
                
        except Exception as e:
            logger.error(f"Error initializing Fyers connection: {e}")
    
    def _load_token(self):
        """Load existing access token"""
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                
                # Check if token is expired
                expires_at = datetime.fromisoformat(token_data.get('expires_at', ''))
                if datetime.now() >= expires_at:
                    logger.info("Token expired, generating new one")
                    self._generate_new_token()
                    
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            self._generate_new_token()
    
    def _generate_new_token(self):
        """Generate new access token"""
        try:
            # This requires manual intervention for OAuth flow
            # In production, you'd implement automated token refresh
            logger.warning("Token generation requires manual OAuth flow")
            logger.info(f"Visit: https://api.fyers.in/api/v2/generate-authcode?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state=sample")
            
            # For now, use stored token if available
            # TODO: Implement automated token refresh
            
        except Exception as e:
            logger.error(f"Error generating token: {e}")
    
    def get_historical_data(self, symbol: str, timeframe: str = "D", days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data from Fyers"""
        try:
            if not self.fyers:
                logger.error("Fyers API not initialized")
                return None
            
            # Convert symbol to Fyers format
            fyers_symbol = self._convert_to_fyers_symbol(symbol)
            if not fyers_symbol:
                logger.warning(f"Symbol mapping not found for {symbol}")
                return None
            
            # Calculate date range
            to_date = datetime.now()
            from_date = to_date - timedelta(days=days)
            
            # Prepare request data
            data = {
                "symbol": fyers_symbol,
                "resolution": timeframe,
                "date_format": "1",
                "range_from": from_date.strftime("%Y-%m-%d"),
                "range_to": to_date.strftime("%Y-%m-%d"),
                "cont_flag": "1"
            }
            
            # Make API call
            response = self.fyers.history(data=data)
            
            if response['s'] == 'ok':
                # Convert to DataFrame
                candles = response['candles']
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                # Ensure proper data types
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                logger.info(f"Successfully fetched {len(df)} candles for {symbol}")
                return df
            else:
                logger.error(f"Fyers API error: {response}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return None
    
    def get_live_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live market data"""
        try:
            if not self.fyers:
                return None
            
            fyers_symbol = self._convert_to_fyers_symbol(symbol)
            if not fyers_symbol:
                return None
            
            data = {"symbols": fyers_symbol}
            response = self.fyers.quotes(data=data)
            
            if response['s'] == 'ok':
                quote_data = response['d'][0]
                return {
                    'symbol': symbol,
                    'ltp': quote_data['v']['lp'],
                    'open': quote_data['v']['o'],
                    'high': quote_data['v']['h'],
                    'low': quote_data['v']['l'],
                    'prev_close': quote_data['v']['prev_close_price'],
                    'volume': quote_data['v']['volume'],
                    'change': quote_data['v']['ch'],
                    'change_pct': quote_data['v']['chp'],
                    'timestamp': datetime.now()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching live data for {symbol}: {e}")
            return None
    
    def get_batch_historical_data(self, symbols: List[str], timeframe: str = "D", days: int = 365) -> Dict[str, pd.DataFrame]:
        """Get historical data for multiple symbols"""
        batch_data = {}
        
        for symbol in symbols:
            try:
                data = self.get_historical_data(symbol, timeframe, days)
                if data is not None:
                    batch_data[symbol] = data
                
                # Add delay to respect API limits
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {e}")
        
        return batch_data
    
    def is_connected(self) -> bool:
        """Check if Fyers API is connected"""
        try:
            if not self.fyers:
                return False
            
            # Test connection with a simple API call
            response = self.fyers.funds()
            return response.get('s') == 'ok'
            
        except Exception as e:
            logger.error(f"Connection check failed: {e}")
            return False
    
    def _convert_to_fyers_symbol(self, symbol: str) -> Optional[str]:
        """Convert symbol to Fyers format"""
        # Check if already in Fyers format
        if ':' in symbol and '-' in symbol:
            return symbol
        
        # Use mapping for known symbols
        if symbol in self.symbol_mapping:
            return self.symbol_mapping[symbol]
        
        # Default NSE equity format
        return f"NSE:{symbol}-EQ"
    
    def update_symbol_mapping(self, new_mappings: Dict[str, str]):
        """Update symbol mapping with new symbols"""
        self.symbol_mapping.update(new_mappings)
