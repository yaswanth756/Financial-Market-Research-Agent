"""
LangGraph Financial Research Agent
====================================
The core multi-step research engine.

Modes:
  QUICK (<30s)  → Summarize, key risks, YoY growth, simple lookups
  DEEP  (<3min) → Fundamental analysis, peer benchmarking, bull/bear thesis,
                   scenario analysis, investment memos

Graph Nodes:
  1. router        → Classify mode + intent + detect follow-ups
  2. clarifier     → Ask clarifying questions if needed
  3. data_gatherer → Fetch market data, Qdrant search, web search
  4. analyzer      → LLM synthesis with confidence scoring
  5. memo_writer   → Structure output as investment memo (deep mode)
  6. memory_saver  → Persist results to Qdrant cache + conversation

Architecture:
  router → clarifier (optional) → data_gatherer → analyzer → memo_writer → memory_saver
"""

import warnings
warnings.filterwarnings('ignore')

import os
import ssl
import json
import re
import time as _time
import datetime
from typing import TypedDict, Annotated, Optional, Literal

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

from langgraph.graph import StateGraph, END

from google import genai
from google.genai import types
import httpx

# Patch httpx for SSL
_orig_httpx = httpx.Client.__init__
def _patched(self, *a, **kw):
    kw['verify'] = False
    kw.setdefault('timeout', httpx.Timeout(60.0, connect=15.0))
    return _orig_httpx(self, *a, **kw)
httpx.Client.__init__ = _patched

_orig_async = httpx.AsyncClient.__init__
def _patched_async(self, *a, **kw):
    kw['verify'] = False
    kw.setdefault('timeout', httpx.Timeout(60.0, connect=15.0))
    return _orig_async(self, *a, **kw)
httpx.AsyncClient.__init__ = _patched_async

from financial_memory import get_memory
from market_tools import (
    get_stock_price, get_price_history, get_portfolio_snapshot,
    get_stock_fundamentals, get_analyst_recommendations,
    compare_stocks, get_technical_indicators,
    format_market_context, format_stock_detail,
    SYMBOL_MAP, _format_currency, _format_large_number,
)
from hybrid_search import HybridSearchEngine
from analyst import (
    classify_query, resolve_stock_from_query, QueryRoute,
    ROUTE_EMOJI, ROUTE_LABEL,
)
from user_config import PORTFOLIO, USER_PROFILE
from duckduckgo_search import DDGS

# ============================================================================
# GEMINI CLIENT
# ============================================================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    from dotenv import load_dotenv
    load_dotenv()
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash"


# ============================================================================
# AGENT STATE
# ============================================================================
class AgentState(TypedDict):
    """State that flows through the LangGraph nodes."""
    # Input
    query: str
    mode: str  # "quick" or "deep"

    # Router output
    route: str
    symbols: list[str]
    intent: str
    needs_web: bool
    is_follow_up: bool
    resolved_query: str  # After follow-up resolution

    # Clarifier
    needs_clarification: bool
    clarification_question: str
    user_assumptions: dict  # time_horizon, scenario, etc.

    # Data gathered
    market_data: str
    news_data: str
    research_cache: str
    memory_context: str
    conversation_context: str
    contradictions: list[str]

    # Analysis output
    analysis: str
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    confidence_reasons: list[str]
    sources_count: int

    # Final output
    final_report: str
    route_label: str
    route_emoji: str
    error: str


# ============================================================================
# FOLLOW-UP DETECTION
# ============================================================================
FOLLOW_UP_PATTERNS = [
    r'^(now|also|and|but)\s+',
    r'^(what about|how about|tell me about)\s+',
    r'^(stress test|re-?evaluate|recalculate|redo)\s+',
    r'^(assuming|if|under|with)\s+',
    r'^(compare that|compare it|versus|vs)\s+',
    r'\b(the same stock|that stock|those stocks|same company)\b',
    r'\b(its|their)\s+(price|fundamentals?|technicals?|pe|revenue|earnings|target|recommendation)',
    r'^(why|how come|explain)\s+',
    r'\b(instead|rather|alternatively)\b',
    r'^(deeper|more detail|elaborate|expand)\s*',
    r'^(and\s+)?(what|how)\s+(about|is)\s+(its|their|the)\b',
    r'^(also|now)\s+(show|get|check|tell)',
]


def is_follow_up(query: str) -> bool:
    """Detect if query is a follow-up that needs context from previous turn."""
    q = query.lower().strip()
    # Only treat as follow-up if no stock symbol is explicitly mentioned
    from analyst import resolve_stock_from_query
    has_own_symbols = bool(resolve_stock_from_query(query))
    if has_own_symbols:
        return False
    return any(re.search(p, q) for p in FOLLOW_UP_PATTERNS)


