"""
The Analyst Layer - Powered by Gemini 2.5

Phase 9: PROFESSIONAL ALL-ROUNDER QUERY ROUTING

10 Smart Routes:
- Route 1: STOCK_PRICE       → "What's the price of Apple?"
- Route 2: RECOMMENDATIONS   → "Show analyst recommendations for Tesla"
- Route 3: FUNDAMENTALS      → "What are the fundamentals of Microsoft?"
- Route 4: COMPARISON        → "Compare Google and Amazon stocks"
- Route 5: TECHNICALS        → "Technical analysis of Reliance"
- Route 6: NEWS_SEARCH       → "Latest news about cryptocurrency"
- Route 7: PORTFOLIO         → "How is my portfolio doing?"
- Route 8: DISCOVERY         → "Should I buy Zomato?"
- Route 9: GENERAL_MARKET    → "How is the market today?"
- Route 10: CONVERSATIONAL   → Greetings, thanks, etc.

Supports: Indian (NSE) + US (NYSE/NASDAQ) + Crypto + Commodities
"""

import warnings
warnings.filterwarnings('ignore')
# Suppress specific warning from duckduckgo_search about package rename
warnings.filterwarnings('ignore', category=RuntimeWarning, module='duckduckgo_search')

import os
import ssl
import json
import re
import datetime

# === GLOBAL SSL FIX ===
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

from market_tools import (
    get_stock_price,
    get_price_history,
    get_portfolio_snapshot,
    validate_news_vs_price,
    get_analyst_recommendations,
    get_stock_fundamentals,
    compare_stocks,
    get_technical_indicators,
    format_market_context,
    format_stock_detail,
    SYMBOL_MAP,
    _format_currency,
    _format_large_number,
)
from hybrid_search import HybridSearchEngine
from user_config import PORTFOLIO, USER_PROFILE, is_relevant_to_portfolio
from duckduckgo_search import DDGS


# GEMINI 2.5 SETUP


from google import genai
from google.genai import types
import httpx
import time as _time

_original_httpx_client_init = httpx.Client.__init__
def _patched_httpx_init(self, *args, **kwargs):
    kwargs['verify'] = False
    if 'limits' not in kwargs:
        kwargs['limits'] = httpx.Limits(max_connections=20, max_keepalive_connections=5)
    if 'timeout' not in kwargs:
        kwargs['timeout'] = httpx.Timeout(60.0, connect=15.0)
    return _original_httpx_client_init(self, *args, **kwargs)
httpx.Client.__init__ = _patched_httpx_init

_original_async_init = httpx.AsyncClient.__init__
def _patched_async_init(self, *args, **kwargs):
    kwargs['verify'] = False
    if 'limits' not in kwargs:
        kwargs['limits'] = httpx.Limits(max_connections=20, max_keepalive_connections=5)
    if 'timeout' not in kwargs:
        kwargs['timeout'] = httpx.Timeout(60.0, connect=15.0)
    return _original_async_init(self, *args, **kwargs)
httpx.AsyncClient.__init__ = _patched_async_init

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================================
# GLOBAL STOCK NAME → SYMBOL RESOLVER
# ============================================================================

STOCK_NAME_MAP = {
    # Indian - New-Age Tech
    "zomato": "ZOMATO", "swiggy": "SWIGGY", "paytm": "PAYTM", "one97": "PAYTM",
    "nykaa": "NYKAA", "policybazaar": "POLICYBZR", "delhivery": "DELHIVERY",
    "irctc": "IRCTC", "easemytrip": "EASEMYTRIP", "jio financial": "JIOFIN",
    "jio": "JIOFIN",
    # Indian - IT
    "tcs": "TCS", "infosys": "INFY", "infy": "INFY", "wipro": "WIPRO",
    "hcl tech": "HCLTECH", "hcltech": "HCLTECH", "tech mahindra": "TECHM",
    "techm": "TECHM", "persistent": "PERSISTENT", "coforge": "COFORGE",
    "ltimindtree": "LTIM",
    # Indian - Banking
    "hdfc bank": "HDFCBANK", "hdfcbank": "HDFCBANK", "icici bank": "ICICIBANK",
    "icicibank": "ICICIBANK", "sbi": "SBIN", "kotak": "KOTAKBANK",
    "axis bank": "AXISBANK", "indusind": "INDUSINDBK", "federal bank": "FEDERALBNK",
    "bandhan bank": "BANDHANBNK", "idfc first": "IDFCFIRSTB",
    # Indian - Energy / Conglomerate
    "reliance": "RELIANCE", "ril": "RELIANCE", "ongc": "ONGC", "bpcl": "BPCL",
    "ntpc": "NTPC", "power grid": "POWERGRID", "tata power": "TATAPOWER",
    "adani green": "ADANIGREEN", "adani enterprises": "ADANIENT",
    "adani ports": "ADANIPORTS", "adani": "ADANIENT",
    # Indian - Large Caps
    "bharti airtel": "BHARTIARTL", "airtel": "BHARTIARTL",
    "itc": "ITC", "hul": "HINDUNILVR", "hindustan unilever": "HINDUNILVR",
    "maruti": "MARUTI", "tata motors": "TATAMOTORS",
    "bajaj finance": "BAJFINANCE", "asian paints": "ASIANPAINT",
    "sun pharma": "SUNPHARMA", "dr reddy": "DRREDDY", "titan": "TITAN",
    "l&t": "LT", "larsen": "LT",
    "tata steel": "TATASTEEL", "jsw steel": "JSWSTEEL",
    "hindalco": "HINDALCO", "coal india": "COALINDIA",
    "ultratech": "ULTRACEMCO", "cipla": "CIPLA",
    "apollo hospitals": "APOLLOHOSP", "apollo": "APOLLOHOSP",
    "divis lab": "DIVISLAB", "hdfc life": "HDFCLIFE", "sbi life": "SBILIFE",
    "bajaj finserv": "BAJAJFINSV", "mahindra": "M&M", "m&m": "M&M",
    "eicher": "EICHERMOT", "hero motocorp": "HEROMOTOCO",
    "hal": "HAL", "bel": "BEL", "vedanta": "VEDL",

    # ==================== US / GLOBAL STOCKS ====================
    "apple": "AAPL", "aapl": "AAPL",
    "google": "GOOGL", "googl": "GOOGL", "alphabet": "GOOGL",
    "microsoft": "MSFT", "msft": "MSFT",
    "amazon": "AMZN", "amzn": "AMZN",
    "tesla": "TSLA", "tsla": "TSLA",
    "meta": "META", "facebook": "META",
    "nvidia": "NVDA", "nvda": "NVDA",
    "netflix": "NFLX", "nflx": "NFLX",
    "amd": "AMD",
    "intel": "INTC", "intc": "INTC",
    "salesforce": "CRM", "crm": "CRM",
    "oracle": "ORCL", "orcl": "ORCL",
    "paypal": "PYPL", "pypl": "PYPL",
    "disney": "DIS", "dis": "DIS",
    "boeing": "BA",
    "jpmorgan": "JPM", "jp morgan": "JPM", "jpm": "JPM",
    "goldman sachs": "GS", "goldman": "GS",
    "visa": "V",
    "mastercard": "MA",
    "walmart": "WMT", "wmt": "WMT",
    "coca cola": "KO", "coca-cola": "KO", "coke": "KO",
    "pepsi": "PEP", "pepsico": "PEP",
    "pfizer": "PFE",
    "exxon": "XOM", "exxon mobil": "XOM",
    "chevron": "CVX",
    "berkshire": "BRK-B", "berkshire hathaway": "BRK-B",
    "spotify": "SPOT",
    "uber": "UBER",
    "airbnb": "ABNB",
    "snowflake": "SNOW",
    "palantir": "PLTR",
    "coinbase": "COIN",
    "block": "SQ", "square": "SQ",
    "shopify": "SHOP",
    "zoom": "ZM",
    "alibaba": "BABA",
    "tsmc": "TSM",
    "sony": "SONY",
    "nike": "NKE",
    "starbucks": "SBUX",

    # ==================== CRYPTO ====================
    "bitcoin": "BTC", "btc": "BTC",
    "ethereum": "ETH", "eth": "ETH",
    "solana": "SOL", "sol": "SOL",
    "ripple": "XRP", "xrp": "XRP",
    "cardano": "ADA", "ada": "ADA",
    "dogecoin": "DOGE", "doge": "DOGE",
    "polkadot": "DOT",
    "avalanche": "AVAX",
    "polygon": "MATIC",
    "chainlink": "LINK",
    "bnb": "BNB",
    "cryptocurrency": "__CRYPTO_GENERAL__",
    "crypto": "__CRYPTO_GENERAL__",

    # ==================== COMMODITIES ====================
    "gold": "GOLD", "silver": "SILVER",
    "crude oil": "CRUDE", "crude": "CRUDE", "oil": "CRUDE",
    "natural gas": "NATURALGAS",
}




