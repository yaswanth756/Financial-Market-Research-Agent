
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from market_tools import get_stock_price, _resolve_symbol
import yfinance as yf

print("--- Resolving Symbol ---")
resolved = _resolve_symbol("ZOMATO")
print(f" 'ZOMATO' resolves to: '{resolved}'")

print("\n--- Testing get_stock_price('ZOMATO') ---")
data = get_stock_price("ZOMATO")
import json
print(json.dumps(data, indent=2))

print("\n--- Direct yfinance Check ('ZOMATO.NS') ---")
try:
    ticker = yf.Ticker("ZOMATO.NS")
    info = ticker.info
    print(f"Keys found: {len(info.keys())}")
    print(f"Current Price: {info.get('currentPrice')}")
    print(f"RegularMarketPrice: {info.get('regularMarketPrice')}")
except Exception as e:
    print(f"Direct yf error: {e}")
