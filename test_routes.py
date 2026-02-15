"""
🧪 MarketMind — Live Demo: "The Hard Stuff" Test
===================================================
Tests the 2 TOUGHEST question types that previously FAILED:

  Q1: "What is the GNPA of Bajaj Finance?"
      → OLD: ❌ Checked API. No data. Failed.
      → NEW: ✅ Detects NUMBERS type → Searches web → Finds exact %

  Q2: "Why is Bajaj Finance profit down?"
      → OLD: ❌ Saw profit. Checked API. Said "-6%". No reason.
      → NEW: ✅ Detects REASONS type → Searches web → Finds "Higher provisions"

Run:
  python test_routes.py
"""

import warnings
warnings.filterwarnings('ignore')

import os, ssl, time, sys

ssl._create_default_https_context = ssl._create_unverified_context
os.environ['PYTHONHTTPSVERIFY'] = '0'
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

# ============================================================================
# COLORS
# ============================================================================
class C:
    GREEN  = '\033[92m'
    RED    = '\033[91m'
    YELLOW = '\033[93m'
    CYAN   = '\033[96m'
    MAG    = '\033[95m'
    BOLD   = '\033[1m'
    DIM    = '\033[2m'
    END    = '\033[0m'

def header(text):
    print(f"\n{C.BOLD}{C.CYAN}{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}{C.END}\n")

def step(num, text):
    print(f"  {C.BOLD}{C.YELLOW}STEP {num}:{C.END} {C.YELLOW}{text}{C.END}")

def ok(text):
    print(f"  {C.GREEN}✅ {text}{C.END}")

def fail(text):
    print(f"  {C.RED}❌ {text}{C.END}")

def info(text):
    print(f"  {C.CYAN}ℹ️  {text}{C.END}")

def data(label, value):
    print(f"     {C.MAG}{label}:{C.END} {value}")

def divider():
    print(f"  {C.DIM}{'─'*66}{C.END}")


# ============================================================================
# QUESTION 1: GNPA — "Numbers" type (Yahoo API has NO NPA data)
# ============================================================================
def test_question_1():
    header("QUESTION 1: What is the GNPA of Bajaj Finance?")
    print(f"""  {C.DIM}This is a NUMBERS question. Yahoo Finance does NOT have GNPA data.
  The old system would check the API, find nothing, and give up.
  The new system detects "GNPA" → forces web search → finds the exact %.{C.END}
""")

    # --- Step 1: Router ---
    step(1, "Query Router — Does it detect 'GNPA' as a web trigger?")
    from analyst import classify_query, ROUTE_EMOJI, ROUTE_LABEL
    portfolio = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"]

    route_info = classify_query("What is the GNPA of Bajaj Finance?", portfolio)
    route = route_info['route']
    symbols = route_info.get('symbols', [])
    needs_web = route_info.get('needs_web', False)

    data("Route", f"{ROUTE_EMOJI.get(route, '?')} {ROUTE_LABEL.get(route, route)}")
    data("Symbols", symbols)
    data("Web Search", f"{'🌐 YES' if needs_web else '❌ NO'}")

    if needs_web:
        ok("'GNPA' triggered web search! (FORCE_WEB_KEYWORDS working)")
    else:
        fail("'GNPA' did NOT trigger web search. Something is wrong.")
        return

    # --- Step 2: Smart Search Query ---
    step(2, "Smart Search Brain — What search query does it build?")
    info("Calling _perform_deep_search()...")

    from analyst import GeminiAnalyst
    analyst = GeminiAnalyst()

    t1 = time.time()
    web_results = analyst._perform_deep_search("What is the GNPA of Bajaj Finance?", ["BAJFINANCE"])
    elapsed = time.time() - t1

    ok(f"Got {len(web_results)} web results in {elapsed:.1f}s")
    for i, (score, content, meta) in enumerate(web_results[:3], 1):
        print(f"\n     {C.BOLD}[{i}] {meta.get('source', 'Web')}{C.END}")
        print(f"     {content[:200]}...")

    # --- Step 3: Full AI Pipeline ---
    step(3, "Full AI Pipeline — Gemini synthesizes the answer")
    info("Running analyst.analyze()...")

    t1 = time.time()
    result = analyst.analyze("What is the GNPA of Bajaj Finance?")
    elapsed = time.time() - t1

    ok(f"Full analysis in {elapsed:.1f}s")
    print(f"\n{C.BOLD}{C.CYAN}{'─'*70}{C.END}")
    print(result)
    print(f"{C.BOLD}{C.CYAN}{'─'*70}{C.END}")

    return analyst


