"""
Flask API for MarketMind Research Agent — LangGraph Edition
=============================================================
Professional REST API with LangGraph-powered Research Agent

Endpoints:
  GET  /api/health              → Health check
  GET  /api/portfolio           → Get user portfolio
  POST /api/portfolio           → Update portfolio
  GET  /api/market-data         → Live market ticker data
  POST /api/analyze             → Smart research (Quick/Deep mode)
  GET  /api/morning-briefing    → Morning portfolio briefing
  GET  /api/stock/<symbol>      → Quick stock price lookup
  GET  /api/fundamentals/<sym>  → Fundamental analysis data
  GET  /api/recommendations/<s> → Analyst recommendations
  GET  /api/technicals/<symbol> → Technical indicators
  POST /api/compare             → Compare 2+ stocks
  GET  /api/preferences         → Get user memory/preferences (NEW)
  POST /api/preferences         → Update user preferences (NEW)
  GET  /api/suggest             → Suggest next analysis (NEW)
  GET  /api/history             → Get conversation history (NEW)
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

from research_agent import ResearchAgent
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

# Initialize the LangGraph Research Agent
print("🚀 Starting MarketMind Research Agent API (LangGraph Edition)...")
agent = ResearchAgent()
print("✅ API Ready! (14 Routes Active)")

# ============================================================================
# HEALTH CHECK
# ============================================================================
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "engine": "LangGraph Research Agent",
        "model": "gemini-2.5-flash",
        "version": "3.0",
        "modes": ["quick", "deep"],
        "features": ["memory", "contradiction_detection", "confidence_scoring",
                      "follow_up_support", "research_cache", "bull_bear_thesis"],
        "routes": ["STOCK_PRICE", "RECOMMENDATIONS", "FUNDAMENTALS", "COMPARISON",
                    "TECHNICALS", "NEWS_SEARCH", "PORTFOLIO", "DISCOVERY",
                    "GENERAL_MARKET", "CONVERSATIONAL", "SUGGESTION"],
        "coverage": ["Indian (NSE)", "US (NYSE/NASDAQ)", "Crypto", "Commodities"],
    })

# ============================================================================
# PORTFOLIO CRUD
# ============================================================================
@app.route('/api/portfolio', methods=['GET'])
def get_portfolio():
    from user_config import load_portfolio
    data = load_portfolio()
    return jsonify({
        "stocks": data.get("stocks", []),
        "sectors": data.get("sectors", []),
        "profile": data.get("profile", {})
    })

@app.route('/api/portfolio', methods=['POST'])
def save_portfolio():
    try:
        from user_config import save_portfolio_data
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        if "stocks" not in data or "profile" not in data:
            return jsonify({"error": "Missing stocks or profile"}), 400

        success = save_portfolio_data(data)
        if success:
            # Also sync preferences to memory
            profile = data.get("profile", {})
            agent.update_preferences({
                "risk_tolerance": profile.get("risk_tolerance", "moderate"),
                "investment_horizon": profile.get("investment_horizon", "long-term"),
                "sectors": data.get("sectors", []),
            })
            return jsonify({"success": True, "message": "Portfolio & memory updated!"})
        else:
            return jsonify({"error": "Failed to save data"}), 500
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# MARKET DATA (Ticker)
# ============================================================================
@app.route('/api/market-data', methods=['GET'])
def get_market_data():
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
# MAIN ANALYSIS ENDPOINT (LangGraph Research Agent)
# ============================================================================
@app.route('/api/analyze', methods=['POST'])
def analyze():
    """
    Main research endpoint.
    Body: { "query": "...", "mode": "quick|deep|auto" }
    """
    data = request.json
    query = data.get('query', '')
    mode = data.get('mode', 'auto')

    if not query:
        return jsonify({"error": "Query is required"}), 400

    try:
        result = agent.analyze(query, mode=mode)

        return jsonify({
            "query": query,
            "report": result.get("report", ""),
            "route": result.get("route", "GENERAL"),
            "route_label": result.get("route_label", ""),
            "route_emoji": result.get("route_emoji", "🤖"),
            "mode": result.get("mode", mode),
            "confidence": result.get("confidence", "MEDIUM"),
            "confidence_reasons": result.get("confidence_reasons", []),
            "symbols": result.get("symbols", []),
            "contradictions": result.get("contradictions", []),
            "is_follow_up": result.get("is_follow_up", False),
            "elapsed": result.get("elapsed", 0),
            "sources_count": result.get("sources_count", 0),
            "intent": result.get("intent", ""),
            "success": result.get("success", True),
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# MORNING BRIEFING
# ============================================================================
@app.route('/api/morning-briefing', methods=['GET'])
def morning_briefing():
    try:
        result = agent.morning_briefing()
        return jsonify({
            "report": result.get("report", ""),
            "route": "PORTFOLIO",
            "route_label": "Morning Briefing",
            "route_emoji": "☀️",
            "confidence": result.get("confidence", "MEDIUM"),
            "success": True
        })
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# QUICK STOCK PRICE LOOKUP
# ============================================================================
@app.route('/api/stock/<symbol>', methods=['GET'])
def stock_price(symbol):
    try:
        data = get_stock_price(symbol)
        history = get_price_history(symbol, "5d")
        if history.get('success'):
            data['trend_5d'] = history['trend']
            data['change_5d_pct'] = history['total_change_pct']
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# FUNDAMENTALS
# ============================================================================
@app.route('/api/fundamentals/<symbol>', methods=['GET'])
def fundamentals(symbol):
    try:
        data = get_stock_fundamentals(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# ANALYST RECOMMENDATIONS
# ============================================================================
@app.route('/api/recommendations/<symbol>', methods=['GET'])
def recommendations(symbol):
    try:
        data = get_analyst_recommendations(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# TECHNICAL INDICATORS
# ============================================================================
@app.route('/api/technicals/<symbol>', methods=['GET'])
def technicals(symbol):
    try:
        data = get_technical_indicators(symbol)
        return jsonify(data)
    except Exception as e:
        return jsonify({"symbol": symbol, "error": str(e), "success": False}), 500

# ============================================================================
# COMPARE STOCKS
# ============================================================================
@app.route('/api/compare', methods=['POST'])
def compare():
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
# NEW: USER PREFERENCES (Memory)
# ============================================================================
@app.route('/api/preferences', methods=['GET'])
def get_preferences():
    """Get user's financial memory preferences."""
    try:
        prefs = agent.get_preferences()
        return jsonify({"preferences": prefs, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

@app.route('/api/preferences', methods=['POST'])
def update_preferences():
    """Update user's financial memory preferences."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
        agent.update_preferences(data)
        return jsonify({"success": True, "message": "Preferences saved to memory!", "preferences": agent.get_preferences()})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# NEW: SUGGEST NEXT ANALYSIS
# ============================================================================
@app.route('/api/suggest', methods=['GET'])
def suggest_next():
    """Based on past research patterns, suggest what to analyze next."""
    try:
        suggestion = agent.suggest_next()
        return jsonify({"suggestion": suggestion, "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# NEW: CONVERSATION HISTORY
# ============================================================================
@app.route('/api/history', methods=['GET'])
def get_history():
    """Get recent conversation history."""
    try:
        memory = agent.memory
        history = memory.conversation_history[-20:]
        return jsonify({"history": history, "count": len(history), "success": True})
    except Exception as e:
        return jsonify({"error": str(e), "success": False}), 500

# ============================================================================
# RUN SERVER
# ============================================================================
if __name__ == '__main__':
    print("\n" + "="*60)
    print("🌐 MarketMind Research Agent API (LangGraph)")
    print("   Running at http://localhost:5001")
    print("="*60)
    print("\n📡 Core Endpoints:")
    print("   POST /api/analyze             → Research Agent (Quick/Deep)")
    print("   GET  /api/stock/<symbol>      → Quick Price Lookup")
    print("   GET  /api/fundamentals/<sym>  → Fundamentals")
    print("   GET  /api/recommendations/<s> → Analyst Ratings")
    print("   GET  /api/technicals/<sym>    → Technical Analysis")
    print("   POST /api/compare             → Compare Stocks")
    print("\n🧠 Memory Endpoints:")
    print("   GET  /api/preferences         → Get Memory/Preferences")
    print("   POST /api/preferences         → Update Preferences")
    print("   GET  /api/suggest             → Suggest Next Analysis")
    print("   GET  /api/history             → Conversation History")
    print("\n📊 Portfolio Endpoints:")
    print("   GET  /api/portfolio           → Get Portfolio")
    print("   POST /api/portfolio           → Update Portfolio")
    print("   GET  /api/market-data         → Live Ticker Data")
    print("   GET  /api/morning-briefing    → Morning Briefing")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=5001, debug=False)
