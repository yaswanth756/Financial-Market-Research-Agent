
import sys
import os
import yfinance as yf

# Check version
print(f"yfinance version: {yf.__version__}")

stocks = ["TCS.NS", "GOOGL", "ZOMATO.NS"]

for s in stocks:
    print(f"\n--- Checking {s} ---")
    try:
        t = yf.Ticker(s)
        # Try history
        hist = t.history(period="1d")
        if not hist.empty:
            last_close = hist['Close'].iloc[-1]
            print(f"History (Last Close): {last_close:.2f}")
        else:
            print("History empty")
            
        # Try fast_info
        try:
            fast_info = t.fast_info
            curr = fast_info['last_price']
            print(f"Fast Info (Last Price): {curr:.2f}")
        except Exception as e:
            print(f"Fast Info failed: {e}")
            
        # Try info last
        info = t.info
        curr_info = info.get('currentPrice') or info.get('regularMarketPrice')
        print(f"Info (Current Price): {curr_info}")
        
    except Exception as e:
        print(f"Error for {s}: {e}")
