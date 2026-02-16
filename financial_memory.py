"""
Financial Memory — Qdrant-backed Persistent Memory
====================================================
Stores across sessions:
1. User Preferences (risk tolerance, preferred KPIs, sectors)
2. Past Research (queries + results cached)
3. Conversation Context (follow-up support)

Collections:
- financial_user_memory   → preferences & profile
- financial_research_cache → past research results
- financial_market_news    → news articles (existing)
"""

import json
import hashlib
import datetime
from typing import Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from user_config import QDRANT_URL, QDRANT_API_KEY

# Collection names
MEMORY_COLLECTION = "financial_user_memory"
RESEARCH_CACHE_COLLECTION = "financial_research_cache"

# Embedding model (same as news_stream)
_model = None

def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _embed(text: str) -> list[float]:
    return _get_model().encode(text).tolist()


def _hash_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


class FinancialMemory:
    """
    Persistent financial memory backed by Qdrant.
    Remembers:
    - risk_tolerance, preferred_kpis, sectors, geographies
    - past research queries and results
    - conversation history for follow-ups
    """

    def __init__(self):
        print("🧠 Initializing Financial Memory...")
        self.client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        self._ensure_collections()

        # In-memory conversation buffer (last N turns for follow-ups)
        self.conversation_history: list[dict] = []
        self.max_history = 20

        # Load user preferences from Qdrant on startup
        self.preferences = self._load_preferences()
        print(f"   ✅ Memory ready | Preferences: {json.dumps(self.preferences, indent=2)}")

    def _ensure_collections(self):
        """Create Qdrant collections if they don't exist."""
        for coll in [MEMORY_COLLECTION, RESEARCH_CACHE_COLLECTION]:
            try:
                self.client.get_collection(coll)
            except Exception:
                print(f"   📦 Creating collection: {coll}")
                self.client.create_collection(
                    collection_name=coll,
                    vectors_config=models.VectorParams(
                        size=384,
                        distance=models.Distance.COSINE,
                    ),
                )

    # ================================================================
    # USER PREFERENCES
    # ================================================================

    def _load_preferences(self) -> dict:
        """Load user preferences from Qdrant."""
        defaults = {
            "risk_tolerance": "moderate",
            "preferred_kpis": ["EBITDA", "ROE", "Revenue Growth"],
            "sectors": ["IT", "Banking", "Energy"],
            "geographies": ["India", "US"],
            "investment_horizon": "long-term",
            "analysis_style": "balanced",  # conservative / balanced / aggressive
        }
        try:
            results = self.client.scroll(
                collection_name=MEMORY_COLLECTION,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="user_preferences"),
                        )
                    ]
                ),
                limit=1,
                with_payload=True,
                with_vectors=False,
            )
            points, _ = results
            if points:
                stored = points[0].payload.get("preferences", {})
                # Merge with defaults (so new keys are added)
                for k, v in defaults.items():
                    if k not in stored:
                        stored[k] = v
                return stored
        except Exception as e:
            print(f"   ⚠️ Could not load preferences: {e}")
        return defaults

    def save_preferences(self, prefs: dict):
        """Save user preferences to Qdrant (upsert)."""
        self.preferences.update(prefs)
        point_id = _hash_id("user_preferences_v1")
        text = f"User preferences: {json.dumps(self.preferences)}"
        self.client.upsert(
            collection_name=MEMORY_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=_embed(text),
                    payload={
                        "type": "user_preferences",
                        "preferences": self.preferences,
                        "updated_at": datetime.datetime.now().isoformat(),
                    },
                )
            ],
        )
        print(f"   💾 Preferences saved to Qdrant")

    def get_preferences(self) -> dict:
        return self.preferences

    def update_preference(self, key: str, value):
        """Update a single preference key."""
        self.preferences[key] = value
        self.save_preferences(self.preferences)

    # ================================================================
    # RESEARCH CACHE
    # ================================================================

    def cache_research(self, query: str, result: str, metadata: dict = None):
        """Cache a research result in Qdrant for future retrieval."""
        point_id = _hash_id(query.lower().strip())
        payload = {
            "type": "research_cache",
            "query": query,
            "result": result[:5000],  # Limit size
            "metadata": metadata or {},
            "created_at": datetime.datetime.now().isoformat(),
            "ttl_hours": 24,  # Results are "fresh" for 24 hours
        }
        self.client.upsert(
            collection_name=RESEARCH_CACHE_COLLECTION,
            points=[
                models.PointStruct(
                    id=point_id,
                    vector=_embed(query),
                    payload=payload,
                )
            ],
        )

    def find_similar_research(self, query: str, top_k: int = 3, freshness_hours: int = 24) -> list[dict]:
        """
        Find past research similar to current query.
        Returns cached results if fresh enough.
        """
        try:
            results = self.client.query_points(
                collection_name=RESEARCH_CACHE_COLLECTION,
                query=_embed(query),
                limit=top_k,
                with_payload=True,
            )
            
            now = datetime.datetime.now()
            fresh_results = []
            for point in results.points:
                payload = point.payload
                created = datetime.datetime.fromisoformat(payload.get("created_at", "2000-01-01"))
                age_hours = (now - created).total_seconds() / 3600
                ttl = payload.get("ttl_hours", 24)
                
                fresh_results.append({
                    "query": payload.get("query", ""),
                    "result": payload.get("result", ""),
                    "metadata": payload.get("metadata", {}),
                    "age_hours": round(age_hours, 1),
                    "is_fresh": age_hours <= ttl,
                    "score": point.score,
                })
            return fresh_results
        except Exception as e:
            print(f"   ⚠️ Research cache lookup failed: {e}")
            return []

    # ================================================================
    # CONVERSATION HISTORY (in-memory for speed, persisted summary)
    # ================================================================

    def add_turn(self, role: str, content: str, metadata: dict = None):
        """Add a conversation turn."""
        turn = {
            "role": role,  # "user" or "assistant"
            "content": content,
            "metadata": metadata or {},
            "timestamp": datetime.datetime.now().isoformat(),
        }
        self.conversation_history.append(turn)
        # Keep only last N turns
        if len(self.conversation_history) > self.max_history:
            self.conversation_history = self.conversation_history[-self.max_history:]

    def get_conversation_context(self, last_n: int = 6) -> str:
        """Get recent conversation as formatted text for LLM context."""
        if not self.conversation_history:
            return ""
        recent = self.conversation_history[-last_n:]
        lines = ["## 💬 RECENT CONVERSATION CONTEXT"]
        for turn in recent:
            role_emoji = "👤" if turn["role"] == "user" else "🤖"
            # Truncate long responses
            content = turn["content"][:300]
            lines.append(f"{role_emoji} {turn['role'].upper()}: {content}")
        return "\n".join(lines)

    def get_last_user_query(self) -> Optional[str]:
        """Get the last user query (for follow-up detection)."""
        for turn in reversed(self.conversation_history):
            if turn["role"] == "user":
                return turn["content"]
        return None

    def get_last_symbols(self) -> list[str]:
        """Get symbols from the last assistant response metadata."""
        for turn in reversed(self.conversation_history):
            if turn["role"] == "assistant":
                return turn.get("metadata", {}).get("symbols", [])
        return []

    # ================================================================
    # INTERACTION PATTERNS
    # ================================================================

    def save_interaction(self, query: str, symbols: list, route: str):
        """Save a user interaction pattern to learn from."""
        point_id = _hash_id(f"interaction_{datetime.datetime.now().isoformat()}_{query[:50]}")
        text = f"User asked about {', '.join(symbols) if symbols else 'general'}: {query}"
        payload = {
            "type": "interaction",
            "query": query,
            "symbols": symbols,
            "route": route,
            "timestamp": datetime.datetime.now().isoformat(),
        }
        try:
            self.client.upsert(
                collection_name=MEMORY_COLLECTION,
                points=[
                    models.PointStruct(
                        id=point_id,
                        vector=_embed(text),
                        payload=payload,
                    )
                ],
            )
        except Exception:
            pass  # Non-critical

    def suggest_next_analysis(self) -> str:
        """Based on past interactions, suggest what to analyze next."""
        try:
            results = self.client.scroll(
                collection_name=MEMORY_COLLECTION,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="type",
                            match=models.MatchValue(value="interaction"),
                        )
                    ]
                ),
                limit=50,
                with_payload=True,
                with_vectors=False,
            )
            points, _ = results
            if not points:
                return "No past interactions found. Try asking about your portfolio stocks!"

            # Count symbol frequencies
            symbol_counts: dict[str, int] = {}
            route_counts: dict[str, int] = {}
            for p in points:
                for sym in p.payload.get("symbols", []):
                    symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
                route = p.payload.get("route", "")
                if route:
                    route_counts[route] = route_counts.get(route, 0) + 1

            top_symbols = sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:5]
            top_routes = sorted(route_counts.items(), key=lambda x: x[1], reverse=True)[:3]

            suggestion_parts = []
            if top_symbols:
                most_watched = top_symbols[0][0]
                suggestion_parts.append(f"You research **{most_watched}** most often.")
                # Find least-researched in portfolio
                least = [s for s, c in top_symbols if c == min(x[1] for x in top_symbols)]
                if least:
                    suggestion_parts.append(f"Consider deep-diving into **{least[0]}** — you haven't looked at it recently.")

            if top_routes:
                fav_route = top_routes[0][0]
                suggestion_parts.append(f"Your favorite analysis type is **{fav_route}**.")

            prefs = self.preferences
            if prefs.get("sectors"):
                suggestion_parts.append(f"Based on your sector interest ({', '.join(prefs['sectors'])}), check for sector rotation signals.")

            return "\n".join(suggestion_parts) if suggestion_parts else "Try analyzing your portfolio for this week's outlook!"

        except Exception as e:
            return f"Could not generate suggestion: {e}"

    # ================================================================
    # PREFERENCE CONTEXT FOR LLM
    # ================================================================

    def get_preference_context(self) -> str:
        """Format user preferences as LLM context."""
        p = self.preferences
        return (
            f"## 👤 USER PROFILE (From Memory)\n"
            f"- Risk Tolerance: **{p.get('risk_tolerance', 'moderate')}**\n"
            f"- Preferred KPIs: **{', '.join(p.get('preferred_kpis', []))}**\n"
            f"- Sectors of Interest: **{', '.join(p.get('sectors', []))}**\n"
            f"- Geographies: **{', '.join(p.get('geographies', []))}**\n"
            f"- Investment Horizon: **{p.get('investment_horizon', 'long-term')}**\n"
            f"- Analysis Style: **{p.get('analysis_style', 'balanced')}**\n"
        )


# ================================================================
# Singleton
# ================================================================
_memory_instance: Optional[FinancialMemory] = None


def get_memory() -> FinancialMemory:
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = FinancialMemory()
    return _memory_instance