# ============================================================================
# MODE DETECTION
# ============================================================================
DEEP_TRIGGERS = [
    'deep', 'detailed', 'comprehensive', 'full analysis', 'investment memo',
    'bull and bear', 'bull vs bear', 'bull case', 'bear case',
    'scenario analysis', 'sensitivity', 'stress test',
    'peer comparison', 'peer benchmark', 'benchmarking',
    'fundamental analysis', 'dcf', 'valuation model',
    'compare.*fundamental', 'generate.*memo', 'write.*report',
    'overlooked risks', 'hidden risks', 'what should i analyze',
    'based on my.*preference', 'past preference',
]


def detect_mode(query: str, explicit_mode: Optional[str] = None) -> str:
    if explicit_mode:
        return explicit_mode
    q = query.lower()
    if any(re.search(t, q) for t in DEEP_TRIGGERS):
        return "deep"
    return "quick"


# ============================================================================
# CLARIFICATION DETECTION
# ============================================================================
NEEDS_CLARIFICATION_PATTERNS = {
    "time_horizon": [
        r'should i (buy|invest|hold)',
        r'(good|worth) (investment|buying)',
        r'(invest|put money) in',
    ],
    "scenario": [
        r'stress test',
        r'scenario',
        r'what if',
        r'assuming',
    ],
    "comparison_scope": [
        r'compare.*(sector|industry|peer)',
        r'benchmark',
    ],
}


def detect_clarification_need(query: str, mode: str, state: AgentState) -> tuple[bool, str, dict]:
    """Check if we need to ask the user for more info before analyzing."""
    q = query.lower()
    assumptions = {}

    # In quick mode, never ask — just assume defaults
    if mode == "quick":
        return False, "", {"time_horizon": "short-term", "scenario": "base_case"}

    # Only ask in deep mode for ambiguous queries
    for category, patterns in NEEDS_CLARIFICATION_PATTERNS.items():
        for p in patterns:
            if re.search(p, q):
                if category == "time_horizon" and "horizon" not in q and "term" not in q:
                    memory = get_memory()
                    prefs = memory.get_preferences()
                    default_horizon = prefs.get("investment_horizon", "long-term")
                    # Auto-use from memory instead of asking
                    assumptions["time_horizon"] = default_horizon
                elif category == "scenario" and "inflation" not in q and "recession" not in q:
                    assumptions["scenario"] = "base_case"

    return False, "", assumptions


# ============================================================================
# CONTRADICTION DETECTION
# ============================================================================
def detect_contradictions(market_data: str, news_data: str) -> list[str]:
    """Detect contradictions between market data and news sources."""
    contradictions = []

    # Simple heuristic contradiction detection
    # Positive price + negative news
    if ("🟢" in market_data or "UP" in market_data) and any(
        w in news_data.lower() for w in ['crash', 'plunge', 'collapse', 'crisis', 'sell-off']
    ):
        contradictions.append(
            "⚠️ CONTRADICTION: Stock price is UP but news mentions negative events. "
            "Possible delayed reaction or market has already priced in the bad news."
        )

    # Negative price + positive news
    if ("🔴" in market_data or "DOWN" in market_data) and any(
        w in news_data.lower() for w in ['beat', 'surge', 'record', 'strong', 'upgrade']
    ):
        contradictions.append(
            "⚠️ CONTRADICTION: Stock price is DOWN but news is positive. "
            "Possible profit-booking, broader market drag, or news not yet reflected."
        )

    # Multiple sources disagreeing
    bullish_sources = len(re.findall(r'(bullish|upgrade|buy|outperform)', news_data.lower()))
    bearish_sources = len(re.findall(r'(bearish|downgrade|sell|underperform)', news_data.lower()))
    if bullish_sources >= 2 and bearish_sources >= 2:
        contradictions.append(
            f"⚠️ MIXED SIGNALS: {bullish_sources} bullish vs {bearish_sources} bearish signals across sources. "
            "Analyst opinions are divided."
        )

    return contradictions


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================
def calculate_confidence(
    sources_count: int,
    has_live_data: bool,
    has_web_data: bool,
    contradictions: list[str],
    mode: str,
) -> tuple[str, list[str]]:
    """Calculate confidence level with reasons."""
    score = 0
    reasons = []

    # Sources
    if sources_count >= 5:
        score += 3
        reasons.append(f"✅ {sources_count} sources consulted")
    elif sources_count >= 2:
        score += 2
        reasons.append(f"⚠️ {sources_count} sources (moderate coverage)")
    else:
        score += 1
        reasons.append(f"⚠️ Only {sources_count} source(s) — limited data")

    # Live data
    if has_live_data:
        score += 2
        reasons.append("✅ Live market data included")
    else:
        reasons.append("⚠️ No live market data")

    # Web data
    if has_web_data:
        score += 1
        reasons.append("✅ Web intelligence included")

    # Contradictions reduce confidence
    if contradictions:
        score -= len(contradictions)
        reasons.append(f"⚠️ {len(contradictions)} contradiction(s) detected")

    # Map to level
    if score >= 5:
        return "HIGH", reasons
    elif score >= 3:
        return "MEDIUM", reasons
    else:
        return "LOW", reasons


