"""
Smart Retrieval Layer for Financial RAG
========================================
Phase 2: HyDE + Reranking for production-grade retrieval

HyDE: Hypothetical Document Embeddings
- Generates a "fake ideal answer" to search for
- Bridges gap between short queries and long documents

Reranker: Cross-Encoder Quality Filter  
- Takes top 20 results, scores each 0-1
- Returns only top 5 most relevant
"""

import warnings
warnings.filterwarnings('ignore')

from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os

os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'

# ============================================================================
# LOCAL EMBEDDINGS (Same as news_stream.py)
# ============================================================================
class LocalEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text).tolist()

# ============================================================================
# HYDE GENERATOR (Hypothetical Document Embeddings)
# ============================================================================
class HyDEGenerator:
    """
    Instead of searching with "Apple news?", we generate:
    "Apple Inc. reported strong Q4 earnings with revenue of $XX billion,
    beating analyst expectations. iPhone sales grew YY%..."
    
    Then we search for REAL articles that match this hypothesis.
    """
    
    # Finance-specific templates for different query types
    TEMPLATES = {
        "stock": """
Financial Analysis Report: {topic}

The stock has shown significant movement in recent trading sessions. 
Key factors affecting the price include quarterly earnings reports, 
market sentiment, institutional investor activity, and sector trends.
Analysts have revised their price targets based on recent developments.
Trading volume has been notable with implications for near-term momentum.
Revenue growth and profit margins remain key metrics to watch.
        """,
        
        "market": """
Market Overview Report: {topic}

The broader market indices have experienced volatility amid economic data releases.
Key drivers include Federal Reserve policy decisions, inflation metrics, 
employment data, and corporate earnings season. Sector rotation has been 
observed with flows between growth and value stocks. Global factors including
geopolitical tensions and currency movements are impacting sentiment.
Technical indicators suggest key support and resistance levels.
        """,
        
        "earnings": """
Earnings Analysis: {topic}

The company reported quarterly results with revenue and EPS figures.
Management provided forward guidance on growth expectations.
Key segments showed varying performance with margin implications.
The earnings call highlighted strategic initiatives and market opportunities.
Analyst reactions included price target revisions and rating changes.
Year-over-year comparisons reveal trends in profitability and growth.
        """,
        
        "sector": """
Sector Analysis: {topic}

The sector has seen notable developments affecting constituent stocks.
Industry trends including supply chain dynamics, regulatory changes,
and technological disruption are reshaping competitive landscapes.
Key players are adjusting strategies to capture market share.
Valuations across the sector reflect growth expectations and risk factors.
        """,
        
        "default": """
Financial News Summary: {topic}

Recent developments in the financial markets have focused on this topic.
Key stakeholders including companies, regulators, and investors are 
responding to evolving conditions. Market implications include potential
impacts on valuations, trading activity, and investor sentiment.
Analysts are monitoring developments for investment implications.
        """
    }
    
    def __init__(self):
        print("🔄 Initializing HyDE Generator...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ HyDE Generator ready!")
    
    def detect_query_type(self, query: str) -> str:
        """Detect the type of financial query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['earnings', 'revenue', 'profit', 'quarter', 'q1', 'q2', 'q3', 'q4']):
            return "earnings"
        elif any(word in query_lower for word in ['market', 'sensex', 'nifty', 'index', 'dow', 'nasdaq']):
            return "market"
        elif any(word in query_lower for word in ['sector', 'industry', 'banking', 'tech', 'pharma', 'auto']):
            return "sector"
        elif any(word in query_lower for word in ['stock', 'share', 'price', 'buy', 'sell']):
            return "stock"
        else:
            return "default"
    
    def generate_hypothesis(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query"""
        query_type = self.detect_query_type(query)
        template = self.TEMPLATES[query_type]
        hypothesis = template.format(topic=query)
        return hypothesis.strip()
    
    def get_hyde_embedding(self, query: str):
        """Get embedding of the hypothetical document instead of the query"""
        hypothesis = self.generate_hypothesis(query)
        return self.embedder.encode(hypothesis).tolist()

