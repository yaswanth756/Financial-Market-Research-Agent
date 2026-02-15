"""
Market Tools - The Agent's Professional Toolkit
=================================================
Phase 9: ALL-ROUNDER FINANCIAL AGENT

Tools:
1. get_stock_price()          → Live prices for ANY stock globally
2. get_price_history()        → Historical data & trends
3. get_portfolio_snapshot()   → Batch portfolio data
4. validate_news_vs_price()   → News vs Price validator
5. get_analyst_recommendations() → Analyst ratings & targets (NEW)
6. get_stock_fundamentals()   → Full fundamental analysis (NEW)
7. compare_stocks()           → Head-to-head comparison (NEW)
8. get_technical_indicators() → RSI, Moving Averages, MACD (NEW)
9. format_market_context()    → LLM-ready context builder

Supports: Indian (NSE/BSE) + US (NYSE/NASDAQ) + Crypto
"""

import warnings
warnings.filterwarnings('ignore')

import yfinance as yf
from datetime import datetime, timedelta
import json

# ============================================================================
# GLOBAL STOCK SYMBOL MAPPING
# ============================================================================
# Indian stocks use .NS suffix, US stocks use direct symbols

SYMBOL_MAP = {
    # ==================== INDIAN STOCKS (NSE) ====================
    # IT Sector
    "TCS": "TCS.NS", "INFY": "INFY.NS", "WIPRO": "WIPRO.NS",
    "HCLTECH": "HCLTECH.NS", "TECHM": "TECHM.NS", "LTI": "LTIM.NS",
    "LTIM": "LTIM.NS", "PERSISTENT": "PERSISTENT.NS", "COFORGE": "COFORGE.NS",
    
    # Banking
    "HDFCBANK": "HDFCBANK.NS", "ICICIBANK": "ICICIBANK.NS", "SBIN": "SBIN.NS",
    "KOTAKBANK": "KOTAKBANK.NS", "AXISBANK": "AXISBANK.NS", "BANKBARODA": "BANKBARODA.NS",
    "PNB": "PNB.NS", "INDUSINDBK": "INDUSINDBK.NS", "IDFCFIRSTB": "IDFCFIRSTB.NS",
    "BANDHANBNK": "BANDHANBNK.NS", "FEDERALBNK": "FEDERALBNK.NS",
    
    # Energy
    "RELIANCE": "RELIANCE.NS", "ONGC": "ONGC.NS", "BPCL": "BPCL.NS",
    "IOC": "IOC.NS", "NTPC": "NTPC.NS", "POWERGRID": "POWERGRID.NS",
    "ADANIGREEN": "ADANIGREEN.NS", "ADANIENT": "ADANIENT.NS",
    "ADANIPORTS": "ADANIPORTS.NS", "ADANIPOWER": "ADANIPOWER.NS",
    
    # New-Age / Consumer Internet
    "ZOMATO": "ZOMATO.NS", "PAYTM": "PAYTM.NS", "ONEPAYTM": "PAYTM.NS",
    "ONE97": "PAYTM.NS", "NYKAA": "NYKAA.NS", "POLICYBZR": "POLICYBZR.NS",
    "DELHIVERY": "DELHIVERY.NS", "CARTRADE": "CARTRADE.NS",
    "EASEMYTRIP": "EASEMYTRIP.NS", "IRCTC": "IRCTC.NS", "JIOFIN": "JIOFIN.NS",
    "SWIGGY": "SWIGGY.NS",
    
    # Large Caps
    "BHARTIARTL": "BHARTIARTL.NS", "ITC": "ITC.NS", "HINDUNILVR": "HINDUNILVR.NS",
    "MARUTI": "MARUTI.NS", "TATAMOTORS": "TATAMOTORS.NS", "BAJFINANCE": "BAJFINANCE.NS",
    "ASIANPAINT": "ASIANPAINT.NS", "SUNPHARMA": "SUNPHARMA.NS",
    "DRREDDY": "DRREDDY.NS", "TITAN": "TITAN.NS", "LT": "LT.NS",
    "TATASTEEL": "TATASTEEL.NS", "JSWSTEEL": "JSWSTEEL.NS",
    "HINDALCO": "HINDALCO.NS", "COALINDIA": "COALINDIA.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS", "GRASIM": "GRASIM.NS", "CIPLA": "CIPLA.NS",
    "APOLLOHOSP": "APOLLOHOSP.NS", "DIVISLAB": "DIVISLAB.NS",
    "HDFCLIFE": "HDFCLIFE.NS", "SBILIFE": "SBILIFE.NS",
    "BAJAJFINSV": "BAJAJFINSV.NS", "M&M": "M&M.NS", "MAHINDRA": "M&M.NS",
    "EICHERMOT": "EICHERMOT.NS", "HEROMOTOCO": "HEROMOTOCO.NS",
    "TATAPOWER": "TATAPOWER.NS", "HAL": "HAL.NS", "BEL": "BEL.NS",
    "VEDL": "VEDL.NS",
    
    # Indian Indices
    "NIFTY50": "^NSEI", "SENSEX": "^BSESN",
    "BANKNIFTY": "^NSEBANK", "NIFTYIT": "^CNXIT",
    
    # ==================== US / GLOBAL STOCKS ====================
    "AAPL": "AAPL", "APPLE": "AAPL",
    "GOOGL": "GOOGL", "GOOGLE": "GOOGL", "GOOG": "GOOGL", "ALPHABET": "GOOGL",
    "MSFT": "MSFT", "MICROSOFT": "MSFT",
    "AMZN": "AMZN", "AMAZON": "AMZN",
    "TSLA": "TSLA", "TESLA": "TSLA",
    "META": "META", "FACEBOOK": "META", "FB": "META",
    "NVDA": "NVDA", "NVIDIA": "NVDA",
    "NFLX": "NFLX", "NETFLIX": "NFLX",
    "AMD": "AMD",
    "INTC": "INTC", "INTEL": "INTC",
    "CRM": "CRM", "SALESFORCE": "CRM",
    "ORCL": "ORCL", "ORACLE": "ORCL",
    "PYPL": "PYPL", "PAYPAL": "PYPL",
    "DIS": "DIS", "DISNEY": "DIS",
    "BA": "BA", "BOEING": "BA",
    "JPM": "JPM", "JPMORGAN": "JPM",
    "GS": "GS", "GOLDMAN": "GS",
    "V": "V", "VISA": "V",
    "MA": "MA", "MASTERCARD": "MA",
    "WMT": "WMT", "WALMART": "WMT",
    "KO": "KO", "COCACOLA": "KO", "COCA-COLA": "KO",
    "PEP": "PEP", "PEPSI": "PEP",
    "JNJ": "JNJ",
    "PFE": "PFE", "PFIZER": "PFE",
    "UNH": "UNH",
    "XOM": "XOM", "EXXON": "XOM",
    "CVX": "CVX", "CHEVRON": "CVX",
    "BRK-B": "BRK-B", "BERKSHIRE": "BRK-B",
    "SPOT": "SPOT", "SPOTIFY": "SPOT",
    "UBER": "UBER",
    "ABNB": "ABNB", "AIRBNB": "ABNB",
    "SNOW": "SNOW", "SNOWFLAKE": "SNOW",
    "PLTR": "PLTR", "PALANTIR": "PLTR",
    "COIN": "COIN", "COINBASE": "COIN",
    "SQ": "SQ", "BLOCK": "SQ",
    "SHOP": "SHOP", "SHOPIFY": "SHOP",
    "ZM": "ZM", "ZOOM": "ZM",
    "BABA": "BABA", "ALIBABA": "BABA",
    "TSM": "TSM", "TSMC": "TSM",
    "SONY": "SONY",
    "NKE": "NKE", "NIKE": "NKE",
    "SBUX": "SBUX", "STARBUCKS": "SBUX",
    
    # US Indices
    "SPX": "^GSPC", "SP500": "^GSPC", "S&P500": "^GSPC", "S&P": "^GSPC",
    "DOWJONES": "^DJI", "DOW": "^DJI", "DJI": "^DJI",
    "NASDAQ": "^IXIC", "NASDAQCOMP": "^IXIC",
    "VIX": "^VIX",
    "RUSSELL2000": "^RUT",
    
    # ==================== CRYPTO ====================
    "BTC": "BTC-USD", "BITCOIN": "BTC-USD", "BTC-USD": "BTC-USD",
    "ETH": "ETH-USD", "ETHEREUM": "ETH-USD", "ETH-USD": "ETH-USD",
    "SOL": "SOL-USD", "SOLANA": "SOL-USD", "SOL-USD": "SOL-USD",
    "BNB": "BNB-USD", "BNB-USD": "BNB-USD",
    "XRP": "XRP-USD", "RIPPLE": "XRP-USD", "XRP-USD": "XRP-USD",
    "ADA": "ADA-USD", "CARDANO": "ADA-USD", "ADA-USD": "ADA-USD",
    "DOGE": "DOGE-USD", "DOGECOIN": "DOGE-USD", "DOGE-USD": "DOGE-USD",
    "DOT": "DOT-USD", "POLKADOT": "DOT-USD",
    "AVAX": "AVAX-USD", "AVALANCHE": "AVAX-USD",
    "MATIC": "MATIC-USD", "POLYGON": "MATIC-USD",
    "LINK": "LINK-USD", "CHAINLINK": "LINK-USD",
    
    # ==================== COMMODITIES ====================
    "GOLD": "GC=F", "SILVER": "SI=F", "CRUDE": "CL=F",
    "CRUDEOIL": "CL=F", "NATURALGAS": "NG=F",
}


