"""
Flask API for Financial Analyst — ALL-ROUNDER Edition
======================================================
Professional REST API with Smart Query Routing

Endpoints:
  GET  /api/health              → Health check
  GET  /api/portfolio           → Get user portfolio
  POST /api/portfolio           → Update portfolio
  GET  /api/market-data         → Live market ticker data
  POST /api/analyze             → Smart query routing (main endpoint)
  GET  /api/morning-briefing    → Morning portfolio briefing
  GET  /api/stock/<symbol>      → Quick stock price lookup (NEW)
  GET  /api/fundamentals/<sym>  → Fundamental analysis data (NEW)
  GET  /api/recommendations/<s> → Analyst recommendations (NEW)
  GET  /api/technicals/<symbol> → Technical indicators (NEW)
  POST /api/compare             → Compare 2+ stocks (NEW)
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import warnings
warnings.filterwarnings('ignore')

import os
import ssl

# SSL Fix for corporate networks
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

from analyst import GeminiAnalyst
from user_config import PORTFOLIO, USER_PROFILE
from market_tools import (
    get_stock_price,
    get_portfolio_snapshot,
    get_stock_fundamentals,
    get_analyst_recommendations,
    get_technical_indicators,
    compare_stocks,
    get_price_history,
)

app = Flask(__name__)
CORS(app)  # Allow frontend to connect

# Initialize analyst once
print("🚀 Starting MarketMind ALL-ROUNDER API...")
analyst = GeminiAnalyst()
print("✅ API Ready! (10 Routes Active)")

# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": analyst.model,
        "version": "2.0",
        "routes": ["STOCK_PRICE", "RECOMMENDATIONS", "FUNDAMENTALS", "COMPARISON",
                    "TECHNICALS", "NEWS_SEARCH", "PORTFOLIO", "DISCOVERY",
                    "GENERAL_MARKET", "CONVERSATIONAL"],
        "coverage": ["Indian (NSE)", "US (NYSE/NASDAQ)", "Crypto", "Commodities"],
    })

# ============================================================================
# PORTFOLIO CRUD
# ============================================================================
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    """Get user's portfolio (Dynamic)"""
    from user_config import load_portfolio
    data = load_portfolio()
    return jsonify({
        "stocks": data.get("stocks", []),
        "sectors": data.get("sectors", []),
        "profile": data.get("profile", {})
    })

@app.route('/api/portfolio', methods=['POST'])
def save_portfolio():
    """Update user's portfolio & profile"""
    try:
        from user_config import save_portfolio_data

        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        if "stocks" not in data or "profile" not in data:
            return jsonify({"error": "Missing stocks or profile"}), 400

        success = save_portfolio_data(data)

        if success:
            global analyst
            analyst.portfolio = {"stocks": data["stocks"], "sectors": data.get("sectors", [])}
            analyst.profile = data["profile"]
            analyst.portfolio_symbols = [s['symbol'].upper() for s in data["stocks"]]

            return jsonify({"success": True, "message": "Portfolio updated!"})
        else:
            return jsonify({"error": "Failed to save data"}), 500

    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# MARKET DATA (Ticker)
# ============================================================================
@app.route('/api/market-data', methods=['GET'])
def get_market_data():
    """Get live market data for the user's portfolio + indices."""
    try:
        from user_config import load_portfolio
        data = load_portfolio()
        stocks = data.get("stocks", [])

        symbols = [s['symbol'] for s in stocks]
        symbols.extend(["NIFTY50", "SENSEX"])

        snapshot = get_portfolio_snapshot(symbols)
        return jsonify(snapshot)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# MAIN ANALYSIS ENDPOINT (Smart Query Routing)
