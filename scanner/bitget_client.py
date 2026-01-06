import requests
from typing import List, Dict, Any


class BitgetClient:
    def __init__(self, base_url: str = "https://api.bitget.com"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()

    def list_usdt_perp_symbols(self) -> List[str]:
        """Get all USDT perpetual symbols from Bitget"""
        try:
            url = f"{self.base_url}/api/v2/mix/market/tickers"
            params = {
                "productType": "USDT-FUTURES"  # USDT perpetual futures
            }
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Handle the actual data structure: code is '00000' and data is a direct list
            if str(data.get('code')) == '00000' and 'data' in data and isinstance(data['data'], list):
                tickers_data = data['data']
                symbols = []
                for ticker in tickers_data:
                    symbol = ticker.get('symbol')
                    # Include any symbol that looks like a USDT perpetual future
                    # Most symbols are in the format BTCUSDT, ETHUSDT, etc.
                    if symbol and symbol.endswith('USDT'):
                        symbols.append(symbol)
                return symbols
            else:
                print(f"API Error or unexpected structure: {data}")
                return []
        except Exception as e:
            print(f"Error fetching symbols: {e}")
            return []

    def get_klines(self, symbol: str, timeframe: str, limit: int = 200) -> List[Dict[str, Any]]:
        """Get klines/candles for a symbol and timeframe"""
        # Convert timeframe to Bitget format for the candles endpoint
        # Different endpoints may have different formats
        tf_map = {
            '15m': '15m',  # Try the original format
            '1h': '1H',    # Try uppercase H
            '4h': '4H',    # Try uppercase H
            '1d': '1D'     # Try uppercase D
        }
        
        bitget_tf = tf_map.get(timeframe)
        if not bitget_tf:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        
        try:
            url = f"{self.base_url}/api/v2/mix/market/candles"
            params = {
                "symbol": symbol,  # Use the symbol as-is (e.g., BTCUSDT)
                "productType": "USDT-FUTURES",
                "granularity": bitget_tf,
                "limit": str(limit)
            }
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            # Handle the actual data structure for candles: code is '00000' and data is a direct list
            if str(data.get('code')) == '00000' and 'data' in data and isinstance(data['data'], list):
                candles_data = data['data']
                candles = []
                for candle in candles_data:
                    # Format: [timestamp, open, high, low, close, volume, ...]
                    if len(candle) >= 6:
                        candles.append({
                            'ts': int(candle[0]),
                            'open': float(candle[1]),
                            'high': float(candle[2]),
                            'low': float(candle[3]),
                            'close': float(candle[4]),
                            'volume': float(candle[5])
                        })
                # Reverse to get oldest first
                return list(reversed(candles))
            else:
                print(f"API Error for {symbol} {timeframe}: {data}")
                return []
        except Exception as e:
            print(f"Error fetching klines for {symbol} {timeframe}: {e}")
            return []