def _resolve_symbol(symbol: str) -> str:
    """Convert any symbol to yfinance-compatible symbol"""
    sym_upper = symbol.upper().strip()
    if sym_upper in SYMBOL_MAP:
        return SYMBOL_MAP[sym_upper]
    # If already has suffix (.NS, .BO, -USD), use as-is
    if any(sym_upper.endswith(s) for s in [".NS", ".BO", "-USD", "=F"]):
        return sym_upper
    # Try direct (works for most US stocks)
    return sym_upper


def _detect_currency(yf_symbol: str) -> str:
    """Detect currency based on symbol suffix"""
    if yf_symbol.endswith(".NS") or yf_symbol.endswith(".BO"):
        return "INR"
    elif yf_symbol.endswith("-USD") or yf_symbol.endswith("=F"):
        return "USD"
    elif yf_symbol.startswith("^"):
        if "NSEI" in yf_symbol or "BSESN" in yf_symbol or "NSEBANK" in yf_symbol:
            return "INR"
        return "USD"
    return "USD"


def _format_currency(value: float, currency: str) -> str:
    """Format price with correct currency symbol"""
    if currency == "INR":
        return f"₹{value:,.2f}"
    return f"${value:,.2f}"


def _format_large_number(value: float, currency: str = "USD") -> str:
    """Format market cap / large numbers"""
    sym = "₹" if currency == "INR" else "$"
    if value >= 1e12:
        return f"{sym}{value/1e12:.2f}T"
    elif value >= 1e9:
        return f"{sym}{value/1e9:.2f}B"
    elif value >= 1e7 and currency == "INR":
        return f"{sym}{value/1e7:.0f}Cr"
    elif value >= 1e6:
        return f"{sym}{value/1e6:.2f}M"
    return f"{sym}{value:,.0f}"