# ============================================================================
# NODE 1: ROUTER
# ============================================================================
def router_node(state: AgentState) -> dict:
    """Classify the query, detect mode, resolve follow-ups."""
    query = state["query"]
    mode = state.get("mode", "quick")
    memory = get_memory()

    # Detect mode from query content
    mode = detect_mode(query, mode if mode != "auto" else None)

    # Check if this is a follow-up
    follow_up = is_follow_up(query)
    resolved_query = query
    carried_symbols = []

    if follow_up:
        last_query = memory.get_last_user_query()
        last_symbols = memory.get_last_symbols()
        if last_symbols and not resolve_stock_from_query(query):
            carried_symbols = last_symbols
            resolved_query = f"{query} (regarding {', '.join(last_symbols)})"
            print(f"   🔗 Follow-up detected! Carrying symbols: {last_symbols}")

    # Classify the query
    portfolio_symbols = [s['symbol'].upper() for s in PORTFOLIO.get('stocks', [])]
    route_info = classify_query(resolved_query, portfolio_symbols)

    # If follow-up carried symbols but classify_query didn't find them, inject them
    if carried_symbols and not route_info.get("symbols"):
        route_info["symbols"] = carried_symbols
        # Fix route based on follow-up query keywords
        if route_info.get("route") in [QueryRoute.CONVERSATIONAL, "GENERAL", "GENERAL_MARKET"]:
            q_lower = query.lower()
            if any(w in q_lower for w in ['fundamental', 'pe', 'revenue', 'margin', 'eps', 'roe', 'debt']):
                route_info["route"] = QueryRoute.FUNDAMENTALS
            elif any(w in q_lower for w in ['technical', 'rsi', 'macd', 'sma', 'bollinger']):
                route_info["route"] = QueryRoute.TECHNICALS
            elif any(w in q_lower for w in ['recommend', 'target', 'analyst', 'rating']):
                route_info["route"] = QueryRoute.RECOMMENDATIONS
            elif any(w in q_lower for w in ['compare', 'vs', 'versus']):
                route_info["route"] = QueryRoute.COMPARISON
            elif any(w in q_lower for w in ['price', 'trading', 'current', 'cost']):
                route_info["route"] = QueryRoute.STOCK_PRICE
            elif any(w in q_lower for w in ['news', 'latest', 'update']):
                route_info["route"] = QueryRoute.NEWS_SEARCH
            else:
                route_info["route"] = QueryRoute.DISCOVERY
            route_info["needs_web"] = True

    # Special routes based on memory-aware queries
    q_lower = query.lower()
    if any(p in q_lower for p in ['past preference', 'my preference', 'what should i analyze', 'analyze next']):
        route_info["route"] = "SUGGESTION"
        route_info["intent"] = "memory_suggestion"

    return {
        "mode": mode,
        "route": route_info.get("route", "GENERAL"),
        "symbols": route_info.get("symbols", []),
        "intent": route_info.get("intent", "unknown"),
        "needs_web": route_info.get("needs_web", False),
        "is_follow_up": follow_up,
        "resolved_query": resolved_query,
        "route_label": ROUTE_LABEL.get(route_info.get("route", ""), route_info.get("route", "")),
        "route_emoji": ROUTE_EMOJI.get(route_info.get("route", ""), "🤖"),
    }


# ============================================================================
# NODE 2: CLARIFIER
# ============================================================================
def clarifier_node(state: AgentState) -> dict:
    """Check if clarification needed; if so, auto-fill from memory."""
    query = state["query"]
    mode = state["mode"]

    needs_clarify, question, assumptions = detect_clarification_need(query, mode, state)

    return {
        "needs_clarification": needs_clarify,
        "clarification_question": question,
        "user_assumptions": assumptions,
    }