def resolve_stock_from_query(query: str) -> list:
    """
    Extract stock symbols from ANY query — Indian, US, Crypto, Commodities.
    Returns list of resolved symbols.
    """
    q_lower = query.lower()
    found = []

    # 1. Multi-word names first (longest match)
    sorted_names = sorted(STOCK_NAME_MAP.keys(), key=len, reverse=True)
    for name in sorted_names:
        if name in q_lower:
            symbol = STOCK_NAME_MAP[name]
            if symbol not in found and symbol != "__CRYPTO_GENERAL__":
                found.append(symbol)
            q_lower = q_lower.replace(name, " ")

    # 2. Check for uppercase symbols in original query (TCS, AAPL, MSFT, etc.)
    for word in re.findall(r'\b[A-Z][A-Z0-9&\-]{1,15}\b', query):
        if word in SYMBOL_MAP and word not in found:
            found.append(word)

    return found


def is_crypto_query(query: str) -> bool:
    """Check if query is about cryptocurrency in general."""
    crypto_words = ['crypto', 'cryptocurrency', 'bitcoin', 'ethereum', 'blockchain',
                    'defi', 'nft', 'web3', 'altcoin', 'token', 'mining']
    return any(w in query.lower() for w in crypto_words)


# ============================================================================
# QUERY ROUTE DEFINITIONS (10 Professional Routes)
# ============================================================================

class QueryRoute:
    STOCK_PRICE = "STOCK_PRICE"           # Current price lookup
    RECOMMENDATIONS = "RECOMMENDATIONS"    # Analyst recommendations
    FUNDAMENTALS = "FUNDAMENTALS"          # Deep fundamental analysis
    COMPARISON = "COMPARISON"              # Compare 2+ stocks
    TECHNICALS = "TECHNICALS"              # Technical analysis / charts
    NEWS_SEARCH = "NEWS_SEARCH"            # News & information search
    PORTFOLIO = "PORTFOLIO"                # User's portfolio analysis
    DISCOVERY = "DISCOVERY"                # Research stock for potential buy
    GENERAL_MARKET = "GENERAL"             # Broad market / macro
    CONVERSATIONAL = "CHAT"                # Greetings / off-topic


# ============================================================================
# INTENT PATTERNS FOR SMART ROUTING
# ============================================================================

# Each pattern maps to a route — checked in order of specificity
INTENT_PATTERNS = [
    # COMPARISON — must check first (has multiple stocks + compare keywords)
    {
        "route": QueryRoute.COMPARISON,
        "patterns": [
            r'compare\s+.+\s+(and|vs|versus|with)\s+',
            r'(difference|comparison)\s+between\s+',
            r'.+\s+vs\.?\s+.+',
            r'which\s+is\s+better.+\s+(or|vs)\s+',
            r'head\s*to\s*head',
        ],
        "keywords": ['compare', 'comparison', 'versus', 'vs', 'head to head', 'which is better', 'difference between'],
    },
    # STOCK PRICE — direct price lookup
    {
        "route": QueryRoute.STOCK_PRICE,
        "patterns": [
            r"(what'?s|what\s+is|get|show|tell)\s+(the\s+)?(current\s+)?(stock\s+)?(price|value|quote)",
            r'(price|quote)\s+(of|for)\s+',
            r'how\s+much\s+(is|does|are)\s+',
            r'(stock|share)\s+price',
            r'(current|live|today).{0,10}(price|value|trading)',
        ],
        "keywords": ['current price', 'stock price', 'share price', 'price of', 'trading at', 'how much is', 'quote for', 'price today'],
    },
    # RECOMMENDATIONS — analyst ratings
    {
        "route": QueryRoute.RECOMMENDATIONS,
        "patterns": [
            r'(analyst|broker|wall\s*street)\s+(recommend|rating|target|opinion|view|consensus)',
            r'(recommend|rating|target\s+price)\s+(for|of|on)\s+',
            r'(buy|sell|hold)\s+recommend',
            r'(should\s+i\s+buy|is\s+it\s+a\s+good\s+buy)',
            r'(target\s+price|price\s+target)',
            r'(upgrade|downgrade)',
        ],
        "keywords": ['analyst', 'recommendation', 'recommendations', 'target price', 'price target',
                     'rating', 'ratings', 'upgrade', 'downgrade', 'consensus', 'broker', 'wall street',
                     'should i buy', 'good buy', 'worth buying'],
    },
    # FUNDAMENTALS — deep financial analysis
    {
        "route": QueryRoute.FUNDAMENTALS,
        "patterns": [
            r'fundamental(s)?\s+(of|for|analysis)',
            r'(financials|financial\s+data|financial\s+health)\s+(of|for)',
            r'(pe\s+ratio|p/e|market\s+cap|revenue|earnings|profit|margin|debt|balance\s+sheet|income\s+statement)',
            r'(valuation|overvalued|undervalued|fair\s+value)',
            r'(dividend|yield|payout|eps|book\s+value|roe|roa)',
        ],
        "keywords": ['fundamentals', 'fundamental analysis', 'financials', 'financial data',
                     'pe ratio', 'p/e', 'market cap', 'revenue', 'earnings per share', 'eps',
                     'profit margin', 'debt', 'balance sheet', 'income statement', 'valuation',
                     'overvalued', 'undervalued', 'fair value', 'book value', 'roe', 'roa',
                     'dividend yield', 'payout ratio', 'financial health'],
    },
    # TECHNICALS — RSI, moving averages, MACD, charts
    {
        "route": QueryRoute.TECHNICALS,
        "patterns": [
            r'technical\s+(analysis|indicator|signal|chart)',
            r'(rsi|macd|bollinger|moving\s+average|sma|ema|support|resistance)',
            r'(overbought|oversold|momentum|trend\s+analysis)',
            r'(chart\s+pattern|candlestick)',
        ],
        "keywords": ['technical analysis', 'technicals', 'rsi', 'macd', 'bollinger',
                     'moving average', 'sma', 'ema', 'support', 'resistance',
                     'overbought', 'oversold', 'momentum', 'chart', 'trend analysis',
                     'candlestick', 'technical indicators'],
    },
    # NEWS_SEARCH — latest news, events, information
    {
        "route": QueryRoute.NEWS_SEARCH,
        "patterns": [
            r'(latest|recent|breaking|today)\s+(news|update|development|headline)',
            r'news\s+(about|on|for|regarding)',
            r'what\s+(happened|is\s+happening|is\s+going\s+on)',
            r'(tell\s+me\s+about|information\s+about|info\s+on)',
        ],
        "keywords": ['news', 'latest', 'recent news', 'breaking', 'headlines', 'what happened',
                     'update', 'updates', 'developments', 'information about', 'tell me about',
                     'going on with'],
    },
]


