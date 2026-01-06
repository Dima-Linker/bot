import requests

def test_bitget_api():
    """Test the Bitget API to see what symbols are available"""
    base_url = "https://api.bitget.com"
    
    # Test 1: Try to get all USDT perpetual symbols
    print("Test 1: Getting USDT perpetual symbols...")
    try:
        url = f"{base_url}/api/v2/mix/market/tickers"
        params = {"productType": "USDT-FUTURES"}
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Try without productType parameter to see all tickers
    print("Test 2: Getting all tickers...")
    try:
        url = f"{base_url}/api/v2/mix/market/tickers"
        response = requests.get(url, timeout=10)
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Code: {data.get('code')}")
        print(f"Has data: {'data' in data}")
        if 'data' in data and len(data['data']) > 0:
            print(f"First few tickers: {data['data'][:3]}")
            print(f"Total tickers: {len(data['data'])}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "="*50 + "\n")
    
    # Test 3: Try with different productType
    print("Test 3: Getting COIN-FUTURES symbols...")
    try:
        url = f"{base_url}/api/v2/mix/market/tickers"
        params = {"productType": "COIN-FUTURES"}
        response = requests.get(url, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_bitget_api()