import requests

def test_api():
    base_url = "https://api.bitget.com"
    url = f"{base_url}/api/v2/mix/market/tickers"
    params = {"productType": "USDT-FUTURES"}
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    print("Full response structure:")
    print(f"Keys: {list(data.keys())}")
    print(f"Code: {data.get('code')}")
    print(f"Has 'data' key: {'data' in data}")
    
    if 'data' in data:
        inner_data = data['data']
        print(f"Inner data type: {type(inner_data)}")
        if isinstance(inner_data, dict):
            print(f"Inner data keys: {list(inner_data.keys()) if isinstance(inner_data, dict) else 'Not a dict'}")
            if 'data' in inner_data:
                tickers = inner_data['data']
                print(f"Tickers type: {type(tickers)}")
                print(f"Number of tickers: {len(tickers) if isinstance(tickers, list) else 'Not a list'}")
                if isinstance(tickers, list) and len(tickers) > 0:
                    print(f"First ticker: {tickers[0]}")
                    print(f"First symbol: {tickers[0].get('symbol', 'No symbol key')}")
        elif isinstance(inner_data, list):
            print(f"Direct list length: {len(inner_data)}")
            if len(inner_data) > 0:
                print(f"First item: {inner_data[0]}")

if __name__ == "__main__":
    test_api()