# ============================================================================
# CROSS-ENCODER RERANKER (Quality Filter)
# ============================================================================
class Reranker:
    """
    Takes top N results from vector search and reranks using Cross-Encoder.
    
    Why? Bi-encoders (like our embeddings) are fast but approximate.
    Cross-encoders are slower but MUCH more accurate at relevance scoring.
    
    Flow: Query + Each Document -> Cross-Encoder -> Score (0-1)
    """
    
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        print("🔄 Loading Cross-Encoder Reranker...")
        self.model = CrossEncoder(model_name)
        print("✅ Reranker ready!")
    
    def rerank(self, query: str, documents: list, top_k: int = 5) -> list:
        """
        Rerank documents by relevance to query.
        
        Args:
            query: User's search query
            documents: List of (doc_content, metadata) tuples
            top_k: Number of top results to return
        
        Returns:
            List of (score, doc_content, metadata) sorted by relevance
        """
        if not documents:
            return []
        
        # Prepare pairs for cross-encoder
        pairs = [(query, doc[0]) for doc in documents]
        
        # Get relevance scores
        scores = self.model.predict(pairs)
        
        # Combine scores with documents
        scored_docs = list(zip(scores, documents))
        
        # Sort by score (descending) and take top_k
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        return scored_docs[:top_k]

# ============================================================================
# SMART RETRIEVER (Combines Everything)
# ============================================================================
class SmartRetriever:
    """
    Production-grade retriever combining:
    1. HyDE for better query understanding
    2. Initial broad vector search (top 20)
    3. Cross-encoder reranking (filter to top 5)
    """
    
    def __init__(self, db_path: str = "./market_mind_db"):
        print("\n" + "="*60)
        print("🧠 Initializing Smart Retrieval System")
        print("="*60)
        
        # Load components
        self.embeddings = LocalEmbeddings()
        self.hyde = HyDEGenerator()
        self.reranker = Reranker()
        
        # Connect to ChromaDB
        print("🔄 Connecting to ChromaDB...")
        self.db = Chroma(
            persist_directory=db_path, 
            embedding_function=self.embeddings
        )
        print("✅ Connected to database!")
        print("="*60 + "\n")
    
    def search(self, query: str, use_hyde: bool = True, top_k: int = 5, initial_k: int = 20) -> list:
        """
        Smart search with HyDE + Reranking
        
        Args:
            query: User's question
            use_hyde: Whether to use hypothetical document embeddings
            top_k: Final number of results to return
            initial_k: Number of results to fetch before reranking
        
        Returns:
            List of top relevant documents with scores
        """
        print(f"\n🔍 Query: '{query}'")
        print("-" * 50)
        
        # Step 1: Generate embedding (with or without HyDE)
        if use_hyde:
            print("📝 Using HyDE: Generating hypothetical document...")
            query_embedding = self.hyde.get_hyde_embedding(query)
            print("   ✅ Hypothesis generated")
        else:
            print("📝 Using direct query embedding...")
            query_embedding = self.embeddings.embed_query(query)
        
        # Step 2: Initial broad search
        print(f"🔎 Searching database for top {initial_k} matches...")
        results = self.db.similarity_search_by_vector(
            query_embedding, 
            k=initial_k
        )
        
        if not results:
            print("   ❌ No results found")
            return []
        
        print(f"   ✅ Found {len(results)} initial matches")
        
        # Step 3: Prepare for reranking
        documents = [(doc.page_content, doc.metadata) for doc in results]
        
        # Step 4: Rerank with Cross-Encoder
        print(f"⚡ Reranking with Cross-Encoder (keeping top {top_k})...")
        reranked = self.reranker.rerank(query, documents, top_k=top_k)
        
        print(f"   ✅ Reranking complete!")
        print("-" * 50)
        
        return reranked
    
    def pretty_print_results(self, results: list):
        """Display results in a nice format"""
        if not results:
            print("No results found.")
            return
        
        print("\n" + "="*60)
        print("📊 TOP SEARCH RESULTS")
        print("="*60)
        
        for i, (score, (content, metadata)) in enumerate(results, 1):
            print(f"\n🏆 Result #{i} (Score: {score:.3f})")
            print(f"   Source: {metadata.get('source', 'Unknown')}")
            print(f"   URL: {metadata.get('url', 'N/A')[:60]}...")
            print(f"   Preview: {content[:150]}...")
            print("-" * 40)


# ============================================================================
# DEMO / TEST
# ============================================================================
if __name__ == "__main__":
    # Initialize the smart retriever
    retriever = SmartRetriever()
    
    # Test queries
    test_queries = [
        "What's happening with bank stocks?",
        "Latest RBI rate decision",
        "Tech sector earnings",
    ]
    
    print("\n" + "🚀 SMART RETRIEVAL DEMO " + "🚀")
    print("="*60)
    
    for query in test_queries:
        results = retriever.search(query, use_hyde=True, top_k=3)
        retriever.pretty_print_results(results)
        print("\n" + "="*60 + "\n")
