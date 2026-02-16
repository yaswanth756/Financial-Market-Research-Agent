"""
User Configuration - Your Personal Portfolio
=============================================
NOW DYNAMIC: Reads from portfolio.json
"""

import json
import os

# Load .env if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PORTFOLIO_FILE = "portfolio.json"

# Qdrant Configuration (loaded from .env)
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_API_KEY = os.environ.get("QDRANT_API_KEY", "")
QDRANT_COLLECTION = "financial_market_news"

def load_portfolio():
    """Load portfolio from JSON file"""
    try:
        with open(PORTFOLIO_FILE, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ Error loading portfolio: {e}")
        return {
            "stocks": [],
            "sectors": [],
            "profile": {
                "risk_tolerance": "moderate",
                "investment_horizon": "long-term",
                "focus_areas": []
            }
        }

def save_portfolio_data(data):
    """Save updated portfolio to JSON"""
    try:
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"❌ Error saving portfolio: {e}")
        return False

# Initial Load
_data = load_portfolio()
PORTFOLIO = {
    "stocks": _data.get("stocks", []),
    "sectors": _data.get("sectors", []),
    "indices": ["NIFTY50", "SENSEX"]
}
USER_PROFILE = _data.get("profile", {})

# Helper functions for compatibility
def get_portfolio_symbols():
    data = load_portfolio()
    return [s["symbol"] for s in data.get("stocks", [])]

def is_relevant_to_portfolio(text: str) -> tuple:
    """Dynamic relevance check"""
    data = load_portfolio()
    stocks = data.get("stocks", [])
    
    text_lower = text.lower()
    matched = []
    score = 0.0
    
    for stock in stocks:
        if stock["symbol"].lower() in text_lower or stock["name"].lower() in text_lower:
            matched.append(f"📈 {stock['symbol']}")
            score += 1.0
            
    return (score > 0, score, matched)
