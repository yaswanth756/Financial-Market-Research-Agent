"""
Hybrid Search Engine
====================
Gap 2 Fix: Combine BM25 (Keyword Search) + Chroma (Vector Search)
Gap 4 Fix: Deep Search Fallback (Web Search)

WHY THIS MATTERS:
-----------------
Vector Search (Semantic):
  ✅ Good at: "What's happening with banks?" → finds articles about HDFC, ICICI
  ❌ Bad at: "HDFC Q3 Results" → might confuse with "ICICI Q2" or "HDFC Q1"
  ❌ Bad at: Numbers, ticker symbols, exact phrases

BM25 (Keyword Search):
  ✅ Good at: "HDFC Q3 Results" → exact keyword match
  ✅ Good at: Ticker symbols, specific numbers
  ❌ Bad at: Understanding synonyms ("bank" ≠ "financial institution")

Deep Search (Web Fallback):
  ✅ Good at: Breaking news (last hour), obscure topics, confirming facts
  ❌ Bad at: Speed (slow), consistency
"""

import warnings
warnings.filterwarnings('ignore')

import os
import re
import numpy as np
from rank_bm25 import BM25Okapi
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer
from duckduckgo_search import DDGS  # New: Web Search

os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'


# ============================================================================
# LOCAL EMBEDDINGS (Same interface as other files)
# ============================================================================
class LocalEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text).tolist()


# ============================================================================
# TOKENIZER for BM25
# ============================================================================
def tokenize(text: str) -> list:
    """
    Simple but effective tokenizer for financial text.
    Preserves ticker symbols, numbers, and percentages.
    """
    # Lowercase
    text = text.lower()
    # Keep alphanumeric, %, ., and hyphens
    tokens = re.findall(r'[a-z0-9]+(?:\.[a-z0-9]+)*|[0-9]+(?:\.[0-9]+)?%?', text)
    # Remove very short tokens (except numbers)
    tokens = [t for t in tokens if len(t) > 1 or t.isdigit()]
    return tokens


# ============================================================================
# BM25 INDEX
# ============================================================================
class BM25Index:
    """
    Keyword search index using BM25 (Best Match 25).
    """
    
    def __init__(self):
        self.documents = []      # List of (content, metadata)
        self.tokenized_docs = [] # Tokenized versions
        self.bm25 = None
        self.is_built = False
    
    def build_from_chroma(self, chroma_db: Chroma):
        """
        Build BM25 index from all documents in ChromaDB.
        This syncs the keyword index with the vector index.
        """
        print("🔄 Building BM25 index from ChromaDB...")
        
        # Fetch ALL documents from ChromaDB
        try:
            all_data = chroma_db.get(include=["documents", "metadatas"])
            
            if not all_data['documents']:
                print("   ⚠️ No documents in ChromaDB!")
                return
            
            self.documents = []
            self.tokenized_docs = []
            
            for doc_content, metadata in zip(all_data['documents'], all_data['metadatas']):
                self.documents.append((doc_content, metadata or {}))
                self.tokenized_docs.append(tokenize(doc_content))
            
            # Build BM25 index
            self.bm25 = BM25Okapi(self.tokenized_docs)
            self.is_built = True
            
            print(f"   ✅ BM25 index built with {len(self.documents)} documents")
        except Exception as e:
            print(f"   ❌ BM25 Build Error: {e}")
    
    def search(self, query: str, top_k: int = 20) -> list:
        """
        Search using BM25 keyword matching.
        Returns: List of (score, content, metadata) sorted by relevance
        """
        if not self.is_built or not self.bm25:
            print("   ⚠️ BM25 index not built yet!")
            return []
        
        query_tokens = tokenize(query)
        
        if not query_tokens:
            return []
        
        # Get BM25 scores for all documents
        scores = self.bm25.get_scores(query_tokens)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include docs with non-zero relevance
                content, metadata = self.documents[idx]
                results.append((float(scores[idx]), content, metadata))
        
        return results