# ============================================================================
# TOOL 1: GET STOCK PRICE (The Ticker)
# ============================================================================

def get_stock_price(symbol: str) -> dict:
    """
    Fetch current/latest stock price and key metrics.
    Works for ANY stock globally — Indian, US, Crypto, Commodities.
    """
    yf_symbol = _resolve_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        prev_close = info.get('previousClose') or info.get('regularMarketPreviousClose', 0)
        
        if prev_close and prev_close > 0:
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
        else:
            change = 0
            change_pct = 0

        currency = info.get('currency', _detect_currency(yf_symbol))

        result = {
            "symbol": symbol.upper(),
            "yf_symbol": yf_symbol,
            "name": info.get('longName') or info.get('shortName', symbol),
            "current_price": round(current_price, 2),
            "previous_close": round(prev_close, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "day_high": round(info.get('dayHigh', 0) or 0, 2),
            "day_low": round(info.get('dayLow', 0) or 0, 2),
            "open": round(info.get('open', 0) or 0, 2),
            "volume": info.get('volume', 0) or 0,
            "avg_volume": info.get('averageVolume', 0) or 0,
            "52_week_high": round(info.get('fiftyTwoWeekHigh', 0) or 0, 2),
            "52_week_low": round(info.get('fiftyTwoWeekLow', 0) or 0, 2),
            "market_cap": info.get('marketCap', 0) or 0,
            "pe_ratio": round(info.get('trailingPE', 0) or 0, 2),
            "forward_pe": round(info.get('forwardPE', 0) or 0, 2),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "currency": currency,
            "exchange": info.get('exchange', 'N/A'),
            "success": True,
        }
        
        return result
        
    except Exception as e:
        return {
            "symbol": symbol.upper(),
            "error": str(e),
            "success": False,
        }


# ============================================================================
# TOOL 2: GET PRICE HISTORY (The Calculator)
# ============================================================================

def get_price_history(symbol: str, period: str = "5d") -> dict:
    """
    Fetch recent price history for trend analysis.
    Periods: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"
    """
    yf_symbol = _resolve_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period=period)
        
        if hist.empty:
            return {"symbol": symbol, "error": "No data available", "success": False}
        
        prices = []
        for date, row in hist.iterrows():
            prices.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": round(row['Open'], 2),
                "close": round(row['Close'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "volume": int(row['Volume']),
            })
        
        first_close = prices[0]['close']
        last_close = prices[-1]['close']
        total_change = last_close - first_close
        total_change_pct = (total_change / first_close) * 100 if first_close > 0 else 0
        
        if total_change_pct > 2:
            trend = "STRONGLY_UP"
        elif total_change_pct > 0.5:
            trend = "UP"
        elif total_change_pct > -0.5:
            trend = "FLAT"
        elif total_change_pct > -2:
            trend = "DOWN"
        else:
            trend = "STRONGLY_DOWN"
        
        return {
            "symbol": symbol.upper(),
            "period": period,
            "prices": prices,
            "trend": trend,
            "total_change_pct": round(total_change_pct, 2),
            "start_price": first_close,
            "end_price": last_close,
            "success": True,
        }
        
    except Exception as e:
        return {"symbol": symbol, "error": str(e), "success": False}