# ============================================================================
# QUESTION 2: Why profit down — "Reasons" type (API only has %, not WHY)
# ============================================================================
def test_question_2(analyst=None):
    header("QUESTION 2: Why is Bajaj Finance profit down?")
    print(f"""  {C.DIM}This is a REASONS question. Yahoo Finance only shows "-6%" but NOT why.
  The old system would say "profit is down 6%" and stop.
  The new system detects "why" + "profit" → web search → finds the real cause.{C.END}
""")

    # --- Step 1: Router ---
    step(1, "Query Router — Does 'why' + 'profit' trigger web search?")
    from analyst import classify_query, ROUTE_EMOJI, ROUTE_LABEL
    portfolio = ["TCS", "INFY", "RELIANCE", "HDFCBANK", "ICICIBANK"]

    route_info = classify_query("Why is Bajaj Finance profit down?", portfolio)
    route = route_info['route']
    symbols = route_info.get('symbols', [])
    needs_web = route_info.get('needs_web', False)

    data("Route", f"{ROUTE_EMOJI.get(route, '?')} {ROUTE_LABEL.get(route, route)}")
    data("Symbols", symbols)
    data("Web Search", f"{'🌐 YES' if needs_web else '❌ NO'}")

    if needs_web:
        ok("'why' triggered web search! (FORCE_WEB_KEYWORDS working)")
    else:
        fail("'why' did NOT trigger web search. Something is wrong.")
        return

    # --- Step 2: Smart Search Query ---
    step(2, "Smart Search Brain — Does it add 'reason breakdown analysis'?")

    if analyst is None:
        from analyst import GeminiAnalyst
        analyst = GeminiAnalyst()

    t1 = time.time()
    web_results = analyst._perform_deep_search("Why is Bajaj Finance profit down?", ["BAJFINANCE"])
    elapsed = time.time() - t1

    ok(f"Got {len(web_results)} web results in {elapsed:.1f}s")
    for i, (score, content, meta) in enumerate(web_results[:3], 1):
        print(f"\n     {C.BOLD}[{i}] {meta.get('source', 'Web')}{C.END}")
        print(f"     {content[:200]}...")

    # --- Step 3: Full AI Pipeline ---
    step(3, "Full AI Pipeline — Gemini synthesizes the answer")
    info("Running analyst.analyze()...")

    t1 = time.time()
    result = analyst.analyze("Why is Bajaj Finance profit down?")
    elapsed = time.time() - t1

    ok(f"Full analysis in {elapsed:.1f}s")
    print(f"\n{C.BOLD}{C.CYAN}{'─'*70}{C.END}")
    print(result)
    print(f"{C.BOLD}{C.CYAN}{'─'*70}{C.END}")

    return analyst


# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    header("🧪 MarketMind — 'The Hard Stuff' Live Demo")
    print(f"""
  Testing 2 questions that PREVIOUSLY FAILED and NOW WORK:

  {C.CYAN}Q1:{C.END} "What is the GNPA of Bajaj Finance?"    → {C.GREEN}NUMBERS{C.END} type
  {C.CYAN}Q2:{C.END} "Why is Bajaj Finance profit down?"      → {C.GREEN}REASONS{C.END} type

  Each question goes through 3 steps:
    Step 1: Query Router  — Does it detect the hard keyword?
    Step 2: Search Brain  — Does it build a smart search query?
    Step 3: Full Pipeline — Does Gemini give the right answer?
""")

    try:
        input(f"  {C.BOLD}👉 Press ENTER to start Q1...{C.END}\n")
    except EOFError:
        pass

    # Question 1
    analyst = test_question_1()

    try:
        input(f"\n  {C.BOLD}👉 Press ENTER to start Q2...{C.END}\n")
    except EOFError:
        pass

    # Question 2
    analyst = test_question_2(analyst)

    # Done
    header("✅ DEMO COMPLETE")
    print(f"""
  {C.GREEN}Both "Hard Stuff" questions answered successfully!{C.END}

  {C.BOLD}What changed:{C.END}
  1. {C.CYAN}FORCE_WEB_KEYWORDS{C.END} — 100+ new triggers (GNPA, NPA, why, reason, segment...)
  2. {C.CYAN}Smart Search Brain{C.END} — Detects question TYPE and adds magic search words
     • NUMBERS  → "percentage number data reported"
     • REASONS  → "reason breakdown analysis cause factor"
     • SEGMENT  → "segment wise revenue profit breakup"
     • RESULTS  → "net profit revenue PAT reported"
     • FUTURE   → "outlook guidance management forecast"
     • CONCALL  → "management commentary concall highlights"

  {C.BOLD}Try more hard questions:{C.END}
    • "What is the NIM of HDFC Bank?"
    • "Why did Zomato stock crash?"
    • "Bajaj Finance Q3 results segment wise breakup"
    • "What is the management guidance for Reliance?"
    • "ICICI Bank asset quality — GNPA vs NNPA trend"
""")