def classify_query(query: str, portfolio_symbols: list) -> dict:
    """
    Professional Query Router — classifies intent with 10 routes.
    Uses pattern matching + keyword detection + stock resolution.
    """
    q_lower = query.lower().strip()

    # --- Route: CONVERSATIONAL ---
    greetings = {'hi', 'hello', 'hey', 'thanks', 'thank you', 'good morning',
                 'good evening', 'bye', 'ok', 'okay', 'yo', 'sup'}
    if q_lower in greetings or len(q_lower) < 4:
        return {"route": QueryRoute.CONVERSATIONAL, "symbols": [], "is_summary": False,
                "needs_web": False, "intent": "greeting"}

    # --- Detect mentioned stocks ---
    mentioned_symbols = resolve_stock_from_query(query)
    is_crypto = is_crypto_query(query)

    # --- Check if summary mode ---
    is_summary = any(w in q_lower for w in ['summary', 'brief', 'short', 'quickly', 'summarise', 'summarize'])

    # =========================================================================
    # FORCE WEB TRIGGERS — MUST be checked BEFORE any route returns!
    # THE HARD STUFF — words that Yahoo Finance API does NOT have.
    # If ANY of these appear, we MUST search the web for real answers.
    # =========================================================================
    force_web_triggers = [
        # === Original triggers ===
        'dividend', 'earnings', 'results', 'q1', 'q2', 'q3', 'q4',
        'acquisition', 'merger', 'buyout', 'bonus', 'split', 'rights',
        'target', 'upgrade', 'downgrade', 'ipo', 'launch', 'deal',
        'news', 'latest', 'today', 'recent', 'announce', 'declared',
        'buy', 'sell', 'invest', 'should i',

        # === THE HARD STUFF (Numbers Yahoo doesn't have) ===
        'gnpa', 'nnpa', 'npa', 'gross npa', 'net npa', 'slippage',
        'provision', 'provisions', 'write off', 'write-off', 'writeoff',
        'restructured', 'stressed assets', 'asset quality',
        'segment', 'segment wise', 'segmentwise', 'segment-wise',
        'breakup', 'break up', 'break-up', 'breakdown', 'break down',
        'quarter', 'quarterly', 'qoq', 'q-o-q', 'yoy', 'y-o-y',
        'guidance', 'outlook', 'forecast', 'projection',
        'cost of fund', 'cost of funds', 'nim', 'net interest margin',
        'casa', 'casa ratio', 'credit cost', 'credit growth',
        'loan book', 'loan growth', 'deposit growth', 'advances',
        'aum', 'assets under management',
        'disbursement', 'collection efficiency', 'recovery',

        # === THE HARD STUFF (Reasons — "Why?" questions) ===
        'why', 'reason', 'because', 'due to', 'caused by', 'impact of',
        'how come', 'explain', 'what caused', 'what led to',
        'pressure', 'margin pressure', 'headwind', 'tailwind',
        'concern', 'risk', 'worried', 'fear', 'red flag',
        'miss', 'missed', 'beat', 'surprise', 'disappointing',
        'weak', 'strong', 'robust', 'poor', 'stellar',
        'fallen', 'crashed', 'tanked', 'surged', 'spiked', 'rallied',
        'dropped', 'plunged', 'soared', 'jumped',

        # === THE HARD STUFF (Specific financial deep-dives) ===
        'management commentary', 'concall', 'con call', 'conference call',
        'promoter', 'promoter holding', 'promoter pledge', 'pledge',
        'fii', 'dii', 'fpi', 'institutional', 'bulk deal', 'block deal',
        'insider', 'insider trading', 'insider buying', 'insider selling',
        'order book', 'order win', 'order inflow',
        'capex', 'capacity', 'expansion', 'plant', 'factory',
        'regulation', 'regulatory', 'sebi', 'rbi circular', 'policy change',
        'rating', 'credit rating', 'crisil', 'icra', 'care rating',
        'stake', 'stake sale', 'divestment', 'stake buy',
        'bankruptcy', 'nclt', 'insolvency', 'default',
        'tax', 'gst', 'tax benefit', 'tax impact',
        'subsidy', 'government', 'policy',

        # === THE HARD STUFF (Future / Predictions) ===
        'will', 'going to', 'expected', 'expect', 'prediction',
        'next quarter', 'next year', 'fy25', 'fy26', 'fy27',
        'fy2025', 'fy2026', 'fy2027', '2025', '2026', '2027',
        'future', 'ahead', 'coming', 'upcoming',
    ]
    needs_web = any(t in q_lower for t in force_web_triggers)

    # --- Intent Pattern Matching ---
    matched_route = None
    for intent in INTENT_PATTERNS:
        # Check regex patterns
        for pattern in intent["patterns"]:
            if re.search(pattern, q_lower):
                matched_route = intent["route"]
                break
        if matched_route:
            break
        # Check keywords
        for kw in intent["keywords"]:
            if kw in q_lower:
                matched_route = intent["route"]
                break
        if matched_route:
            break

    # --- COMPARISON route needs 2+ symbols ---
    if matched_route == QueryRoute.COMPARISON:
        if len(mentioned_symbols) >= 2:
            return {
                "route": QueryRoute.COMPARISON,
                "symbols": mentioned_symbols,
                "is_summary": is_summary,
                "needs_web": needs_web,
                "intent": "compare_stocks",
            }
        elif len(mentioned_symbols) == 1:
            matched_route = QueryRoute.STOCK_PRICE

    # --- STOCK_PRICE route ---
    if matched_route == QueryRoute.STOCK_PRICE and mentioned_symbols:
        return {
            "route": QueryRoute.STOCK_PRICE,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": needs_web,
            "intent": "price_lookup",
        }

    # --- RECOMMENDATIONS route ---
    if matched_route == QueryRoute.RECOMMENDATIONS and mentioned_symbols:
        return {
            "route": QueryRoute.RECOMMENDATIONS,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "analyst_recommendations",
        }

    # --- FUNDAMENTALS route ---
    # ALWAYS do web search for fundamentals — Yahoo API alone misses
    # GNPA/NPA (banks), quarterly results, real ROE, segment data, etc.
    if matched_route == QueryRoute.FUNDAMENTALS and mentioned_symbols:
        return {
            "route": QueryRoute.FUNDAMENTALS,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "fundamental_analysis",
        }

    # --- TECHNICALS route ---
    if matched_route == QueryRoute.TECHNICALS and mentioned_symbols:
        return {
            "route": QueryRoute.TECHNICALS,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": needs_web,
            "intent": "technical_analysis",
        }

    # --- NEWS_SEARCH route ---
    if matched_route == QueryRoute.NEWS_SEARCH:
        return {
            "route": QueryRoute.NEWS_SEARCH,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "news_search",
            "is_crypto": is_crypto,
        }

    # --- If intent matched but no symbol → still use the route for general queries ---
    if matched_route == QueryRoute.STOCK_PRICE and not mentioned_symbols:
        matched_route = None
    if matched_route == QueryRoute.RECOMMENDATIONS and not mentioned_symbols:
        matched_route = QueryRoute.NEWS_SEARCH
    if matched_route == QueryRoute.FUNDAMENTALS and not mentioned_symbols:
        matched_route = None
    if matched_route == QueryRoute.TECHNICALS and not mentioned_symbols:
        matched_route = None

    # Update needs_web for NEWS_SEARCH matched route
    needs_web = needs_web or matched_route == QueryRoute.NEWS_SEARCH

    # --- Classify stocks: portfolio vs discovery ---
    portfolio_syms = [s.upper() for s in portfolio_symbols]
    portfolio_mentioned = [s for s in mentioned_symbols if s in portfolio_syms]
    discovery_mentioned = [s for s in mentioned_symbols if s not in portfolio_syms]

    # --- PORTFOLIO route ---
    if not matched_route and not discovery_mentioned and portfolio_mentioned:
        if any(w in q_lower for w in ['my portfolio', 'my stocks', 'my holding', 'portfolio']):
            return {
                "route": QueryRoute.PORTFOLIO,
                "symbols": portfolio_mentioned,
                "is_summary": is_summary,
                "needs_web": needs_web,
                "intent": "portfolio_analysis",
            }
        return {
            "route": QueryRoute.PORTFOLIO,
            "symbols": portfolio_mentioned,
            "is_summary": is_summary,
            "needs_web": needs_web,
            "intent": "portfolio_stock",
        }

    # --- DISCOVERY route (any stock NOT in portfolio) ---
    if not matched_route and discovery_mentioned:
        return {
            "route": QueryRoute.DISCOVERY,
            "symbols": mentioned_symbols,
            "discovery_symbols": discovery_mentioned,
            "portfolio_symbols": portfolio_mentioned,
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "stock_discovery",
        }

    # --- GENERAL MARKET ---
    market_keywords = ['market', 'nifty', 'sensex', 'sector', 'rbi', 'fed', 'inflation',
                       'gdp', 'economy', 'rate', 'index', 'dow', 'nasdaq', 's&p',
                       'bull', 'bear', 'rally', 'crash', 'correction', 'recession',
                       'interest rate', 'monetary policy', 'fiscal']
    if any(w in q_lower for w in market_keywords):
        return {
            "route": QueryRoute.GENERAL_MARKET,
            "symbols": mentioned_symbols,
            "is_summary": is_summary,
            "needs_web": needs_web,
            "intent": "market_overview",
        }

    # --- Crypto general query ---
    if is_crypto and not mentioned_symbols:
        return {
            "route": QueryRoute.NEWS_SEARCH,
            "symbols": [],
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "crypto_news",
            "is_crypto": True,
        }

    # --- Fallback: if there are symbols, treat as DISCOVERY ---
    if mentioned_symbols:
        return {
            "route": QueryRoute.DISCOVERY,
            "symbols": mentioned_symbols,
            "discovery_symbols": discovery_mentioned or mentioned_symbols,
            "portfolio_symbols": portfolio_mentioned,
            "is_summary": is_summary,
            "needs_web": True,
            "intent": "general_stock_query",
        }

    # --- Fallback: if has web triggers or long query → GENERAL ---
    if needs_web or len(q_lower.split()) > 3:
        return {
            "route": QueryRoute.GENERAL_MARKET,
            "symbols": [],
            "is_summary": is_summary,
            "needs_web": needs_web,
            "intent": "general_finance",
        }

    # --- Final fallback: CONVERSATIONAL ---
    return {
        "route": QueryRoute.CONVERSATIONAL,
        "symbols": [],
        "is_summary": False,
        "needs_web": False,
        "intent": "general_chat",
    }