# ============================================================================
# TOOL 3: GET PORTFOLIO SNAPSHOT (Batch Ticker)
# ============================================================================

def get_portfolio_snapshot(symbols: list) -> dict:
    """Fetch live prices for all portfolio stocks at once."""
    snapshot = {}
    total_gainers = 0
    total_losers = 0
    total_unchanged = 0
    
    for sym in symbols:
        data = get_stock_price(sym)
        snapshot[sym] = data
        
        if data.get('success'):
            if data.get('change_pct', 0) > 0.1:
                total_gainers += 1
            elif data.get('change_pct', 0) < -0.1:
                total_losers += 1
            else:
                total_unchanged += 1
    
    return {
        "stocks": snapshot,
        "summary": {
            "total": len(symbols),
            "gainers": total_gainers,
            "losers": total_losers,
            "unchanged": total_unchanged,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        },
        "success": True,
    }


# ============================================================================
# TOOL 4: NEWS vs PRICE VALIDATOR (The Brain)
# ============================================================================

def validate_news_vs_price(symbol: str, news_sentiment: str) -> dict:
    """Cross-reference news sentiment with actual price action."""
    price_data = get_stock_price(symbol)
    history = get_price_history(symbol, "5d")
    
    if not price_data.get('success') or not history.get('success'):
        return {
            "symbol": symbol,
            "verdict": "UNABLE_TO_VALIDATE",
            "reason": "Could not fetch market data",
            "success": False,
        }
    
    change_pct = price_data.get('change_pct', 0)
    weekly_trend = history.get('total_change_pct', 0)
    
    verdict = "UNKNOWN"
    explanation = ""
    action_hint = ""
    
    if news_sentiment == "negative":
        if change_pct < -1.5:
            verdict = "PRICED_IN"
            explanation = f"Stock already down {change_pct:.1f}% today. The bad news is reflected."
            action_hint = "Don't panic sell. The drop already happened."
        elif change_pct > 1.0:
            verdict = "CONTRARIAN_SIGNAL"
            explanation = f"News is negative but stock is UP {change_pct:.1f}%. Market expected worse."
            action_hint = "Market disagrees with negative news. Hold or consider adding."
        else:
            verdict = "DEVELOPING"
            explanation = f"Stock moved {change_pct:+.1f}% today. Market hasn't fully reacted yet."
            action_hint = "Watch closely. Full reaction may come tomorrow."
    elif news_sentiment == "positive":
        if change_pct > 1.5:
            verdict = "PRICED_IN"
            explanation = f"Stock already up {change_pct:.1f}% today. Good news reflected."
            action_hint = "Don't chase. Consider waiting for a dip."
        elif change_pct < -1.0:
            verdict = "CONTRARIAN_SIGNAL"
            explanation = f"News is positive but stock is DOWN {change_pct:.1f}%. Market may know something."
            action_hint = "Be cautious. Something else may be going on."
        else:
            verdict = "DEVELOPING"
            explanation = f"Stock moved {change_pct:+.1f}% today. Market hasn't fully reacted."
            action_hint = "Potential opportunity if positive news is legit."
    else:
        verdict = "NEUTRAL"
        explanation = f"News is neutral. Stock moved {change_pct:+.1f}% today."
        action_hint = "No significant action needed."
    
    return {
        "symbol": symbol.upper(),
        "news_sentiment": news_sentiment,
        "actual_price_change": f"{change_pct:+.1f}%",
        "weekly_trend": f"{weekly_trend:+.1f}%",
        "verdict": verdict,
        "explanation": explanation,
        "action_hint": action_hint,
        "price_data": {
            "current": price_data.get('current_price'),
            "prev_close": price_data.get('previous_close'),
            "day_high": price_data.get('day_high'),
            "day_low": price_data.get('day_low'),
        },
        "success": True,
    }


