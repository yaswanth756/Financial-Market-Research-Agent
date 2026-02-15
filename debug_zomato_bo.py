
import yfinance as yf

print("--- Checking ZOMATO.BO ---")
try:
    t = yf.Ticker("ZOMATO.BO")
    print("History (period=1d):")
    hist = t.history(period="1d")
    if not hist.empty:
        print(hist.tail())
        print(f"Last Price: {hist['Close'].iloc[-1]}")
    else:
        print("History empty")
        
    print("Info:")
    print(t.info.get('currentPrice'))
except Exception as e:
    print(e)
