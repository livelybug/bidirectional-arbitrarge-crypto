import json
import os
import hmac
import base64
import datetime
import requests
import sys

# Add current directory to path to find config if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def load_config():
    """Load API credentials from config.json"""
    if os.path.exists('config.json'):
        with open('config.json', 'r') as f:
            return json.load(f)
    print("Warning: config.json not found.")
    return {}

def get_timestamp():
    now = datetime.datetime.now(datetime.timezone.utc)
    return now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

def sign(message, secret_key):
    mac = hmac.new(bytes(secret_key, encoding='utf8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    return base64.b64encode(mac.digest()).decode('utf-8')

def get_headers(api_key, secret_key, passphrase, method, request_path, body=""):
    timestamp = get_timestamp()
    message = timestamp + method + request_path + body
    print("message to sign", message)
    signature = sign(message, secret_key)
    
    return {
        'OK-ACCESS-KEY': api_key,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-PASSPHRASE': passphrase,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'Content-Type': 'application/json'
    }

def test_quote():
    print("============================================")
    print("        OKX Quote URL Tester                ")
    print("============================================\n")

    # 1. Load Config
    config = load_config()
    api_key = str(config.get('OK-ACCESS-KEY', '')).strip()
    secret_key = str(config.get('SECRET-KEY', '')).strip()
    passphrase = str(config.get('OK-ACCESS-PASSPHRASE', '')).strip()
    
    if not api_key or not secret_key:
        print("Error: API credentials not found in config.json")
        return

    # 2. Hardcoded Test Data (or Input)
    # Defaulting to some common values for quick testing as requested
    print("Using default test values (ETH -> USDC on Ethereum). You can modify the script to change them.")
    
    chain_id = "1" # Ethereum
    from_token = "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" # ETH
    to_token = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48" # USDC
    amount = "100000000000000000" # 0.1 ETH
    slippage = "0.5"

    print(f"Chain ID: {chain_id}")
    print(f"From: {from_token}")
    print(f"To: {to_token}")
    print(f"Amount: {amount}")
    print("--------------------------------------------")

    # 3. Construct URL
    base_url = "https://web3.okx.com"
    path = "/api/v6/dex/aggregator/quote"
    
    params = {
        "chainIndex": chain_id,
        "fromTokenAddress": from_token,
        "toTokenAddress": to_token,
        "amount": amount,
        "slippagePercent": slippage
    }
    
    query_string = "?" + "&".join([f"{k}={v}" for k, v in params.items()])
    full_url = base_url + path + query_string

    print(f"\n[Request URL]: \n{full_url}")

    # 4. Generate Headers
    try:
        headers = get_headers(api_key, secret_key, passphrase, "GET", path + query_string)
    except Exception as e:
        print(f"Error generating headers: {e}")
        return

    print("full url", full_url)
    # 5. Send Request
    print("\nSending request...")
    try:
        response = requests.get(full_url, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n[Response Data]:")
            print(json.dumps(data, indent=2))
        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_quote()