# ============================================================================
@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Main analysis endpoint with professional query routing.
    Automatically detects intent and routes to the right analysis pipeline.
    """
    data = request.json
    query = data.get('query', '')

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        from analyst import classify_query, ROUTE_EMOJI, ROUTE_LABEL
        
        # Classify the query to get route info for the frontend
        route_info = classify_query(query, analyst.portfolio_symbols)
        route = route_info.get("route", "GENERAL")
        
        # Get analysis from Gemini
        report = analyst.analyze(query, top_k=5)
        
        return jsonify({
            "query": query,
            "report": report,
            "route": route,
            "route_label": ROUTE_LABEL.get(route, route),
            "route_emoji": ROUTE_EMOJI.get(route, "🤖"),
            "symbols": route_info.get("symbols", []),
            "intent": route_info.get("intent", "unknown"),
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

# ============================================================================
# MORNING BRIEFING
# ============================================================================
@app.route('/api/morning-briefing', methods=['GET'])
def morning_briefing():
    """Get morning portfolio briefing"""
    try:
        report = analyst.morning_briefing()
        return jsonify({
            "report": report,
            "route": "PORTFOLIO",
            "route_label": "Morning Briefing",
            "route_emoji": "☀️",
            "success": True
        })
    except Exception as e:
        return jsonify({
            "error": str(e),
            "success": False
        }), 500

# ============================================================================
# NEW: QUICK STOCK PRICE LOOKUP
# ============================================================================
@app.route('/api/stock/<symbol>', methods=['GET'])
def stock_price(symbol):
    """
    Quick stock price lookup for ANY stock globally.
    Usage: GET /api/stock/AAPL  or  GET /api/stock/TCS  or  GET /api/stock/BTC
    """
    try:
        data = get_stock_price(symbol)
        # Also get 5-day trend
        history = get_price_history(symbol, "5d")
        if history.get('success'):
            data['trend_5d'] = history['trend']
            data['change_5d_pct'] = history['total_change_pct']
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# NEW: FUNDAMENTALS
# ============================================================================
@app.route('/api/fundamentals/<symbol>', methods=['GET'])
def fundamentals(symbol):
    """
    Full fundamental analysis for any stock.
    Usage: GET /api/fundamentals/MSFT
    """
    try:
        data = get_stock_fundamentals(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# NEW: ANALYST RECOMMENDATIONS
# ============================================================================
@app.route('/api/recommendations/<symbol>', methods=['GET'])
def recommendations(symbol):
    """
    Analyst recommendations and target prices.
    Usage: GET /api/recommendations/TSLA
    """
    try:
        data = get_analyst_recommendations(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# NEW: TECHNICAL INDICATORS
# ============================================================================
@app.route('/api/technicals/<symbol>', methods=['GET'])
def technicals(symbol):
    """
    Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages.
    Usage: GET /api/technicals/RELIANCE
    """
    try:
        data = get_technical_indicators(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# NEW: COMPARE STOCKS
# ============================================================================
@app.route('/api/compare', methods=['POST'])
def compare():
    """
    Compare 2+ stocks head-to-head.
    Usage: POST /api/compare  { "symbols": ["GOOGL", "MSFT", "AMZN"] }
    """
    try:
        data = request.json
        symbols = data.get('symbols', [])

        if len(symbols) < 2:
            return jsonify({"error": "Need at least 2 symbols to compare"}), 400

        result = compare_stocks(symbols)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# RUN SERVER
# ============================================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌐 MarketMind ALL-ROUNDER API running at http://localhost:5001")
    print("="*60)
    print("\n📡 Endpoints:")
    print("   POST /api/analyze             → Smart Query Routing")
    print("   GET  /api/stock/<symbol>      → Quick Price Lookup")
    print("   GET  /api/fundamentals/<sym>  → Fundamentals")
    print("   GET  /api/recommendations/<s> → Analyst Ratings")
    print("   GET  /api/technicals/<sym>    → Technical Analysis")
    print("   POST /api/compare             → Compare Stocks")
    print("   GET  /api/morning-briefing    → Morning Briefing")
    print("   GET  /api/market-data         → Live Ticker Data")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
