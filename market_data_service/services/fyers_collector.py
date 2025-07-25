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
from .symbol_mapper import DynamicSymbolMapper
from django.conf import settings

logger = logging.getLogger(__name__)

class FyersDataCollector(MarketDataProviderInterface):
    """Single responsibility: Collect market data from Fyers API"""
    
    def __init__(self):
        self.client_id = settings.FYERS_APP_ID
        self.secret_key = settings.FYERS_SECRET_KEY
        self.redirect_uri = settings.FYERS_REDIRECT_URI
        self.token_file = "data/fyers_token.json"
        self.session_file = "data/fyers_session.json"
        
        self.fyers = None
        self.access_token = None
        self.websocket = None
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests
        
        # ✅ FIXED: Use dynamic symbol mapper instead of hardcoded mapping
        self.symbol_mapper = DynamicSymbolMapper()
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize Fyers API connection"""
        try:
            # Load existing token or generate new one
            if os.path.exists(self.token_file):
                self._load_token()
            else:
                logger.warning("No token file found. Please generate access token first.")
                self._generate_new_token()
            
            if self.access_token:
                self.fyers = fyersModel.FyersModel(
                    client_id=self.client_id,
                    token=self.access_token,
                    log_path=os.getcwd()
                )
                
                # Test connection
                if self._test_connection():
                    logger.info("✅ Fyers API connection initialized successfully")
                else:
                    logger.error("❌ Failed to establish Fyers API connection")
                    self._handle_connection_failure()
            else:
                logger.error("❌ Failed to initialize Fyers API connection - no access token")
                
        except Exception as e:
            logger.error(f"Error initializing Fyers connection: {e}")
            self.fyers = None
    
    def _load_token(self):
        """Load existing access token"""
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
                self.access_token = token_data.get('access_token')
                
                # Check if token is expired
                expires_at_str = token_data.get('expires_at', '')
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                    if datetime.now() >= expires_at:
                        logger.info("Token expired, generating new one")
                        self._generate_new_token()
                        return
                
                logger.info("✅ Successfully loaded existing token")
                    
        except Exception as e:
            logger.error(f"Error loading token: {e}")
            self._generate_new_token()
    
    def _generate_new_token(self):
        """Generate new access token"""
        try:
            # This requires manual intervention for OAuth flow
            # In production, you'd implement automated token refresh
            auth_url = f"https://api.fyers.in/api/v2/generate-authcode?client_id={self.client_id}&redirect_uri={self.redirect_uri}&response_type=code&state=sample"
            
            logger.warning("🔐 Token generation requires manual OAuth flow")
            logger.info(f"📋 Please visit this URL to authorize: {auth_url}")
            logger.info("After authorization, update the token file manually or implement automated refresh")
            
            # TODO: Implement automated token refresh using Selenium
            # For now, the system will work with existing token or manual intervention
            
        except Exception as e:
            logger.error(f"Error generating token: {e}")
    
    def _test_connection(self) -> bool:
        """Test Fyers API connection"""
        try:
            if not self.fyers:
                return False
            
            # Test with a simple API call
            response = self.fyers.funds()
            
            if response and isinstance(response, dict):
                if response.get('s') == 'ok':
                    logger.info("✅ Fyers API connection test successful")
                    return True
                else:
                    logger.warning(f"⚠️ Fyers API returned: {response}")
                    return False
            else:
                logger.error(f"❌ Unexpected response from Fyers API: {response}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Connection test failed: {e}")
            return False
    
    def _handle_connection_failure(self):
        """Handle connection failure scenarios"""
        try:
            logger.warning("🔄 Attempting to recover from connection failure...")
            
            # Try to regenerate token
            self._generate_new_token()
            
            # Log the failure for monitoring
            failure_log = {
                'timestamp': datetime.now().isoformat(),
                'error': 'Connection failure',
                'action': 'Token regeneration attempted'
            }
            
            with open('data/connection_failures.log', 'a') as f:
                f.write(json.dumps(failure_log) + '\n')
                
        except Exception as e:
            logger.error(f"Error handling connection failure: {e}")
    
    def get_historical_data(self, symbol: str, timeframe: str = "D", days: int = 365) -> Optional[pd.DataFrame]:
        """Get historical OHLCV data from Fyers"""
        try:
            if not self.fyers:
                logger.error("❌ Fyers API not initialized")
                return None
            
            # Rate limiting
            self._enforce_rate_limit()
            
            # ✅ FIXED: Use dynamic symbol conversion
            fyers_symbol = self.symbol_mapper._convert_to_fyers_format(symbol)
            logger.info(f"📊 Fetching historical data for {symbol} (Fyers: {fyers_symbol})")
            
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
            
            if response and response.get('s') == 'ok':
                # Convert to DataFrame
                candles = response.get('candles', [])
                
                if not candles:
                    logger.warning(f"⚠️ No candle data received for {symbol}")
                    return None
                
                df = pd.DataFrame(candles, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert timestamp to datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df.set_index('timestamp', inplace=True)
                
                # Ensure proper data types
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                # Remove any rows with NaN values
                df = df.dropna()
                
                if len(df) > 0:
                    logger.info(f"✅ Successfully fetched {len(df)} candles for {symbol}")
                    return df
                else:
                    logger.warning(f"⚠️ No valid data after cleaning for {symbol}")
                    return None
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Fyers API error for {symbol}: {error_msg}")
                
                # Handle specific error cases
                if response and response.get('code') == 429:
                    logger.warning("⏳ Rate limit exceeded, waiting before retry...")
                    time.sleep(5)
                    
                return None
                
        except Exception as e:
            logger.error(f"❌ Error fetching historical data for {symbol}: {e}")
            return None
    
    def get_live_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get live market data"""
        try:
            if not self.fyers:
                logger.error("❌ Fyers API not initialized")
                return None
            
            # Rate limiting
            self._enforce_rate_limit()
            
            fyers_symbol = self.symbol_mapper._convert_to_fyers_format(symbol)
            
            data = {"symbols": fyers_symbol}
            response = self.fyers.quotes(data=data)
            
            if response and response.get('s') == 'ok':
                quotes = response.get('d', [])
                if not quotes:
                    logger.warning(f"⚠️ No quote data for {symbol}")
                    return None
                
                quote_data = quotes[0]
                quote_values = quote_data.get('v', {})
                
                return {
                    'symbol': symbol,
                    'ltp': quote_values.get('lp', 0),
                    'open': quote_values.get('o', 0),
                    'high': quote_values.get('h', 0),
                    'low': quote_values.get('l', 0),
                    'prev_close': quote_values.get('prev_close_price', 0),
                    'volume': quote_values.get('volume', 0),
                    'change': quote_values.get('ch', 0),
                    'change_pct': quote_values.get('chp', 0),
                    'timestamp': datetime.now(),
                    'market_status': quote_values.get('market_status', 'unknown')
                }
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Error fetching live data for {symbol}: {error_msg}")
                return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching live data for {symbol}: {e}")
            return None
    
    def get_batch_historical_data_for_priority_companies(self, priority_companies: List[str], timeframe: str = "D", days: int = 365) -> Dict[str, pd.DataFrame]:
        """✅ FIXED: Get historical data specifically for identified priority companies"""
        batch_data = {}
        failed_companies = []
        
        logger.info(f"🚀 Starting batch fetch for {len(priority_companies)} priority companies")
        
        for i, symbol in enumerate(priority_companies, 1):
            try:
                logger.info(f"📊 [{i}/{len(priority_companies)}] Fetching data for {symbol}")
                
                data = self.get_historical_data(symbol, timeframe, days)
                if data is not None and len(data) > 0:
                    batch_data[symbol] = data
                    logger.info(f"✅ [{i}/{len(priority_companies)}] Successfully fetched {len(data)} records for {symbol}")
                else:
                    failed_companies.append(symbol)
                    logger.warning(f"❌ [{i}/{len(priority_companies)}] Failed to fetch data for {symbol}")
                
                # Add delay to respect API limits
                time.sleep(self.min_request_interval)
                
                # Progress logging every 10 companies
                if i % 10 == 0:
                    success_rate = len(batch_data) / i * 100
                    logger.info(f"📈 Progress: {i}/{len(priority_companies)} companies processed, {success_rate:.1f}% success rate")
                
            except Exception as e:
                failed_companies.append(symbol)
                logger.error(f"❌ [{i}/{len(priority_companies)}] Error fetching data for {symbol}: {e}")
        
        # Final summary
        success_count = len(batch_data)
        total_count = len(priority_companies)
        success_rate = success_count / total_count * 100 if total_count > 0 else 0
        
        logger.info(f"🎯 Batch fetch completed:")
        logger.info(f"   ✅ Successful: {success_count}/{total_count} ({success_rate:.1f}%)")
        logger.info(f"   ❌ Failed: {len(failed_companies)}")
        
        if failed_companies:
            logger.warning(f"❌ Failed companies: {', '.join(failed_companies[:5])}{'...' if len(failed_companies) > 5 else ''}")
        
        return batch_data
    
    def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get live quotes for multiple symbols"""
        try:
            if not self.fyers or not symbols:
                return {}
            
            # Convert symbols to Fyers format
            fyers_symbols = []
            symbol_mapping = {}
            
            for symbol in symbols:
                fyers_symbol = self.symbol_mapper._convert_to_fyers_format(symbol)
                fyers_symbols.append(fyers_symbol)
                symbol_mapping[fyers_symbol] = symbol
            
            # Fyers API supports up to 50 symbols per request
            batch_size = 50
            all_quotes = {}
            
            for i in range(0, len(fyers_symbols), batch_size):
                batch_symbols = fyers_symbols[i:i + batch_size]
                
                try:
                    data = {"symbols": ",".join(batch_symbols)}
                    response = self.fyers.quotes(data=data)
                    
                    if response and response.get('s') == 'ok':
                        quotes = response.get('d', [])
                        
                        for quote in quotes:
                            fyers_symbol = quote.get('n', '')
                            original_symbol = symbol_mapping.get(fyers_symbol, fyers_symbol)
                            
                            quote_values = quote.get('v', {})
                            all_quotes[original_symbol] = {
                                'ltp': quote_values.get('lp', 0),
                                'change': quote_values.get('ch', 0),
                                'change_pct': quote_values.get('chp', 0),
                                'volume': quote_values.get('volume', 0),
                                'timestamp': datetime.now()
                            }
                    
                    # Rate limiting between batches
                    time.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error fetching batch quotes: {e}")
            
            logger.info(f"✅ Fetched quotes for {len(all_quotes)}/{len(symbols)} symbols")
            return all_quotes
            
        except Exception as e:
            logger.error(f"Error fetching multiple quotes: {e}")
            return {}
    
    def is_connected(self) -> bool:
        """Check if Fyers API is connected"""
        try:
            if not self.fyers:
                return False
            
            # Test connection with a simple API call
            response = self.fyers.funds()
            
            if response and isinstance(response, dict):
                return response.get('s') == 'ok'
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Connection check failed: {e}")
            return False
    
    def get_funds_info(self) -> Optional[Dict[str, Any]]:
        """Get account funds information"""
        try:
            if not self.fyers:
                return None
            
            response = self.fyers.funds()
            
            if response and response.get('s') == 'ok':
                fund_data = response.get('fund_limit', [])
                
                if fund_data:
                    return {
                        'available_cash': fund_data[0].get('availableMargin', 0),
                        'used_margin': fund_data[0].get('utilizedMargin', 0),
                        'total_margin': fund_data[0].get('totalMargin', 0),
                        'last_updated': datetime.now()
                    }
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching funds info: {e}")
            return None
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """Get current positions"""
        try:
            if not self.fyers:
                return []
            
            response = self.fyers.positions()
            
            if response and response.get('s') == 'ok':
                positions = response.get('netPositions', [])
                
                processed_positions = []
                for position in positions:
                    processed_positions.append({
                        'symbol': position.get('symbol', ''),
                        'qty': position.get('qty', 0),
                        'avg_price': position.get('avgPrice', 0),
                        'market_value': position.get('marketVal', 0),
                        'pnl': position.get('unrealizedProfit', 0),
                        'product_type': position.get('productType', ''),
                        'side': position.get('side', '')
                    })
                
                return processed_positions
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """Get order history"""
        try:
            if not self.fyers:
                return []
            
            response = self.fyers.orderbook()
            
            if response and response.get('s') == 'ok':
                orders = response.get('orderBook', [])
                
                processed_orders = []
                for order in orders:
                    processed_orders.append({
                        'order_id': order.get('id', ''),
                        'symbol': order.get('symbol', ''),
                        'qty': order.get('qty', 0),
                        'price': order.get('limitPrice', 0),
                        'status': order.get('status', ''),
                        'order_type': order.get('type', ''),
                        'side': order.get('side', ''),
                        'order_time': order.get('orderDateTime', '')
                    })
                
                return processed_orders
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching orders: {e}")
            return []
    
    def place_order(self, symbol: str, side: str, qty: int, order_type: str = "MARKET", price: float = 0) -> Optional[Dict[str, Any]]:
        """Place a trading order"""
        try:
            if not self.fyers:
                logger.error("❌ Fyers API not initialized")
                return None
            
            fyers_symbol = self.symbol_mapper._convert_to_fyers_format(symbol)
            
            order_data = {
                "symbol": fyers_symbol,
                "qty": qty,
                "type": 2 if order_type == "MARKET" else 1,  # 1: Limit, 2: Market
                "side": 1 if side.upper() == "BUY" else -1,
                "productType": "CNC",  # Cash and Carry
                "limitPrice": price if order_type == "LIMIT" else 0,
                "stopPrice": 0,
                "validity": "DAY",
                "disclosedQty": 0,
                "offlineOrder": "False"
            }
            
            response = self.fyers.place_order(data=order_data)
            
            if response and response.get('s') == 'ok':
                logger.info(f"✅ Order placed successfully for {symbol}: {side} {qty} @ {price if order_type == 'LIMIT' else 'MARKET'}")
                return {
                    'order_id': response.get('id', ''),
                    'status': 'SUCCESS',
                    'message': response.get('message', ''),
                    'symbol': symbol,
                    'side': side,
                    'qty': qty,
                    'price': price,
                    'order_type': order_type
                }
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.error(f"❌ Order placement failed for {symbol}: {error_msg}")
                return {
                    'status': 'FAILED',
                    'error': error_msg,
                    'symbol': symbol
                }
            
        except Exception as e:
            logger.error(f"❌ Error placing order for {symbol}: {e}")
            return {
                'status': 'ERROR',
                'error': str(e),
                'symbol': symbol
            }
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting between API calls"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get market status information"""
        try:
            if not self.fyers:
                return {'status': 'UNKNOWN', 'error': 'API not initialized'}
            
            # Use a simple quote request to determine market status
            response = self.fyers.quotes(data={"symbols": "NSE:NIFTY50-INDEX"})
            
            if response and response.get('s') == 'ok':
                quotes = response.get('d', [])
                if quotes:
                    market_status = quotes[0].get('v', {}).get('market_status', 'unknown')
                    return {
                        'status': market_status,
                        'timestamp': datetime.now(),
                        'is_open': market_status in ['OPEN', 'PREOPEN']
                    }
            
            return {'status': 'UNKNOWN', 'error': 'Unable to determine market status'}
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return {'status': 'ERROR', 'error': str(e)}
    
    def save_session_info(self):
        """Save session information for debugging"""
        try:
            session_info = {
                'timestamp': datetime.now().isoformat(),
                'connection_status': self.is_connected(),
                'client_id': self.client_id,
                'token_available': bool(self.access_token),
                'market_status': self.get_market_status()
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_info, f, indent=2, default=str)
            
            logger.info(f"✅ Session info saved to {self.session_file}")
            
        except Exception as e:
            logger.error(f"Error saving session info: {e}")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            if self.websocket:
                self.websocket.close()
            self.save_session_info()
        except:
            pass