# ============================================================================
# SYSTEM PROMPTS PER ROUTE
# ============================================================================

STOCK_PRICE_SYSTEM_PROMPT = """You are a professional stock market data analyst.

## GOAL:
Present the stock price data **concisely**. Focus on the numbers.

## FORMAT:
1. **� Price Snapshot**: Current price | Change | Range
2. **� Key Levels**: 52W High/Low status
3. **💡 Quick Take**: 1-sentence observation

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Ultra-concise. No "market is volatile" filler. Just data.
"""

RECOMMENDATIONS_SYSTEM_PROMPT = """You are a senior equity research analyst.

## GOAL:
Summarize analyst ratings and targets.

## FORMAT:
1. **🎯 Consensus**: Buy/Hold/Sell (Count)
2. **💰 Targets**: Mean | High | Low (Upside %)
3. **⚖️ Verdict**: Your 1-sentence takeaway

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Professional, direct. No disclaimers.
"""

FUNDAMENTALS_SYSTEM_PROMPT = """You are a fundamental equity analyst.

## GOAL:
Assess stock health based on key metrics. Cross-reference API data with web sources.

## CRITICAL RULES:
- If API shows ROE=0%, ROA=0%, or PEG=0, these are likely DATA ERRORS from Yahoo Finance. Flag them as "Data unavailable" and use web sources instead.
- If web sources provide quarterly results (GNPA, NPA, segment data, actual ROE, earnings), PREFER those over API data.
- Never state "not available in provided data" — if the web sources have it, USE IT.

## FORMAT:
1. **🏢 Profile**: Sector | Industry (1 line)
2. **📊 Valuation**: PE | Fwd PE | PEG | P/B (Cheap/Expensive?)
3. **💰 Profitability**: Margins | Growth | ROE
4. **🏥 Business Health & Specifics**: Key metrics from web sources (GNPA/NPA for banks, segment data, quarterly trends, management commentary — whatever is available)
5. **⚖️ Verdict**: UNDERVALUED / FAIR / OVERVALUED (1 sentence reasoning)

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE + Web Intelligence
## STYLE: Data-heavy, minimal text. Use actual numbers from sources.
"""

COMPARISON_SYSTEM_PROMPT = """You are a comparative equity analyst.

## GOAL:
Compare stocks and pick a winner.

## FORMAT:
1. **📊 Head-to-Head**: Key metric comparison (Price, PE, Growth, Margins)
2. **🏆 Winner**: [STOCK NAME]
3. **💡 Why**: 1-2 bullet points on why it wins.

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: direct comparison. No hedging.
"""

TECHNICALS_SYSTEM_PROMPT = """You are a technical analysis expert.

## GOAL:
Identify trends and trading signals.

## FORMAT:
1. **📈 Trend**: Bullish/Bearish/Neutral
2. **📊 Indicators**: RSI | MACD | Moving Avgs
3. **🎯 Levels**: Support | Resistance
4. **⚖️ Action**: BUY / SELL / WAIT (Entry/Exit levels)

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Technical terms only. Short sentences.
"""

NEWS_SEARCH_SYSTEM_PROMPT = """You are a financial news analyst.

## GOAL:
Brief the user on key developments.

## FORMAT:
1. **📰 Headlines**: Top 3 news items (1 line each)
2. **💡 Impact**: Bullish/Bearish for related stocks
3. **⚖️ Takeaway**: What to do (1 sentence)

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: News-ticker style. Fast, factual.
"""

PORTFOLIO_SYSTEM_PROMPT = """You are a senior portfolio manager.

## GOAL:
Update the user on their holdings.

## FORMAT:
1. **📊 Performance**: Key movers today
2. **📰 News**: Relevant updates (if any)
3. **⚖️ Advice**: Hold/Buy/Sell adjustments (if needed)

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Executive summary. No fluff.
"""

DISCOVERY_SYSTEM_PROMPT = """You are a senior equity analyst.

## GOAL:
Evaluate a new stock opportunity.

## FORMAT:
1. **📊 Snapshot**: Price | PE | 52W Range
2. **� Drivers**: Why is it moving? (1-2 bullets)
3. **⚖️ Verdict**: BUY / WATCH / AVOID (1 sentence reasoning)

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Decisive. Professional.
"""

GENERAL_MARKET_SYSTEM_PROMPT = """You are a macro strategist.

## GOAL:
Summarize market status.

## FORMAT:
1. **🌍 Market Pulse**: Trend | Key Indices
2. **📰 Drivers**: What's moving the market (1-2 bullets)
3. **⚖️ Outlook**: Bullish/Bearish short-term

## CLIENT: Portfolio: {portfolio_str} | Data: LIVE
## STYLE: Macro-focused, concise.
"""