# ============================================================================
# TOOL 5: ANALYST RECOMMENDATIONS (NEW)
# ============================================================================

def get_analyst_recommendations(symbol: str) -> dict:
    """
    Fetch analyst recommendations, target prices, and ratings.
    Returns: buy/sell/hold counts, mean target price, current consensus.
    """
    yf_symbol = _resolve_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        
        # Get recommendation data
        target_high = info.get('targetHighPrice', 0) or 0
        target_low = info.get('targetLowPrice', 0) or 0
        target_mean = info.get('targetMeanPrice', 0) or 0
        target_median = info.get('targetMedianPrice', 0) or 0
        current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        recommendation = info.get('recommendationKey', 'N/A')
        num_analysts = info.get('numberOfAnalystOpinions', 0) or 0
        
        # Calculate upside/downside
        if current_price > 0 and target_mean > 0:
            upside_pct = ((target_mean - current_price) / current_price) * 100
        else:
            upside_pct = 0
        
        # Try to get recent recommendations history
        recs_history = []
        try:
            recs_df = ticker.recommendations
            if recs_df is not None and not recs_df.empty:
                recent = recs_df.tail(10)
                for _, row in recent.iterrows():
                    recs_history.append({
                        "firm": str(row.get('Firm', 'Unknown')),
                        "grade": str(row.get('To Grade', row.get('toGrade', 'N/A'))),
                        "action": str(row.get('Action', row.get('action', 'N/A'))),
                    })
        except Exception:
            pass
        
        # Map recommendation to readable format
        rec_map = {
            'strong_buy': 'STRONG BUY 🟢🟢',
            'buy': 'BUY 🟢',
            'hold': 'HOLD ⚪',
            'sell': 'SELL 🔴',
            'strong_sell': 'STRONG SELL 🔴🔴',
            'underperform': 'UNDERPERFORM 🔴',
            'outperform': 'OUTPERFORM 🟢',
            'overweight': 'OVERWEIGHT 🟢',
            'underweight': 'UNDERWEIGHT 🔴',
            'neutral': 'NEUTRAL ⚪',
        }
        
        consensus_display = rec_map.get(recommendation, recommendation.upper() if recommendation != 'N/A' else 'N/A')
        currency = info.get('currency', _detect_currency(yf_symbol))
        
        return {
            "symbol": symbol.upper(),
            "name": info.get('longName') or info.get('shortName', symbol),
            "current_price": round(current_price, 2),
            "consensus": consensus_display,
            "recommendation_key": recommendation,
            "num_analysts": num_analysts,
            "target_high": round(target_high, 2),
            "target_low": round(target_low, 2),
            "target_mean": round(target_mean, 2),
            "target_median": round(target_median, 2),
            "upside_pct": round(upside_pct, 2),
            "recent_recommendations": recs_history[-5:],
            "currency": currency,
            "success": True,
        }
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e), "success": False}


# ============================================================================
# TOOL 6: STOCK FUNDAMENTALS (NEW)
# ============================================================================