# ============================================================================
# NODE 3: DATA GATHERER
# ============================================================================
def data_gatherer_node(state: AgentState) -> dict:
    """Gather all data: market data, Qdrant search, web search, memory."""
    query = state.get("resolved_query", state["query"])
    symbols = state.get("symbols", [])
    route = state.get("route", "GENERAL")
    mode = state.get("mode", "quick")
    needs_web = state.get("needs_web", False)
    memory = get_memory()

    market_data = ""
    news_data = ""
    research_cache = ""

    # --- Special: SUGGESTION route ---
    if (route == "SUGGESTION"):
        suggestion = memory.suggest_next_analysis()
        pref_ctx = memory.get_preference_context()
        return {
            "market_data": pref_ctx,
            "news_data": suggestion,
            "research_cache": "",
            "memory_context": pref_ctx,
            "conversation_context": memory.get_conversation_context(),
            "contradictions": [],
            "sources_count": 1,
        }

    # --- Special: CONVERSATIONAL route ---
    if route == QueryRoute.CONVERSATIONAL:
        return {
            "market_data": "",
            "news_data": "",
            "research_cache": "",
            "memory_context": memory.get_preference_context(),
            "conversation_context": memory.get_conversation_context(),
            "contradictions": [],
            "sources_count": 0,
        }

    # --- Market Data (live from Yahoo Finance) ---
    print(f"   📈 Gathering market data for route={route}, symbols={symbols}")

    if route == QueryRoute.STOCK_PRICE and symbols:
        parts = []
        for sym in symbols:
            parts.append(format_stock_detail(sym))
            hist = get_price_history(sym, "5d")
            if hist.get('success'):
                parts.append(f"   5-Day: {hist['trend']} ({hist['total_change_pct']:+.2f}%)")
        market_data = "\n".join(parts)

    elif route == QueryRoute.FUNDAMENTALS and symbols:
        parts = ["## 📊 FUNDAMENTAL DATA (Live)\n"]
        for sym in symbols:
            f = get_stock_fundamentals(sym)
            if f.get('success'):
                currency = f.get('currency', 'USD')
                parts.append(
                    f"**{f.get('name', sym)}** ({f['symbol']}) — {f['sector']} / {f['industry']}\n"
                    f"Price: {_format_currency(f['current_price'], currency)}\n"
                    f"MCap: {f['valuation']['market_cap_formatted']} | PE: {f['valuation']['trailing_pe']} | "
                    f"Fwd PE: {f['valuation']['forward_pe']} | PEG: {f['valuation']['peg_ratio']}\n"
                    f"P/B: {f['valuation']['price_to_book']} | EV/EBITDA: {f['valuation']['ev_to_ebitda']}\n"
                    f"Revenue: {f['profitability']['revenue_formatted']} (Growth: {f['profitability']['revenue_growth']}%)\n"
                    f"Margins: Gross={f['profitability']['gross_margins']}% | Op={f['profitability']['operating_margins']}% | Net={f['profitability']['profit_margins']}%\n"
                    f"EPS: {f['profitability']['eps_trailing']} (Fwd: {f['profitability']['eps_forward']})\n"
                    f"Cash: {f['balance_sheet']['total_cash_formatted']} | Debt: {f['balance_sheet']['total_debt_formatted']} | D/E: {f['balance_sheet']['debt_to_equity']}\n"
                    f"ROE: {f['balance_sheet']['return_on_equity']}% | ROA: {f['balance_sheet']['return_on_assets']}%\n"
                    f"Div Yield: {f['dividends']['dividend_yield']}%\n"
                )
        market_data = "\n".join(parts)

    elif route == QueryRoute.COMPARISON and symbols:
        comp = compare_stocks(symbols)
        if comp.get('success'):
            parts = ["## ⚖️ COMPARISON\n"]
            for sym, data in comp['comparison'].items():
                if 'error' not in data:
                    currency = data.get('currency', 'USD')
                    parts.append(
                        f"**{data['name']}** ({sym}): {_format_currency(data['price'], currency)} ({data['change_pct']:+.2f}%)\n"
                        f"  MCap: {data['market_cap']} | PE: {data['pe_ratio']} | Growth: {data['revenue_growth']}%\n"
                        f"  Margin: {data['profit_margin']}% | ROE: {data['roe']}% | D/E: {data['debt_to_equity']}\n"
                    )
            market_data = "\n".join(parts)

    elif route == QueryRoute.TECHNICALS and symbols:
        parts = ["## 📈 TECHNICALS\n"]
        for sym in symbols:
            tech = get_technical_indicators(sym)
            if tech.get('success'):
                parts.append(
                    f"**{sym}** — {tech['overall_signal']}\n"
                    f"  RSI: {tech['rsi_14']} | MACD: {tech['macd_line']} | Signal: {tech['signal_line']}\n"
                    f"  SMA20: {tech['sma_20']} | SMA50: {tech['sma_50']}\n"
                    f"  Bollinger: {tech['bollinger_lower']} - {tech['bollinger_upper']}\n"
                )
                for s in tech['signals']:
                    parts.append(f"  {s}")
        market_data = "\n".join(parts)

    elif route == QueryRoute.RECOMMENDATIONS and symbols:
        parts = ["## 🎯 ANALYST RECOMMENDATIONS\n"]
        for sym in symbols:
            recs = get_analyst_recommendations(sym)
            if recs.get('success'):
                currency = recs.get('currency', 'USD')
                parts.append(
                    f"**{recs.get('name', sym)}** ({recs['symbol']})\n"
                    f"  Consensus: {recs['consensus']} | Analysts: {recs['num_analysts']}\n"
                    f"  Target: {_format_currency(recs['target_mean'], currency)} "
                    f"(Low: {_format_currency(recs['target_low'], currency)} / High: {_format_currency(recs['target_high'], currency)})\n"
                    f"  Upside: {recs['upside_pct']:+.1f}%\n"
                )
        market_data = "\n".join(parts)

    elif route in [QueryRoute.PORTFOLIO, QueryRoute.GENERAL_MARKET]:
        portfolio_symbols_list = [s['symbol'] for s in PORTFOLIO.get('stocks', [])]
        market_data = format_market_context(portfolio_symbols_list + (symbols or []))

    elif route == QueryRoute.DISCOVERY and symbols:
        parts = []
        for sym in symbols:
            parts.append(format_stock_detail(sym))
            recs = get_analyst_recommendations(sym)
            if recs.get('success'):
                currency = recs.get('currency', 'USD')
                parts.append(f"  Analyst: {recs['consensus']} | Target: {_format_currency(recs['target_mean'], currency)} ({recs['upside_pct']:+.1f}%)")
        market_data = "\n".join(parts)

    elif symbols:
        market_data = "\n".join(format_stock_detail(sym) for sym in symbols)

    # --- DEEP MODE: Get extra data ---
    if mode == "deep" and symbols:
        extra_parts = ["\n## 📊 DEEP MODE — ADDITIONAL DATA\n"]
        for sym in symbols:
            if route != QueryRoute.FUNDAMENTALS:
                f = get_stock_fundamentals(sym)
                if f.get('success'):
                    extra_parts.append(
                        f"**{sym} Fundamentals**: PE={f['valuation']['trailing_pe']} | "
                        f"Revenue={f['profitability']['revenue_formatted']} | "
                        f"Margin={f['profitability']['profit_margins']}% | "
                        f"ROE={f['balance_sheet']['return_on_equity']}% | "
                        f"D/E={f['balance_sheet']['debt_to_equity']}"
                    )
            if route != QueryRoute.TECHNICALS:
                t = get_technical_indicators(sym)
                if t.get('success'):
                    extra_parts.append(f"**{sym} Technicals**: {t['overall_signal']} | RSI={t['rsi_14']}")
            if route != QueryRoute.RECOMMENDATIONS:
                r = get_analyst_recommendations(sym)
                if r.get('success'):
                    extra_parts.append(f"**{sym} Analyst**: {r['consensus']} | Target Upside: {r['upside_pct']:+.1f}%")
            # Price history
            hist = get_price_history(sym, "3mo")
            if hist.get('success'):
                extra_parts.append(f"**{sym} 3-Month**: {hist['trend']} ({hist['total_change_pct']:+.2f}%)")
        market_data += "\n".join(extra_parts)

    # --- Hybrid Search (Qdrant + BM25) ---
    print("   📚 Running hybrid search...")
    search_engine = HybridSearchEngine()
    documents = search_engine.search(
        query, top_k=5,
        vector_weight=0.4 if symbols else 0.7,
        bm25_weight=0.6 if symbols else 0.3,
        web_fallback=False,
    )

    # --- Web Search ---
    web_docs = []
    if needs_web or mode == "deep":
        print("   🌐 Web search...")
        try:
            search_q = query
            if symbols:
                search_q = f"{symbols[0]} stock {query} {datetime.datetime.now().year}"
            with DDGS(verify=False) as ddgs:
                max_results = 7 if mode == "deep" else 4
                raw = list(ddgs.news(search_q, max_results=max_results))
                if len(raw) < 2:
                    raw += list(ddgs.text(search_q, max_results=max_results))
                for r in raw[:8]:
                    title = r.get('title', '')
                    body = r.get('body', '') or r.get('snippet', '')
                    source = r.get('source', 'Web')
                    content = f"[{source}] {title}\n{body}"
                    web_docs.append((0.95, content, {'source': source, 'url': r.get('url', '#')}))
        except Exception as e:
            print(f"   ⚠️ Web search error: {e}")

    all_docs = web_docs + documents
    all_docs = all_docs[:10]

    if all_docs:
        news_data = "\n\n".join([
            f"[Source {i+1}] ({meta.get('source', 'Unknown')})\n{content}"
            for i, (score, content, meta) in enumerate(all_docs)
        ])
    else:
        news_data = "No specific news found."

    # --- Research Cache ---
    cached = memory.find_similar_research(query, top_k=2)
    fresh_cache = [c for c in cached if c.get('is_fresh') and c.get('score', 0) > 0.85]
    if fresh_cache:
        research_cache = "\n\n".join([
            f"## 📋 PREVIOUS RESEARCH (from {c['age_hours']:.0f}h ago)\nQuery: {c['query']}\n{c['result'][:500]}"
            for c in fresh_cache
        ])
    else:
        research_cache = ""

    # --- Contradiction detection ---
    contradictions = detect_contradictions(market_data, news_data)

    # --- Memory context ---
    memory_context = memory.get_preference_context()
    conversation_context = memory.get_conversation_context()

    sources_count = len(all_docs) + (1 if market_data else 0)

    return {
        "market_data": market_data,
        "news_data": news_data,
        "research_cache": research_cache,
        "memory_context": memory_context,
        "conversation_context": conversation_context,
        "contradictions": contradictions,
        "sources_count": sources_count,
    }