SUMMARY_SYSTEM_PROMPT = """You are a Senior Financial Analyst. Return a **CONCISE EXECUTIVE SUMMARY** (Max 200 words).

## FORMAT:
1. **📉 Market Pulse**: 1 sentence on price action.
2. **📰 Key Driver**: 1-2 bullet points.
3. **⚖️ Verdict**: [BULLISH/BEARISH/NEUTRAL] + Action.

## CONTEXT: Portfolio: {portfolio_str} | Date: {current_date}
"""


# ============================================================================
# ROUTE → EMOJI MAP
# ============================================================================
ROUTE_EMOJI = {
    QueryRoute.STOCK_PRICE: "💹",
    QueryRoute.RECOMMENDATIONS: "🎯",
    QueryRoute.FUNDAMENTALS: "📊",
    QueryRoute.COMPARISON: "⚖️",
    QueryRoute.TECHNICALS: "📈",
    QueryRoute.NEWS_SEARCH: "📰",
    QueryRoute.PORTFOLIO: "💼",
    QueryRoute.DISCOVERY: "🔍",
    QueryRoute.GENERAL_MARKET: "🌐",
    QueryRoute.CONVERSATIONAL: "💬",
}

ROUTE_LABEL = {
    QueryRoute.STOCK_PRICE: "Stock Price",
    QueryRoute.RECOMMENDATIONS: "Analyst Recommendations",
    QueryRoute.FUNDAMENTALS: "Fundamental Analysis",
    QueryRoute.COMPARISON: "Stock Comparison",
    QueryRoute.TECHNICALS: "Technical Analysis",
    QueryRoute.NEWS_SEARCH: "News & Research",
    QueryRoute.PORTFOLIO: "Portfolio Analysis",
    QueryRoute.DISCOVERY: "Stock Discovery",
    QueryRoute.GENERAL_MARKET: "Market Overview",
    QueryRoute.CONVERSATIONAL: "Chat",
}


# ============================================================================
# THE GEMINI-POWERED ALL-ROUNDER ANALYST
# ============================================================================