def get_stock_fundamentals(symbol: str) -> dict:
    """
    Full fundamental analysis: financials, ratios, growth, dividends.
    """
    yf_symbol = _resolve_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        info = ticker.info
        currency = info.get('currency', _detect_currency(yf_symbol))
        
        # Valuation Metrics
        valuation = {
            "market_cap": info.get('marketCap', 0) or 0,
            "market_cap_formatted": _format_large_number(info.get('marketCap', 0) or 0, currency),
            "enterprise_value": info.get('enterpriseValue', 0) or 0,
            "trailing_pe": round(info.get('trailingPE', 0) or 0, 2),
            "forward_pe": round(info.get('forwardPE', 0) or 0, 2),
            "peg_ratio": round(info.get('pegRatio', 0) or 0, 2),
            "price_to_book": round(info.get('priceToBook', 0) or 0, 2),
            "price_to_sales": round(info.get('priceToSalesTrailing12Months', 0) or 0, 2),
            "ev_to_ebitda": round(info.get('enterpriseToEbitda', 0) or 0, 2),
        }
        
        # Profitability
        profitability = {
            "revenue": info.get('totalRevenue', 0) or 0,
            "revenue_formatted": _format_large_number(info.get('totalRevenue', 0) or 0, currency),
            "revenue_growth": round((info.get('revenueGrowth', 0) or 0) * 100, 2),
            "gross_margins": round((info.get('grossMargins', 0) or 0) * 100, 2),
            "operating_margins": round((info.get('operatingMargins', 0) or 0) * 100, 2),
            "profit_margins": round((info.get('profitMargins', 0) or 0) * 100, 2),
            "ebitda": info.get('ebitda', 0) or 0,
            "ebitda_formatted": _format_large_number(info.get('ebitda', 0) or 0, currency),
            "net_income": info.get('netIncomeToCommon', 0) or 0,
            "eps_trailing": round(info.get('trailingEps', 0) or 0, 2),
            "eps_forward": round(info.get('forwardEps', 0) or 0, 2),
            "earnings_growth": round((info.get('earningsGrowth', 0) or 0) * 100, 2),
        }
        
        # Balance Sheet Health
        balance_sheet = {
            "total_cash": info.get('totalCash', 0) or 0,
            "total_cash_formatted": _format_large_number(info.get('totalCash', 0) or 0, currency),
            "total_debt": info.get('totalDebt', 0) or 0,
            "total_debt_formatted": _format_large_number(info.get('totalDebt', 0) or 0, currency),
            "debt_to_equity": round(info.get('debtToEquity', 0) or 0, 2),
            "current_ratio": round(info.get('currentRatio', 0) or 0, 2),
            "quick_ratio": round(info.get('quickRatio', 0) or 0, 2),
            "return_on_equity": round((info.get('returnOnEquity', 0) or 0) * 100, 2),
            "return_on_assets": round((info.get('returnOnAssets', 0) or 0) * 100, 2),
            "book_value": round(info.get('bookValue', 0) or 0, 2),
        }
        
        # Dividends
        dividends = {
            "dividend_rate": round(info.get('dividendRate', 0) or 0, 2),
            "dividend_yield": round((info.get('dividendYield', 0) or 0) * 100, 2),
            "payout_ratio": round((info.get('payoutRatio', 0) or 0) * 100, 2),
            "ex_dividend_date": str(info.get('exDividendDate', 'N/A')),
            "five_year_avg_yield": round((info.get('fiveYearAvgDividendYield', 0) or 0), 2),
        }
        
        # Share Stats
        shares = {
            "shares_outstanding": info.get('sharesOutstanding', 0) or 0,
            "float_shares": info.get('floatShares', 0) or 0,
            "held_by_insiders": round((info.get('heldPercentInsiders', 0) or 0) * 100, 2),
            "held_by_institutions": round((info.get('heldPercentInstitutions', 0) or 0) * 100, 2),
            "short_ratio": round(info.get('shortRatio', 0) or 0, 2),
        }
        
        return {
            "symbol": symbol.upper(),
            "name": info.get('longName') or info.get('shortName', symbol),
            "sector": info.get('sector', 'N/A'),
            "industry": info.get('industry', 'N/A'),
            "description": info.get('longBusinessSummary', 'N/A')[:500],
            "currency": currency,
            "current_price": round(info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0, 2),
            "52_week_high": round(info.get('fiftyTwoWeekHigh', 0) or 0, 2),
            "52_week_low": round(info.get('fiftyTwoWeekLow', 0) or 0, 2),
            "50_day_avg": round(info.get('fiftyDayAverage', 0) or 0, 2),
            "200_day_avg": round(info.get('twoHundredDayAverage', 0) or 0, 2),
            "beta": round(info.get('beta', 0) or 0, 2),
            "valuation": valuation,
            "profitability": profitability,
            "balance_sheet": balance_sheet,
            "dividends": dividends,
            "shares": shares,
            "success": True,
        }
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e), "success": False}


# ============================================================================
# TOOL 7: COMPARE STOCKS
# ============================================================================

def compare_stocks(symbols: list) -> dict:
    """
    Head-to-head comparison of 2+ stocks.
    Returns: prices, PE, market cap, margins, growth for each.
    """
    comparison = {}
    
    for sym in symbols:
        price_data = get_stock_price(sym)
        fundamentals = get_stock_fundamentals(sym)
        
        if price_data.get('success') and fundamentals.get('success'):
            comparison[sym.upper()] = {
                "name": price_data.get('name', sym),
                "price": price_data.get('current_price', 0),
                "change_pct": price_data.get('change_pct', 0),
                "market_cap": fundamentals['valuation']['market_cap_formatted'],
                "pe_ratio": fundamentals['valuation']['trailing_pe'],
                "forward_pe": fundamentals['valuation']['forward_pe'],
                "revenue": fundamentals['profitability']['revenue_formatted'],
                "revenue_growth": fundamentals['profitability']['revenue_growth'],
                "profit_margin": fundamentals['profitability']['profit_margins'],
                "operating_margin": fundamentals['profitability']['operating_margins'],
                "roe": fundamentals['balance_sheet']['return_on_equity'],
                "debt_to_equity": fundamentals['balance_sheet']['debt_to_equity'],
                "dividend_yield": fundamentals['dividends']['dividend_yield'],
                "beta": fundamentals.get('beta', 0),
                "52w_high": price_data.get('52_week_high', 0),
                "52w_low": price_data.get('52_week_low', 0),
                "currency": price_data.get('currency', 'USD'),
            }
        else:
            comparison[sym.upper()] = {
                "error": price_data.get('error', 'Failed to fetch data'),
                "success": False,
            }
            
    return {
        "comparison": comparison,
        "symbols": [s.upper() for s in symbols],
        "success": True,
    }