# ============================================================================
# NODE 4: ANALYZER
# ============================================================================

# System prompts per mode
QUICK_SYSTEM = """You are a senior financial analyst providing QUICK insights.

## RULES:
- MAX 250 words. Be concise.
- Use bullet points and bold numbers.
- No disclaimers. No filler. Just facts + verdict.
- If contradictions exist, flag them clearly.
- State your confidence level.
- If CONVERSATION CONTEXT is provided, use it to understand follow-up questions.
  Resolve pronouns like "it", "its", "that stock" using the previous conversation.

## USER PROFILE:
{memory_context}

## FORMAT:
1. **📊 Key Data**: 3-5 bullet points with numbers
2. **💡 Quick Take**: 1-2 sentence verdict
3. **⚠️ Risks**: Only if critical (1 line)
"""

DEEP_SYSTEM = """You are a senior equity analyst writing a DETAILED investment memo.

## RULES:
- Thorough analysis (500-800 words). Evidence-based.
- Reference actual numbers from the provided data.
- If data shows contradictions, explain BOTH sides.
- Clearly state assumptions.
- Provide confidence-weighted conclusions.
- Focus on the user's preferred KPIs: {preferred_kpis}
- Calibrate to user's risk tolerance: {risk_tolerance}
- If CONVERSATION CONTEXT is provided, use it to understand follow-up questions.
  Resolve pronouns like "it", "its", "that stock" using the previous conversation.

## USER PROFILE:
{memory_context}

## FORMAT FOR INVESTMENT MEMO:
1. **📋 Executive Summary** (2-3 sentences)
2. **📊 Key Metrics** (table or bullet points with actual numbers)
3. **🟢 Bull Case** (3 evidence-backed points)
4. **🔴 Bear Case** (3 evidence-backed points)
5. **⚖️ Risk Assessment** (top 3 risks with likelihood)
6. **🎯 Verdict & Recommendation** (BUY/HOLD/SELL with target & timeframe)
7. **📌 Assumptions** (list key assumptions made)
8. **🔍 Confidence**: [HIGH/MEDIUM/LOW] with reasoning
"""