class GeminiAnalyst:
    """
    Professional All-Rounder Financial Agent with 10 smart query routes.
    Handles ANY financial query — stocks, crypto, fundamentals, technicals,
    comparisons, news, recommendations, portfolio, and market analysis.
    """

    def __init__(self):
        print("\n" + "="*70)
        print("🤖 Initializing MarketMind ALL-ROUNDER Agent (10-Route Engine)")
        print("="*70)

        self.search_engine = HybridSearchEngine()
        self.portfolio = PORTFOLIO
        self.profile = USER_PROFILE
        self.model = "gemini-2.5-flash"
        self.portfolio_symbols = [s['symbol'].upper() for s in self.portfolio['stocks']]

        print(f"📊 Portfolio: {self.portfolio_symbols}")
        print(f"👤 Profile: {self.profile.get('risk_tolerance', 'moderate')} risk")
        print(f"🧭 Routes: PRICE | RECS | FUNDAMENTALS | COMPARE | TECHNICALS | NEWS | PORTFOLIO | DISCOVERY | MARKET | CHAT")
        print(f"🌍 Coverage: Indian (NSE) + US (NYSE/NASDAQ) + Crypto + Commodities")
        print("="*70 + "\n")

    def _get_portfolio_string(self) -> str:
        stocks = [f"{s['symbol']} ({s['sector']})" for s in self.portfolio['stocks']]
        return ", ".join(stocks)

    def _get_market_snapshot(self, extra_symbols: list = None) -> str:
        symbols = [s['symbol'] for s in self.portfolio['stocks']]
        if extra_symbols:
            for sym in extra_symbols:
                if sym not in symbols:
                    symbols.append(sym)
        return format_market_context(symbols)

    def _get_stock_detail_context(self, symbols: list) -> str:
        """Rich detail for specific stocks."""
        lines = []
        for sym in symbols:
            lines.append(format_stock_detail(sym))
            # Also get 5-day trend
            hist = get_price_history(sym, "5d")
            if hist.get('success'):
                lines.append(f"   5-Day Trend: {hist['trend']} ({hist['total_change_pct']:+.2f}%)")
            lines.append("")
        return "\n".join(lines)

    def _get_recommendations_context(self, symbols: list) -> str:
        """Format analyst recommendations for LLM."""
        lines = ["## 🎯 ANALYST RECOMMENDATIONS (Live Data)\n"]
        for sym in symbols:
            recs = get_analyst_recommendations(sym)
            if recs.get('success'):
                currency = recs.get('currency', 'USD')
                lines.append(
                    f"**{recs.get('name', sym)}** ({recs['symbol']})\n"
                    f"   Consensus: {recs['consensus']}\n"
                    f"   Analysts: {recs['num_analysts']}\n"
                    f"   Current Price: {_format_currency(recs['current_price'], currency)}\n"
                    f"   Target (Mean): {_format_currency(recs['target_mean'], currency)} | "
                    f"High: {_format_currency(recs['target_high'], currency)} | "
                    f"Low: {_format_currency(recs['target_low'], currency)}\n"
                    f"   Upside/Downside: {recs['upside_pct']:+.1f}%\n"
                )
                if recs.get('recent_recommendations'):
                    lines.append("   Recent Actions:")
                    for r in recs['recent_recommendations']:
                        lines.append(f"   - {r['firm']}: {r['grade']} ({r['action']})")
                lines.append("")
            else:
                lines.append(f"⚠️ {sym}: Could not fetch recommendations\n")
        return "\n".join(lines)

    def _get_fundamentals_context(self, symbols: list) -> str:
        """Format fundamentals for LLM."""
        lines = ["## 📊 FUNDAMENTAL DATA (Live)\n"]
        for sym in symbols:
            f = get_stock_fundamentals(sym)
            if f.get('success'):
                lines.append(
                    f"**{f.get('name', sym)}** ({f['symbol']}) — {f['sector']} / {f['industry']}\n"
                    f"   Description: {f['description'][:200]}...\n"
                    f"   Price: {_format_currency(f['current_price'], f['currency'])} | "
                    f"52W: {_format_currency(f['52_week_low'], f['currency'])} - {_format_currency(f['52_week_high'], f['currency'])}\n"
                    f"   50D Avg: {_format_currency(f['50_day_avg'], f['currency'])} | "
                    f"200D Avg: {_format_currency(f['200_day_avg'], f['currency'])} | Beta: {f['beta']}\n"
                    f"\n   VALUATION:\n"
                    f"   MCap: {f['valuation']['market_cap_formatted']} | PE: {f['valuation']['trailing_pe']} | "
                    f"Fwd PE: {f['valuation']['forward_pe']} | PEG: {f['valuation']['peg_ratio']}\n"
                    f"   P/B: {f['valuation']['price_to_book']} | P/S: {f['valuation']['price_to_sales']} | "
                    f"EV/EBITDA: {f['valuation']['ev_to_ebitda']}\n"
                    f"\n   PROFITABILITY:\n"
                    f"   Revenue: {f['profitability']['revenue_formatted']} (Growth: {f['profitability']['revenue_growth']}%)\n"
                    f"   Gross Margin: {f['profitability']['gross_margins']}% | "
                    f"Op Margin: {f['profitability']['operating_margins']}% | "
                    f"Net Margin: {f['profitability']['profit_margins']}%\n"
                    f"   EPS: {f['profitability']['eps_trailing']} (Fwd: {f['profitability']['eps_forward']}) | "
                    f"Earnings Growth: {f['profitability']['earnings_growth']}%\n"
                    f"\n   BALANCE SHEET:\n"
                    f"   Cash: {f['balance_sheet']['total_cash_formatted']} | "
                    f"Debt: {f['balance_sheet']['total_debt_formatted']} | "
                    f"D/E: {f['balance_sheet']['debt_to_equity']}\n"
                    f"   ROE: {f['balance_sheet']['return_on_equity']}% | "
                    f"ROA: {f['balance_sheet']['return_on_assets']}% | "
                    f"Current Ratio: {f['balance_sheet']['current_ratio']}\n"
                    f"\n   DIVIDENDS:\n"
                    f"   Yield: {f['dividends']['dividend_yield']}% | "
                    f"Payout: {f['dividends']['payout_ratio']}% | "
                    f"5Y Avg Yield: {f['dividends']['five_year_avg_yield']}%\n"
                    f"\n   OWNERSHIP:\n"
                    f"   Insiders: {f['shares']['held_by_insiders']}% | "
                    f"Institutions: {f['shares']['held_by_institutions']}% | "
                    f"Short Ratio: {f['shares']['short_ratio']}\n"
                )
            else:
                lines.append(f"⚠️ {sym}: Could not fetch fundamentals\n")
        return "\n".join(lines)

    def _get_comparison_context(self, symbols: list) -> str:
        """Format comparison for LLM."""
        comp = compare_stocks(symbols)
        if not comp.get('success'):
            return "⚠️ Could not generate comparison"

        lines = ["## ⚖️ HEAD-TO-HEAD COMPARISON (Live Data)\n"]
        for sym, data in comp['comparison'].items():
            if 'error' in data:
                lines.append(f"⚠️ {sym}: {data['error']}")
                continue
            currency = data.get('currency', 'USD')
            lines.append(
                f"**{data['name']}** ({sym})\n"
                f"   Price: {_format_currency(data['price'], currency)} ({data['change_pct']:+.2f}%)\n"
                f"   MCap: {data['market_cap']} | PE: {data['pe_ratio']} | Fwd PE: {data['forward_pe']}\n"
                f"   Revenue: {data['revenue']} | Growth: {data['revenue_growth']}%\n"
                f"   Profit Margin: {data['profit_margin']}% | Op Margin: {data['operating_margin']}%\n"
                f"   ROE: {data['roe']}% | D/E: {data['debt_to_equity']} | Beta: {data['beta']}\n"
                f"   Div Yield: {data['dividend_yield']}%\n"
                f"   52W: {_format_currency(data['52w_low'], currency)} - {_format_currency(data['52w_high'], currency)}\n"
            )
        return "\n".join(lines)

    def _get_technicals_context(self, symbols: list) -> str:
        """Format technical indicators for LLM."""
        lines = ["## 📈 TECHNICAL INDICATORS (Calculated from 3-month data)\n"]
        for sym in symbols:
            tech = get_technical_indicators(sym)
            if tech.get('success'):
                lines.append(
                    f"**{sym}** — Overall: {tech['overall_signal']}\n"
                    f"   Price: {tech['current_price']}\n"
                    f"   RSI(14): {tech['rsi_14']}\n"
                    f"   SMA(20): {tech['sma_20']} | SMA(50): {tech['sma_50']}\n"
                    f"   EMA(12): {tech['ema_12']} | EMA(26): {tech['ema_26']}\n"
                    f"   MACD: {tech['macd_line']} | Signal: {tech['signal_line']} | Hist: {tech['macd_histogram']}\n"
                    f"   Bollinger: Upper={tech['bollinger_upper']} | Mid={tech['bollinger_mid']} | Lower={tech['bollinger_lower']}\n"
                    f"\n   SIGNALS:\n"
                )
                for s in tech['signals']:
                    lines.append(f"   {s}")
                lines.append("")
            else:
                lines.append(f"⚠️ {sym}: {tech.get('error', 'Technical data unavailable')}\n")
        return "\n".join(lines)

    def _perform_deep_search(self, query: str, symbols: list = None) -> list:
        """
        SMART Web Search — The Brain v2.
        Detects WHAT TYPE of question you're asking and builds the perfect search query.

        Types:
        - NUMBERS:  "What is the GNPA?"      → adds "percentage number data"
        - REASONS:  "Why is profit down?"     → adds "reason breakdown analysis"
        - FUTURE:   "Will it go up?"          → adds "outlook forecast guidance"
        - SEGMENT:  "Segment wise breakup"    → adds "segment revenue breakup quarterly"
        - RESULTS:  "Q3 results"              → adds "quarter net profit revenue reported"
        - COMPARE:  "NPA vs last quarter"     → adds "qoq yoy comparison trend"
        """
        q_lower = query.lower()
        current_year = datetime.datetime.now().year

        # ============================================================
        # STEP A: Extract stock names & meaningful words
        # ============================================================
        stop_words = {
            'what', 'is', 'the', 'of', 'for', 'a', 'an', 'in', 'on', 'at',
            'to', 'and', 'or', 'how', 'why', 'when', 'where', 'which',
            'tell', 'me', 'show', 'get', 'give', 'about', 'please',
            'can', 'you', 'does', 'did', 'do', 'are', 'was', 'were',
            'will', 'would', 'could', 'should', 'latest', 'current',
            'today', 'now', 'recent', 'its', 'it', 'this', 'that',
            'has', 'have', 'had', 'been', 'be', 'i', 'my', 'any',
            'there', 'their', 'some', 'also', 'much', 'many',
        }

        # Get meaningful words from query
        words = re.findall(r'[a-zA-Z0-9&]+', query)
        meaningful = [w for w in words if w.lower() not in stop_words and len(w) > 1]

        # Add stock symbols
        if symbols:
            for sym in symbols:
                if sym not in meaningful:
                    meaningful.insert(0, sym)

        # Base search = stock name + meaningful keywords
        search_query = " ".join(meaningful) if meaningful else query

        # Always add "stock" context if we have symbols
        if symbols and "stock" not in search_query.lower():
            search_query = f"{symbols[0]} stock {search_query}"

        # ============================================================
        # STEP B: Detect question TYPE and add MAGIC WORDS
        # ============================================================

        # --- TYPE 1: NUMBERS (What is the GNPA? NPA ratio? Credit cost?) ---
        number_words = ['gnpa', 'nnpa', 'npa', 'ratio', 'percentage', 'number',
                        'how much', 'what is the', 'credit cost', 'nim', 'casa',
                        'cost of fund', 'yield', 'slippage', 'provision',
                        'aum', 'disbursement', 'loan book', 'deposit',
                        'collection efficiency', 'recovery rate']
        if any(w in q_lower for w in number_words):
            search_query += f" {current_year} quarter percentage number data reported"
            print(f"   🧠 Query Type: NUMBERS → Adding data keywords")

        # --- TYPE 2: REASONS (Why profit down? What caused the fall?) ---
        reason_words = ['why', 'reason', 'because', 'due to', 'caused',
                        'how come', 'explain', 'what caused', 'what led',
                        'impact', 'pressure', 'headwind', 'concern',
                        'disappointing', 'miss', 'missed', 'weak', 'poor',
                        'fallen', 'crashed', 'tanked', 'dropped', 'plunged']
        if any(w in q_lower for w in reason_words):
            search_query += f" {current_year} reason breakdown analysis cause factor"
            print(f"   🧠 Query Type: REASONS → Adding cause keywords")

        # --- TYPE 3: SEGMENT (Segment wise? Breakup? Which segment?) ---
        segment_words = ['segment', 'breakup', 'break up', 'breakdown',
                         'break down', 'segment wise', 'which segment',
                         'business wise', 'division', 'vertical']
        if any(w in q_lower for w in segment_words):
            search_query += f" {current_year} segment wise revenue profit breakup quarterly results"
            print(f"   🧠 Query Type: SEGMENT → Adding breakup keywords")

        # --- TYPE 4: QUARTERLY RESULTS (Q1/Q2/Q3/Q4 results?) ---
        result_words = ['q1', 'q2', 'q3', 'q4', 'quarter', 'quarterly',
                        'results', 'earnings', 'reported', 'announced']
        if any(w in q_lower for w in result_words):
            search_query += f" {current_year} net profit revenue PAT reported quarter results"
            print(f"   🧠 Query Type: RESULTS → Adding earnings keywords")

        # --- TYPE 5: FUTURE / PREDICTION (Will it go up? Outlook?) ---
        future_words = ['will', 'going to', 'expected', 'expect', 'prediction',
                        'forecast', 'outlook', 'guidance', 'ahead', 'next quarter',
                        'next year', 'target', 'future', 'upcoming']
        if any(w in q_lower for w in future_words):
            search_query += f" {current_year} outlook guidance management forecast target"
            print(f"   🧠 Query Type: FUTURE → Adding outlook keywords")

        # --- TYPE 6: MANAGEMENT / CONCALL ---
        mgmt_words = ['management', 'concall', 'con call', 'conference call',
                       'commentary', 'ceo', 'cfo', 'md said', 'promoter']
        if any(w in q_lower for w in mgmt_words):
            search_query += f" {current_year} management commentary concall highlights key takeaway"
            print(f"   🧠 Query Type: MANAGEMENT → Adding concall keywords")

        # --- TYPE 7: COMPARISON (vs last quarter, YoY, QoQ) ---
        compare_words = ['vs', 'versus', 'compared', 'comparison', 'qoq',
                         'yoy', 'last quarter', 'last year', 'previous']
        if any(w in q_lower for w in compare_words):
            search_query += f" {current_year} qoq yoy comparison trend change"
            print(f"   🧠 Query Type: COMPARISON → Adding trend keywords")

        # --- TYPE 8: ASSET QUALITY (Banking specific) ---
        asset_words = ['asset quality', 'stressed', 'restructured', 'write off',
                       'writeoff', 'write-off', 'default', 'nclt', 'insolvency']
        if any(w in q_lower for w in asset_words):
            search_query += f" {current_year} asset quality stressed book gross net NPA slippage recovery"
            print(f"   🧠 Query Type: ASSET QUALITY → Adding banking keywords")

        # --- TYPE 9: DIVIDEND / CORPORATE ACTION ---
        if 'dividend' in q_lower:
            search_query += f" {current_year} declared amount record date ex date per share"
            print(f"   🧠 Query Type: DIVIDEND → Adding date keywords")
        elif any(w in q_lower for w in ['bonus', 'split', 'buyback', 'rights']):
            search_query += f" {current_year} announced ratio record date details"
            print(f"   🧠 Query Type: CORPORATE ACTION → Adding detail keywords")

        # --- TYPE 10: ACQUISITION / DEAL ---
        if any(w in q_lower for w in ['acquisition', 'merger', 'deal', 'buyout', 'stake']):
            search_query += f" {current_year} official deal value target company announcement"
            print(f"   🧠 Query Type: DEAL → Adding M&A keywords")

        # --- FALLBACK: If no type detected, add generic search boost ---
        type_detected = any(
            any(w in q_lower for w in wlist)
            for wlist in [number_words, reason_words, segment_words, result_words,
                          future_words, mgmt_words, compare_words, asset_words]
        )
        if not type_detected:
            if 'crypto' in q_lower or 'bitcoin' in q_lower:
                search_query += f" {current_year} market analysis price update"
            elif symbols:
                search_query += f" {current_year} latest news analysis update"
            print(f"   🧠 Query Type: GENERAL → Adding generic keywords")

        print(f"   🌐 Deep Search: '{search_query}'")

        # ============================================================
        # STEP C: Execute search (News first, then Text fallback)
        # ============================================================
        results = []
        try:
            with DDGS(verify=False) as ddgs:
                try:
                    # Try news first (fresher results)
                    web_raw = list(ddgs.news(search_query, max_results=5))
                    if not web_raw or len(web_raw) < 2:
                        # Fallback to text search for broader coverage
                        text_raw = list(ddgs.text(search_query, max_results=5))
                        web_raw = (web_raw or []) + (text_raw or [])
                except Exception as e_inner:
                    print(f"      ⚠️ Complex search failed ({e_inner}), trying simple query...")
                    # Fallback to simple query
                    simple_query = query
                    if symbols:
                        simple_query = f"{symbols[0]} latest news"
                    web_raw = list(ddgs.text(simple_query, max_results=5))

                for res in web_raw[:7]:
                    title = res.get('title', 'Web Result')
                    body = res.get('body', '') or res.get('snippet', '')
                    source = res.get('source', 'Web')
                    content = f"WEB RESULT [{source}]: {title}\n{body}"
                    meta = {'source': f'DuckDuckGo: {source}', 'url': res.get('url', '#')}
                    results.append((0.95, content, meta))

            print(f"      → Found {len(results)} web results")
        except Exception as e:
            print(f"      ❌ Web Search Failed: {e}")
        return results

    # ================================================================
    # MAIN ANALYZE METHOD
    # ================================================================
    def analyze(self, query: str, top_k: int = 5) -> str:
        print(f"\n{'='*60}")
        print(f"🔍 Query: '{query}'")
        print(f"{'='*60}")

        # ============================================================
        # STEP 1: ROUTE THE QUERY
        # ============================================================
        route_info = classify_query(query, self.portfolio_symbols)
        route = route_info["route"]
        mentioned_symbols = route_info.get("symbols", [])
        is_summary = route_info.get("is_summary", False)
        needs_web = route_info.get("needs_web", False)
        intent = route_info.get("intent", "unknown")

        emoji = ROUTE_EMOJI.get(route, "🤖")
        label = ROUTE_LABEL.get(route, route)

        print(f"🧭 Route: {emoji} {label}")
        print(f"📌 Symbols: {mentioned_symbols}")
        print(f"💡 Intent: {intent}")
        print(f"🌐 Web Search: {'YES' if needs_web else 'NO'}")
        print("-" * 50)

        # ============================================================
        # ROUTE: CONVERSATIONAL
        # ============================================================
        if route == QueryRoute.CONVERSATIONAL:
            return (
                "👋 Hello! I'm **MarketMind** — your all-rounder financial agent.\n\n"
                "I can help you with:\n\n"
                "| 💹 | **Stock Prices** | *\"What's the current price of Apple?\"* |\n"
                "|---|---|---|\n"
                "| 🎯 | **Analyst Recommendations** | *\"Show analyst recommendations for Tesla\"* |\n"
                "| 📊 | **Fundamentals** | *\"What are the fundamentals of Microsoft?\"* |\n"
                "| ⚖️ | **Compare Stocks** | *\"Compare Google and Amazon stocks\"* |\n"
                "| 📈 | **Technical Analysis** | *\"Technical analysis of Reliance\"* |\n"
                "| 📰 | **News Search** | *\"Latest news about cryptocurrency\"* |\n"
                "| 💼 | **Portfolio Analysis** | *\"How is my portfolio doing?\"* |\n"
                "| 🔍 | **Stock Research** | *\"Should I buy Zomato?\"* |\n"
                "| 🌐 | **Market Overview** | *\"How is the market today?\"* |\n\n"
                "I cover **Indian stocks (NSE)**, **US stocks (NYSE/NASDAQ)**, **Crypto**, and **Commodities**. Ask me anything! 🚀"
            )

        # ============================================================
        # STEP 2: GATHER DATA (Route-specific)
        # ============================================================
        print(f"📈 Fetching data for {label}...")
        data_context = ""

        if route == QueryRoute.STOCK_PRICE:
            data_context = "## 💹 LIVE STOCK DATA\n\n" + self._get_stock_detail_context(mentioned_symbols)

        elif route == QueryRoute.RECOMMENDATIONS:
            data_context = self._get_recommendations_context(mentioned_symbols)
            # Also add current price context
            data_context += "\n\n## 💹 CURRENT PRICE DATA\n\n" + self._get_stock_detail_context(mentioned_symbols)

        elif route == QueryRoute.FUNDAMENTALS:
            data_context = self._get_fundamentals_context(mentioned_symbols)

        elif route == QueryRoute.COMPARISON:
            data_context = self._get_comparison_context(mentioned_symbols)
            # Also add price history
            for sym in mentioned_symbols:
                hist = get_price_history(sym, "1mo")
                if hist.get('success'):
                    data_context += f"\n{sym} 1-Month Trend: {hist['trend']} ({hist['total_change_pct']:+.2f}%)"

        elif route == QueryRoute.TECHNICALS:
            data_context = self._get_technicals_context(mentioned_symbols)
            data_context += "\n\n## 💹 PRICE CONTEXT\n\n" + self._get_stock_detail_context(mentioned_symbols)

        elif route == QueryRoute.DISCOVERY:
            discovery_syms = route_info.get("discovery_symbols", mentioned_symbols)
            data_context = "## 🔍 TARGET STOCK DATA\n\n" + self._get_stock_detail_context(discovery_syms)
            # Add recommendations too
            data_context += "\n\n" + self._get_recommendations_context(discovery_syms)
            # Add portfolio for comparison
            data_context += "\n\n## 💼 YOUR PORTFOLIO (For Comparison)\n\n" + self._get_market_snapshot()

        elif route == QueryRoute.PORTFOLIO:
            data_context = "## 💼 PORTFOLIO LIVE DATA\n\n" + self._get_market_snapshot(mentioned_symbols)

        elif route == QueryRoute.GENERAL_MARKET:
            data_context = self._get_market_snapshot(mentioned_symbols)

        elif route == QueryRoute.NEWS_SEARCH:
            if mentioned_symbols:
                data_context = "## 💹 RELATED STOCK DATA\n\n" + self._get_stock_detail_context(mentioned_symbols)

        print("   ✅ Data gathered")

        # ============================================================
        # STEP 3: LOCAL HYBRID SEARCH
        # ============================================================
        print("📚 Running Local Hybrid Search...")
        is_specific = len(mentioned_symbols) > 0

        documents = self.search_engine.search(
            query,
            top_k=top_k,
            vector_weight=0.4 if is_specific else 0.7,
            bm25_weight=0.6 if is_specific else 0.3,
            web_fallback=False
        )

        # ============================================================
        # STEP 4: WEB SEARCH (If needed)
        # ============================================================
        if needs_web:
            print("   🚀 Executing Deep Web Search...")
            web_docs = self._perform_deep_search(query, mentioned_symbols)
            documents = web_docs + documents
            documents = documents[:8]

        if documents:
            doc_context = "\n\n".join([
                f"[Source {i+1}] ({meta.get('source','Unknown')})\n{content}"
                for i, (score, content, meta) in enumerate(documents)
            ])
        else:
            doc_context = "No specific news found. Use live market data and general knowledge."

        # ============================================================
        # STEP 5: SELECT SYSTEM PROMPT
        # ============================================================
        prompt_map = {
            QueryRoute.STOCK_PRICE: STOCK_PRICE_SYSTEM_PROMPT,
            QueryRoute.RECOMMENDATIONS: RECOMMENDATIONS_SYSTEM_PROMPT,
            QueryRoute.FUNDAMENTALS: FUNDAMENTALS_SYSTEM_PROMPT,
            QueryRoute.COMPARISON: COMPARISON_SYSTEM_PROMPT,
            QueryRoute.TECHNICALS: TECHNICALS_SYSTEM_PROMPT,
            QueryRoute.NEWS_SEARCH: NEWS_SEARCH_SYSTEM_PROMPT,
            QueryRoute.PORTFOLIO: PORTFOLIO_SYSTEM_PROMPT,
            QueryRoute.DISCOVERY: DISCOVERY_SYSTEM_PROMPT,
            QueryRoute.GENERAL_MARKET: GENERAL_MARKET_SYSTEM_PROMPT,
        }

        base_prompt = prompt_map.get(route, GENERAL_MARKET_SYSTEM_PROMPT)
        if is_summary:
            base_prompt = SUMMARY_SYSTEM_PROMPT

        system_prompt = base_prompt.format(
            portfolio_str=self._get_portfolio_string(),
            risk_tolerance=self.profile.get('risk_tolerance', 'moderate'),
            investment_horizon=self.profile.get('investment_horizon', 'long-term'),
            current_date=datetime.datetime.now().strftime("%B %d, %Y"),
        )

        print(f"   👉 Prompt Mode: {label}")

        # ============================================================
        # STEP 6: BUILD USER PROMPT
        # ============================================================
        user_prompt = f"""
## ❓ USER QUESTION:
{query}

## 📊 LIVE DATA (REAL-TIME — USE THESE NUMBERS):
{data_context}

## 📰 INTELLIGENCE BRIEF (NEWS & SOURCES):
{doc_context}

## INSTRUCTIONS:
- **EXTREMELY CONCISE**. Max 300 words.
- Use **bullet points** and **short sentences**.
- **No standard disclaimers**.
- Answer the specific route goal directly.
- Use the **LIVE DATA** provided. Do not hallucinate.
"""

        # ============================================================
        # STEP 7: CALL GEMINI (with retry)
        # ============================================================
        print("🧠 Gemini 2.5 Synthesizing...")
        analysis = None
        last_error = None
        for attempt in range(3):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=user_prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3,
                        max_output_tokens=8000,
                    )
                )
                analysis = response.text
                break
            except Exception as e:
                last_error = e
                error_str = str(e)
                if any(kw in error_str.lower() for kw in ['<!doctype', '<html', 'too many open files', 'sophos']):
                    print(f"   ⚠️ Attempt {attempt+1}/3: Network firewall blocking. Retrying...")
                else:
                    print(f"   ⚠️ Attempt {attempt+1}/3: {error_str[:100]}. Retrying...")
                _time.sleep(2 ** attempt)

        if analysis is None:
            error_msg = str(last_error)
            if any(kw in error_msg.lower() for kw in ['<!doctype', '<html', 'too many open files', 'sophos']):
                return "❌ **Analysis failed: Network firewall/proxy is blocking the Gemini API.**\n\n**Fix:** Switch to mobile hotspot or use a VPN."
            return f"❌ Analysis failed: {last_error}"

        # ============================================================
        # STEP 8: FINAL OUTPUT
        # ============================================================
        web_note = "Includes Web Search" if needs_web else "Local DB + Live Data"
        sym_str = ", ".join(mentioned_symbols) if mentioned_symbols else "General"

        return f"""
# {emoji} MarketMind — {label}

{analysis}

---
*{emoji} Route: {label} | Symbols: {sym_str} | Sources: {len(documents)} ({web_note})*
"""

    def morning_briefing(self) -> str:
        return self.analyze("What is the critical update for my portfolio stocks today? Check sentiment vs price.")

    def ask(self, question: str) -> str:
        return self.analyze(question)


# ============================================================================
# DEMO
# ============================================================================
if __name__ == "__main__":
    analyst = GeminiAnalyst()

    tests = [
        ("Stock Price", "What's the current stock price of Apple?"),
        ("Recommendations", "Show me analyst recommendations for Tesla"),
        ("Fundamentals", "What are the fundamentals of Microsoft stock?"),
        ("Comparison", "Compare the performance of Google and Amazon stocks"),
        ("Technicals", "Technical analysis of Reliance"),
        ("News", "Get the latest financial news about cryptocurrency"),
        ("Portfolio", "How is my portfolio doing today?"),
        ("Discovery", "Should I buy Zomato?"),
        ("Market", "How is the market today?"),
    ]

    for name, query in tests:
        print(f"\n{'='*70}")
        print(f"TEST: {name}")
        print(f"{'='*70}")
        result = analyst.analyze(query)
        print(result[:500] + "..." if len(result) > 500 else result)