# ============================================================================
# TOOL 8: TECHNICAL INDICATORS
# ============================================================================

def get_technical_indicators(symbol: str) -> dict:
    """
    Calculate key technical indicators: RSI, Moving Averages, MACD, Bollinger Bands.
    """
    yf_symbol = _resolve_symbol(symbol)
    
    try:
        ticker = yf.Ticker(yf_symbol)
        hist = ticker.history(period="6mo")
        
        if hist.empty or len(hist) < 50:
            return {"symbol": symbol, "error": "Insufficient data for technicals", "success": False}
        
        closes = hist['Close'].values
        current = closes[-1]
        
        # --- RSI (14) ---
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else 0
        avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else 0
        
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
        # --- Moving Averages ---
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50
        
        # --- MACD (12, 26, 9) ---
        def calc_ema(data, period):
            k = 2 / (period + 1)
            ema = [data[0]]
            for i in range(1, len(data)):
                ema.append(data[i] * k + ema[-1] * (1 - k))
            return ema
            
        ema_12 = calc_ema(closes, 12)
        ema_26 = calc_ema(closes, 26)
        macd_line = ema_12[-1] - ema_26[-1]
        
        macd_series = [ema_12[i] - ema_26[i] for i in range(len(ema_26))]
        signal_series = calc_ema(macd_series, 9)
        signal_line = signal_series[-1]
        macd_histogram = macd_line - signal_line
        
        # --- Bollinger Bands (20, 2) ---
        bb_mean = sma_20
        # Calculate std dev properly
        variance = sum((c - bb_mean) ** 2 for c in closes[-20:]) / 20
        bb_std = variance ** 0.5
        bb_upper = bb_mean + (2 * bb_std)
        bb_lower = bb_mean - (2 * bb_std)
        
        # --- Signals ---
        signals = []
        if rsi > 70:
            signals.append("⚠️ RSI OVERBOUGHT (>70) — May see a pullback")
        elif rsi < 30:
            signals.append("🟢 RSI OVERSOLD (<30) — Potential bounce zone")
            
        if current > sma_20 > sma_50:
            signals.append("🟢 BULLISH: Price above both SMA20 & SMA50")
        elif current < sma_20 < sma_50:
            signals.append("🔴 BEARISH: Price below both SMA20 & SMA50")
            
        if macd_histogram > 0 and macd_line > signal_line:
            signals.append("🟢 MACD BULLISH: Above signal line")
        elif macd_histogram < 0 and macd_line < signal_line:
            signals.append("🔴 MACD BEARISH: Below signal line")
            
        if current > bb_upper:
            signals.append("⚠️ ABOVE upper Bollinger Band — Overextended")
        elif current < bb_lower:
            signals.append("🟢 BELOW lower Bollinger Band — Oversold territory")
            
        # Overall Signal
        bullish_count = sum(1 for s in signals if "🟢" in s)
        bearish_count = sum(1 for s in signals if "🔴" in s or "⚠️" in s)
        
        if bullish_count > bearish_count:
            overall = "BULLISH 🟢"
        elif bearish_count > bullish_count:
            overall = "BEARISH 🔴"
        else:
            overall = "NEUTRAL ⚪"
            
        return {
            "symbol": symbol.upper(),
            "current_price": round(current, 2),
            "rsi_14": round(rsi, 2),
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "ema_12": round(ema_12[-1], 2),
            "ema_26": round(ema_26[-1], 2),
            "macd_line": round(macd_line, 2),
            "signal_line": round(signal_line, 2),
            "macd_histogram": round(macd_histogram, 2),
            "bollinger_upper": round(bb_upper, 2),
            "bollinger_lower": round(bb_lower, 2),
            "bollinger_mid": round(bb_mean, 2),
            "signals": signals,
            "overall_signal": overall,
            "success": True,
        }
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e), "success": False}


# ============================================================================
# FORMAT TOOLS OUTPUT FOR LLM CONTEXT
# ============================================================================

