import sys
print("Step 1: Basic imports...", flush=True)

try:
    from langgraph.graph import StateGraph, END
    print("  ✅ LangGraph OK", flush=True)
except Exception as e:
    print(f"  ❌ LangGraph FAIL: {e}", flush=True)
    sys.exit(1)

try:
    from qdrant_client import QdrantClient
    print("  ✅ Qdrant Client OK", flush=True)
except Exception as e:
    print(f"  ❌ Qdrant FAIL: {e}", flush=True)
    sys.exit(1)

try:
    from google import genai
    print("  ✅ Google GenAI OK", flush=True)
except Exception as e:
    print(f"  ❌ Google GenAI FAIL: {e}", flush=True)
    sys.exit(1)

print("\nStep 2: Project imports...", flush=True)

try:
    from user_config import QDRANT_URL, QDRANT_API_KEY
    print("  ✅ user_config OK", flush=True)
except Exception as e:
    print(f"  ❌ user_config FAIL: {e}", flush=True)
    sys.exit(1)

try:
    from market_tools import get_stock_price
    print("  ✅ market_tools OK", flush=True)
except Exception as e:
    print(f"  ❌ market_tools FAIL: {e}", flush=True)
    sys.exit(1)

try:
    from analyst import classify_query, QueryRoute, ROUTE_EMOJI, ROUTE_LABEL
    print("  ✅ analyst OK", flush=True)
except Exception as e:
    print(f"  ❌ analyst FAIL: {e}", flush=True)
    sys.exit(1)

print("\nStep 3: New modules...", flush=True)

try:
    from financial_memory import FinancialMemory, get_memory
    print("  ✅ financial_memory OK", flush=True)
except Exception as e:
    print(f"  ❌ financial_memory FAIL: {e}", flush=True)
    sys.exit(1)

try:
    from research_agent import ResearchAgent
    print("  ✅ research_agent OK", flush=True)
except Exception as e:
    print(f"  ❌ research_agent FAIL: {e}", flush=True)
    sys.exit(1)

print("\n🎉 ALL IMPORTS SUCCESSFUL!", flush=True)