# ============================================================================
# RECIPROCAL RANK FUSION (RRF)
# ============================================================================
def reciprocal_rank_fusion(
    vector_results: list,
    bm25_results: list,
    k: int = 60,
    vector_weight: float = 0.5,
    bm25_weight: float = 0.5,
) -> list:
    """
    Combine results from Vector and BM25 search using Reciprocal Rank Fusion.
    """
    # Use content hash as document key for deduplication
    doc_scores = {}  # key -> {rrf_score, content, metadata}
    
    def doc_key(content: str) -> str:
        """Create a unique key from first 200 chars of content"""
        return content[:200].strip()
    
    # Score Vector results
    for rank, (score, content, metadata) in enumerate(vector_results, 1):
        key = doc_key(content)
        if key not in doc_scores:
            doc_scores[key] = {
                'rrf_score': 0.0,
                'content': content,
                'metadata': metadata,
                'sources': [],
            }
        doc_scores[key]['rrf_score'] += vector_weight / (k + rank)
        doc_scores[key]['sources'].append(f"vector(rank={rank})")
    
    # Score BM25 results
    for rank, (score, content, metadata) in enumerate(bm25_results, 1):
        key = doc_key(content)
        if key not in doc_scores:
            doc_scores[key] = {
                'rrf_score': 0.0,
                'content': content,
                'metadata': metadata,
                'sources': [],
            }
        doc_scores[key]['rrf_score'] += bm25_weight / (k + rank)
        doc_scores[key]['sources'].append(f"bm25(rank={rank})")
    
    # Sort by fused RRF score
    fused = sorted(doc_scores.values(), key=lambda x: x['rrf_score'], reverse=True)
    
    # Return as (score, content, metadata)
    return [(item['rrf_score'], item['content'], item['metadata']) for item in fused]