SUGGESTION_SYSTEM = """You are a financial advisor reviewing a user's research patterns.

## RULES:
- Based on their past behavior and preferences, suggest what to research next.
- Be specific — mention stock names, sectors, analysis types.
- Keep it to 3-4 actionable suggestions.
- Reference their risk tolerance and preferred KPIs.
- If CONVERSATION CONTEXT is provided, factor in what the user recently researched.

## USER PROFILE:
{memory_context}
"""


def analyzer_node(state: AgentState) -> dict:
    """Call Gemini LLM to synthesize all gathered data."""
    query = state.get("resolved_query", state["query"])
    mode = state.get("mode", "quick")
    route = state.get("route", "GENERAL")
    memory = get_memory()
    prefs = memory.get_preferences()

    # --- Handle CONVERSATIONAL ---
    if route == QueryRoute.CONVERSATIONAL:
        return {
            "analysis": (
                "👋 Hello! I'm **MarketMind** — your financial research agent.\n\n"
                "**Quick Mode** (<30s): Stock prices, summaries, quick lookups\n"
                "**Deep Mode** (<3min): Full analysis, bull/bear thesis, investment memos\n\n"
                "Try: *\"Compare TCS vs Infosys on fundamentals\"* or *\"Generate a bull and bear case for HDFC Bank\"*"
            ),
            "confidence": "HIGH",
            "confidence_reasons": [],
        }

    # --- Select system prompt ---
    if route == "SUGGESTION":
        system = SUGGESTION_SYSTEM
    elif mode == "deep":
        system = DEEP_SYSTEM
    else:
        system = QUICK_SYSTEM

    system = system.format(
        memory_context=state.get("memory_context", ""),
        preferred_kpis=", ".join(prefs.get("preferred_kpis", ["EBITDA", "ROE"])),
        risk_tolerance=prefs.get("risk_tolerance", "moderate"),
    )

    # --- Build user prompt ---
    parts = [f"## ❓ QUERY:\n{query}\n"]

    if state.get("user_assumptions"):
        parts.append(f"## 📐 ASSUMPTIONS:\n{json.dumps(state['user_assumptions'], indent=2)}\n")

    if state.get("market_data"):
        parts.append(f"## 📊 LIVE MARKET DATA:\n{state['market_data']}\n")

    if state.get("news_data"):
        parts.append(f"## 📰 NEWS & INTELLIGENCE:\n{state['news_data']}\n")

    if state.get("research_cache"):
        parts.append(f"## 📋 PAST RESEARCH:\n{state['research_cache']}\n")

    if state.get("conversation_context"):
        parts.append(f"\n{state['conversation_context']}\n")

    if state.get("contradictions"):
        parts.append("## ⚠️ CONTRADICTIONS DETECTED:\n" + "\n".join(state["contradictions"]) + "\n")

    if mode == "deep":
        parts.append(
            "\n## 📝 INSTRUCTIONS:\n"
            "- Write a FULL investment memo following the format above.\n"
            "- Include bull AND bear case with evidence.\n"
            "- State ALL assumptions.\n"
            "- Provide confidence level with reasons.\n"
        )
    else:
        parts.append(
            "\n## 📝 INSTRUCTIONS:\n"
            "- Be CONCISE (max 250 words).\n"
            "- Focus on the specific question.\n"
            "- Use actual numbers from the data.\n"
        )

    user_prompt = "\n".join(parts)

    # --- Call Gemini ---
    print(f"   🧠 Calling Gemini ({mode} mode)...")
    analysis = None
    last_error = None
    for attempt in range(3):
        try:
            response = gemini_client.models.generate_content(
                model=MODEL,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=0.3 if mode == "quick" else 0.4,
                    max_output_tokens=2000 if mode == "quick" else 8000,
                ),
            )
            analysis = response.text
            break
        except Exception as e:
            last_error = e
            print(f"   ⚠️ Attempt {attempt+1}/3 failed: {str(e)[:80]}")
            _time.sleep(2 ** attempt)

    if analysis is None:
        return {
            "analysis": f"❌ Analysis failed: {last_error}",
            "confidence": "LOW",
            "confidence_reasons": ["LLM call failed"],
            "error": str(last_error),
        }

    # --- Confidence ---
    confidence, reasons = calculate_confidence(
        sources_count=state.get("sources_count", 0),
        has_live_data=bool(state.get("market_data")),
        has_web_data="Web" in state.get("news_data", ""),
        contradictions=state.get("contradictions", []),
        mode=mode,
    )

    return {
        "analysis": analysis,
        "confidence": confidence,
        "confidence_reasons": reasons,
    }