def format_market_context(portfolio_symbols: list) -> str:
    """Generate formatted market context string for LLM prompt."""
    lines = ["## 📈 LIVE MARKET DATA (Real-time)\n"]
    
    for sym in portfolio_symbols:
        data = get_stock_price(sym)
        if data.get('success'):
            emoji = "🟢" if data['change_pct'] > 0 else "🔴" if data['change_pct'] < 0 else "⚪"
            currency = data.get('currency', 'INR')
            price_str = _format_currency(data['current_price'], currency)
            lines.append(
                f"{emoji} **{data.get('name', data['symbol'])}** ({data['symbol']}) "
                f"| {price_str} "
                f"| Change: {data['change_pct']:+.2f}% "
                f"| Day: {_format_currency(data['day_low'], currency)} - {_format_currency(data['day_high'], currency)} "
                f"| Vol: {data.get('volume', 0):,}"
            )
        else:
            lines.append(f"⚠️ **{sym}**: Price data unavailable")
    
    # Add index data
    for idx in ["NIFTY50", "SENSEX", "SPX", "NASDAQ", "BTC-USD", "GOLD"]:
        # Only add if not already in portfolio
        if idx not in portfolio_symbols:
            data = get_stock_price(idx)
            if data.get('success'):
                emoji = "🟢" if data['change_pct'] > 0 else "🔴" if data['change_pct'] < 0 else "⚪"
                lines.append(
                    f"{emoji} **{data.get('name', idx)}**: {data['current_price']:,.2f} ({data['change_pct']:+.2f}%)"
                )
            
    return "\n".join(lines)


def format_stock_detail(symbol: str) -> str:
    """Generate a rich formatted stock detail for LLM context."""
    data = get_stock_price(symbol)
    if not data.get('success'):
        return f"⚠️ Could not fetch data for {symbol}"

    currency = data.get('currency', 'USD')
    price_str = _format_currency(data['current_price'], currency)
    emoji = "🟢" if data['change_pct'] > 0 else "🔴" if data['change_pct'] < 0 else "⚪"
    
    mcap = data.get('market_cap', 0)
    mcap_str = _format_large_number(mcap, currency) if mcap else "N/A"
    
    return (
        f"{emoji} **{data.get('name', symbol)}** ({data['symbol']})\n"
        f"   Price: {price_str} | Change: {data['change_pct']:+.2f}%\n"
        f"   Day Range: {_format_currency(data['day_low'], currency)} - {_format_currency(data['day_high'], currency)}\n"
        f"   52W Range: {_format_currency(data.get('52_week_low', 0), currency)} - {_format_currency(data.get('52_week_high', 0), currency)}\n"
        f"   PE: {data.get('pe_ratio', 'N/A')} | Fwd PE: {data.get('forward_pe', 'N/A')} | MCap: {mcap_str}\n"
        f"   Volume: {data.get('volume', 0):,} (Avg: {data.get('avg_volume', 0):,})\n"
        f"   Sector: {data.get('sector', 'N/A')} | Industry: {data.get('industry', 'N/A')}"
    )


# ============================================================================
# DEMO / TEST
# ============================================================================

if __name__ == "__main__":
    print("="*60)
    print("🔧 Market Tools v2 — All-Rounder Demo")
    print("="*60)
    
    # Test 1: Indian stock
    print("\n--- Indian Stock (TCS) ---")
    result = get_stock_price("TCS")
    print(json.dumps({k: v for k, v in result.items() if k != 'yf_symbol'}, indent=2))
    
    # Test 2: US stock
    print("\n--- US Stock (Apple) ---")
    result = get_stock_price("AAPL")
    print(json.dumps({k: v for k, v in result.items() if k != 'yf_symbol'}, indent=2))
    
    # Test 3: Crypto
    print("\n--- Crypto (Bitcoin) ---")
    result = get_stock_price("BTC")
    print(json.dumps({k: v for k, v in result.items() if k != 'yf_symbol'}, indent=2))
    
    # Test 4: Analyst Recommendations
    print("\n--- Analyst Recommendations (TSLA) ---")
    recs = get_analyst_recommendations("TSLA")
    print(json.dumps(recs, indent=2))
    
    # Test 5: Fundamentals
    print("\n--- Fundamentals (MSFT) ---")
    fund = get_stock_fundamentals("MSFT")
    if fund.get('success'):
        print(f"PE: {fund['valuation']['trailing_pe']}, Revenue: {fund['profitability']['revenue_formatted']}")
    
    # Test 6: Compare
    print("\n--- Compare (GOOGL vs MSFT) ---")
    comp = compare_stocks(["GOOGL", "MSFT"])
    print(json.dumps(comp, indent=2, default=str))
    
    # Test 7: Technicals
    print("\n--- Technical Indicators (RELIANCE) ---")
    tech = get_technical_indicators("RELIANCE")
    print(json.dumps(tech, indent=2))