# ============================================================================
# HYBRID SEARCH ENGINE
# ============================================================================
class HybridSearchEngine:
    """
    Production-grade hybrid search combining:
    1. Semantic search (ChromaDB + embeddings)
    2. Keyword search (BM25)
    3. Deep Search Fallback (Web)
    """
    
    def __init__(self, db_path: str = "./market_mind_db"):
        print("\n🔀 Initializing Hybrid Search Engine")
        print("-" * 50)
        
        # Vector search
        self.embeddings = LocalEmbeddings()
        self.chroma_db = Chroma(
            persist_directory=db_path,
            embedding_function=self.embeddings
        )
        print("   ✅ ChromaDB (Vector Search) connected")
        
        # Keyword search
        self.bm25_index = BM25Index()
        self._sync_bm25()
        
        # Track last sync time
        self._doc_count = self._get_doc_count()
        
        print("-" * 50)
        print("🔀 Hybrid Search Engine ready!\n")
    
    def _get_doc_count(self) -> int:
        """Get current document count in ChromaDB"""
        try:
            all_data = self.chroma_db.get()
            return len(all_data['ids'])
        except Exception:
            return 0
    
    def _sync_bm25(self):
        """Rebuild BM25 index from ChromaDB"""
        self.bm25_index.build_from_chroma(self.chroma_db)
    
    def _check_sync(self):
        """Check if BM25 index needs to be rebuilt (new docs added)"""
        current_count = self._get_doc_count()
        if current_count != self._doc_count:
            print(f"   🔄 New documents detected ({self._doc_count} → {current_count}), rebuilding BM25...")
            self._sync_bm25()
            self._doc_count = current_count
    
    def search(
        self,
        query: str,
        top_k: int = 20,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5,
        use_hyde_embedding: list = None,
        web_fallback: bool = True
    ) -> list:
        """
        Hybrid search combining semantic + keyword matching + Web Fallback.
        """
        # Auto-sync BM25 if new documents were added
        self._check_sync()
        
        # --- VECTOR SEARCH ---
        print(f"   🔎 Vector Search: '{query[:50]}...'")
        vector_results = []
        try:
            if use_hyde_embedding:
                vector_results_raw = self.chroma_db.similarity_search_by_vector(
                    use_hyde_embedding, k=top_k
                )
            else:
                embedding = self.embeddings.embed_query(query)
                vector_results_raw = self.chroma_db.similarity_search_by_vector(
                    embedding, k=top_k
                )
            
            for rank, doc in enumerate(vector_results_raw, 1):
                score = 1.0 / rank  # Simple rank-based score
                vector_results.append((score, doc.page_content, doc.metadata))
            print(f"      → Found {len(vector_results)} vector results")
        except Exception as e:
            print(f"      ❌ Vector Search Error: {e}")
        
        
        # --- BM25 SEARCH ---
        print(f"   📝 BM25 Search: '{query[:50]}...'")
        try:
            bm25_results = self.bm25_index.search(query, top_k=top_k)
            print(f"      → Found {len(bm25_results)} keyword results")
        except Exception as e:
            print(f"      ❌ BM25 Search Error: {e}")
            bm25_results = []
        
        
        # --- FUSION ---
        print(f"   🔀 Fusing results (Vector={vector_weight:.0%}, BM25={bm25_weight:.0%})...")
        fused = reciprocal_rank_fusion(
            vector_results=vector_results,
            bm25_results=bm25_results,
            vector_weight=vector_weight,
            bm25_weight=bm25_weight,
        )
        
        # --- DEEP SEARCH FALLBACK ---
        # If we have very few results, OR specific query requested
        if web_fallback and len(fused) < 3:
            print(f"   🌐 LOCAL INTEL LOW ({len(fused)} docs). TRIGGERING DEEP SEARCH...")
            try:
                with DDGS() as ddgs:
                    # 1. Try News Search first
                    print("      → Searching DuckDuckGo News...")
                    web_results_raw = list(ddgs.news(query, max_results=4))
                    
                    # 2. If no news, try standard search
                    if not web_results_raw:
                        print("      → Searching DuckDuckGo Web...")
                        web_results_raw = list(ddgs.text(query, max_results=4))
                    
                    print(f"      → Found {len(web_results_raw)} external results")
                    
                    for res in web_results_raw:
                        # Give web results a high synthetic score to boost visibility
                        score = 0.8
                        # Handle different APi responses
                        title = res.get('title', 'Unknown Title')
                        body = res.get('body', '') or res.get('snippet', '')
                        content = f"WEB SEARCH RESULT: {title}\n{body}"
                        
                        meta = {
                            'source': f"Web: {res.get('source', 'Internet')}",
                            'date': res.get('date', 'Recent'),
                            'url': res.get('url', '#')
                        }
                        fused.append((score, content, meta))
                        
            except Exception as e:
                print(f"      ❌ Web Search failed: {e}")

        # Deduplicate, Sort, Return
        # (Content-based dedup)
        unique_docs = []
        seen_content = set()
        
        # Re-sort because we appended web results
        fused.sort(key=lambda x: x[0], reverse=True)
        
        for score, content, meta in fused:
            content_sig = content[:200].lower()
            if content_sig not in seen_content:
                unique_docs.append((score, content, meta))
                seen_content.add(content_sig)
        
        top_results = unique_docs[:top_k]
        print(f"      → {len(unique_docs)} unique docs → returning top {len(top_results)}")
        
        return top_results


# ============================================================================
# DEMO
# ============================================================================
if __name__ == "__main__":
    engine = HybridSearchEngine()
    
    # Test fallback
    print("\n--- Testing Deep Search Fallback ---")
    results = engine.search("Latest Tata Steel acquisition 2026", top_k=3, web_fallback=True)
    
    for i, (score, content, meta) in enumerate(results, 1):
        print(f"\n{i}. [{score:.2f}] {meta.get('source')} - {content[:100]}...")