# ============================================================================
# NODE 5: MEMO WRITER (formats final output)
# ============================================================================
def memo_writer_node(state: AgentState) -> dict:
    """Format the final report with metadata."""
    mode = state.get("mode", "quick")
    route = state.get("route", "GENERAL")
    symbols = state.get("symbols", [])
    confidence = state.get("confidence", "MEDIUM")
    analysis = state.get("analysis", "No analysis generated.")
    contradictions = state.get("contradictions", [])
    confidence_reasons = state.get("confidence_reasons", [])

    emoji = state.get("route_emoji", ROUTE_EMOJI.get(route, "🤖"))
    label = state.get("route_label", ROUTE_LABEL.get(route, route))
    sym_str = ", ".join(symbols) if symbols else "General"
    mode_label = "⚡ Quick" if mode == "quick" else "🔬 Deep"
    sources = state.get("sources_count", 0)

    # Confidence badge
    conf_badge = {"HIGH": "🟢 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "🔴 LOW"}.get(confidence, confidence)

    parts = [f"# {emoji} MarketMind — {label}\n"]
    parts.append(analysis)

    # Contradictions section
    if contradictions:
        parts.append("\n---\n### ⚠️ Contradictions Detected")
        for c in contradictions:
            parts.append(c)

    # Footer
    parts.append(f"\n---")
    parts.append(f"*{mode_label} Mode | Confidence: {conf_badge} | Symbols: {sym_str} | Sources: {sources}*")

    return {"final_report": "\n".join(parts)}


# ============================================================================
# NODE 6: MEMORY SAVER
# ============================================================================
def memory_saver_node(state: AgentState) -> dict:
    """Save conversation turn, cache research, track interaction."""
    memory = get_memory()
    query = state["query"]
    symbols = state.get("symbols", [])
    route = state.get("route", "GENERAL")
    report = state.get("final_report", "")

    # Save conversation turn
    memory.add_turn("user", query, {"symbols": symbols, "route": route, "mode": state.get("mode", "quick")})
    memory.add_turn("assistant", report[:1000], {"symbols": symbols, "route": route})

    # Cache research result
    if report and route != QueryRoute.CONVERSATIONAL:
        memory.cache_research(query, report, {"symbols": symbols, "route": route, "mode": state.get("mode")})

    # Track interaction pattern
    memory.save_interaction(query, symbols, route)

    return {}


# ============================================================================
# BUILD THE GRAPH
# ============================================================================
def build_research_graph() -> StateGraph:
    """Build the LangGraph research agent."""
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("router", router_node)
    graph.add_node("clarifier", clarifier_node)
    graph.add_node("data_gatherer", data_gatherer_node)
    graph.add_node("analyzer", analyzer_node)
    graph.add_node("memo_writer", memo_writer_node)
    graph.add_node("memory_saver", memory_saver_node)

    # Define edges (linear pipeline)
    graph.set_entry_point("router")
    graph.add_edge("router", "clarifier")
    graph.add_edge("clarifier", "data_gatherer")
    graph.add_edge("data_gatherer", "analyzer")
    graph.add_edge("analyzer", "memo_writer")
    graph.add_edge("memo_writer", "memory_saver")
    graph.add_edge("memory_saver", END)

    return graph.compile()


# ============================================================================
# RESEARCH AGENT CLASS (Easy interface)
# ============================================================================
class ResearchAgent:
    """
    High-level interface to the LangGraph research agent.
    Use this from the API layer.
    """

    def __init__(self):
        print("\n" + "=" * 70)
        print("🤖 Initializing MarketMind Research Agent (LangGraph)")
        print("=" * 70)
        self.graph = build_research_graph()
        self.memory = get_memory()
        self.portfolio = PORTFOLIO
        self.portfolio_symbols = [s['symbol'].upper() for s in self.portfolio.get('stocks', [])]
        print(f"   📊 Portfolio: {self.portfolio_symbols}")
        print(f"   🧠 Memory: Loaded ({len(self.memory.conversation_history)} turns)")
        print(f"   ⚡ Modes: Quick (<30s) | Deep (<3min)")
        print("=" * 70 + "\n")

    def analyze(self, query: str, mode: str = "auto") -> dict:
        """
        Run the full research pipeline.

        Args:
            query: User question
            mode: "quick", "deep", or "auto" (auto-detect)

        Returns:
            dict with: report, route, mode, confidence, symbols, etc.
        Args:
            query: User question
            mode: "quick", "deep", or "auto" (auto-detect)

        Returns:
            dict with: report, route, mode, confidence, symbols, etc.
        """
        start = _time.time()

        # Build initial state
        initial_state: AgentState = {
            "query": query,
            "mode": mode,
            "route": "",
            "symbols": [],
            "intent": "",
            "needs_web": False,
            "is_follow_up": False,
            "resolved_query": query,
            "needs_clarification": False,
            "clarification_question": "",
            "user_assumptions": {},
            "market_data": "",
            "news_data": "",
            "research_cache": "",
            "memory_context": "",
            "conversation_context": "",
            "contradictions": [],
            "analysis": "",
            "confidence": "MEDIUM",
            "confidence_reasons": [],
            "sources_count": 0,
            "final_report": "",
            "route_label": "",
            "route_emoji": "",
            "error": "",
        }

        # Run the graph
        try:
            result = self.graph.invoke(initial_state)
        except Exception as e:
            elapsed = _time.time() - start
            return {
                "report": f"❌ Agent error: {e}",
                "route": "ERROR",
                "route_label": "Error",
                "route_emoji": "❌",
                "mode": mode,
                "confidence": "LOW",
                "symbols": [],
                "elapsed": round(elapsed, 2),
                "success": False,
                "error": str(e),
            }

        elapsed = _time.time() - start
        print(f"   ⏱️ Completed in {elapsed:.1f}s")

        return {
            "report": result.get("final_report", "No report generated."),
            "route": result.get("route", "GENERAL"),
            "route_label": result.get("route_label", ""),
            "route_emoji": result.get("route_emoji", "🤖"),
            "mode": result.get("mode", mode),
            "confidence": result.get("confidence", "MEDIUM"),
            "confidence_reasons": result.get("confidence_reasons", []),
            "symbols": result.get("symbols", []),
            "contradictions": result.get("contradictions", []),
            "is_follow_up": result.get("is_follow_up", False),
            "elapsed": round(elapsed, 2),
            "sources_count": result.get("sources_count", 0),
            "success": True,
        }

    def get_preferences(self) -> dict:
        return self.memory.get_preferences()

    def update_preferences(self, prefs: dict):
        self.memory.save_preferences(prefs)

    def suggest_next(self) -> str:
        return self.memory.suggest_next_analysis()

    def morning_briefing(self) -> dict:
        return self.analyze("What is the critical update for my portfolio stocks today?", mode="quick")


# ============================================================================
# DEMO
# ============================================================================
if __name__ == "__main__":
    agent = ResearchAgent()

    print("\n--- TEST 1: Quick Mode ---")
    r = agent.analyze("What's the price of TCS?")
    print(r["report"][:500])

    print("\n--- TEST 2: Deep Mode ---")
    r = agent.analyze("Generate a bull and bear case for HDFC Bank", mode="deep")
    print(r["report"][:800])

    print(f"\nElapsed: {r['elapsed']}s | Confidence: {r['confidence']}")
