from scanner.bitget_client import BitgetClient

def test_client():
    client = BitgetClient()
    symbols = client.list_usdt_perp_symbols()
    print(f"Found {len(symbols)} symbols")
    print(f"First 10 symbols: {symbols[:10]}")
    if symbols:
        print(f"Example symbol: {symbols[0]}")
        
        # Test getting candles for the first symbol
        if symbols:
            symbol = symbols[0]
            print(f"\nTesting candles for {symbol}:")
            for tf in ['15m', '1h', '4h']:
                try:
                    candles = client.get_klines(symbol, tf, limit=10)
                    print(f"  {tf}: {len(candles)} candles")
                    if len(candles) > 0:
                        print(f"    Last candle: {candles[-1]}")
                        if len(candles) > 1:
                            print(f"    Previous candle: {candles[-2]}")
                except Exception as e:
                    print(f"  {tf}: Error - {e}")

if __name__ == "__main__":
    test_client()