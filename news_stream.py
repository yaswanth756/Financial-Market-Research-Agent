import time
import feedparser
import hashlib
import requests
import warnings
import os

# Suppress warnings  
warnings.filterwarnings('ignore')
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
os.environ['CURL_CA_BUNDLE'] = ''

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from user_config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION
from langchain_core.documents import Document
from sentence_transformers import SentenceTransformer

from langchain_core.embeddings import Embeddings

# Custom embedding class that works offline
class LocalEmbeddings(Embeddings):
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print("🔄 Loading local embedding model...")
        self.model = SentenceTransformer(model_name)
        print("✅ Model loaded!")
    
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text: str) -> list[float]:
        return self.model.encode(text).tolist()

# RELIABLE WORKING FEEDS (tested & verified)
RSS_FEEDS = [
    ("FT", "https://www.ft.com/rss/home/uk"),
    ("Economist", "https://www.economist.com/finance-and-economics/rss.xml"),
    ("MoneyControl", "https://www.moneycontrol.com/rss/MCtopnews.xml"),
    ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms"),
]

# THE GATEKEEPER (Finance Keywords Filter)
FINANCE_KEYWORDS = [
    "earnings", "revenue", "profit", "loss", "quarter", "fiscal",
    "dividend", "stock", "shares", "ipo", "fed", "rates", "inflation",
    "bull", "bear", "forecast", "outlook", "debt", "acquisition", "merger",
    "buy", "sell", "hold", "portfolio", "market", "trading", "investor",
    "rupee", "dollar", "gold", "oil", "sensex", "nifty", "bank"
]

def is_strict_finance(text):
    text_lower = text.lower()
    return any(word in text_lower for word in FINANCE_KEYWORDS)

def fetch_rss(url):
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)'}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        if response.status_code == 200:
            return feedparser.parse(response.content)
    except Exception as e:
        pass
    return feedparser.FeedParserDict(entries=[])

# Initialize Qdrant Client & Vector Store
print(f"🔄 Connecting to Qdrant Cloud...")
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embeddings = LocalEmbeddings()

# Check if collection exists, if not create it
try:
    client.get_collection(QDRANT_COLLECTION)
    print(f"✅ Connected to collection: {QDRANT_COLLECTION}")
except Exception:
    print(f"⚠️ Collection '{QDRANT_COLLECTION}' not found. Creating...")
    client.create_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
    )
    print(f"✅ Created collection: {QDRANT_COLLECTION}")

db = QdrantVectorStore(
    client=client,
    collection_name=QDRANT_COLLECTION,
    embedding=embeddings
)

def get_article_id(url):
    return hashlib.md5(url.encode()).hexdigest()

def listen_to_news():
    print("--- 🛡️  Finance News Stream Started ---")
    seen_ids = set()

    while True:
        try:
            new_docs = []
            new_ids = []
            total_found = 0

            for name, rss_url in RSS_FEEDS:
                feed = fetch_rss(rss_url)
                count = len(feed.entries)
                total_found += count
                print(f"📰 {name}: {count} articles")

                for entry in feed.entries:
                    url = entry.link
                    uid = get_article_id(url)
                    title = entry.title
                    
                    if uid in seen_ids: 
                        continue
                    
                    summary = getattr(entry, 'summary', getattr(entry, 'description', ''))
                    full_text = f"{title} {summary}"
                    
                    if not is_strict_finance(full_text):
                        continue 

                    # Check existence using Qdrant Client directly
                    try:
                        existing = client.retrieve(
                            collection_name=QDRANT_COLLECTION,
                            ids=[uid]
                        )
                        if existing:
                            seen_ids.add(uid)
                            continue
                    except Exception:
                        pass

                    print(f"   💰 {title[:65]}...")
                    doc = Document(page_content=full_text, metadata={"source": name, "url": url})
                    new_docs.append(doc)
                    new_ids.append(uid)
                    seen_ids.add(uid)

            print(f"\n📊 Total: {total_found} articles scanned")
            
            if new_docs:
                print(f"💾 Saving {len(new_docs)} new articles to database...")
                db.add_documents(documents=new_docs, ids=new_ids)
                print(f"✅ Saved!")
            else:
                print("ℹ️  No new finance articles")
            
            print("💤 Sleeping 60s...\n" + "="*50 + "\n")
            time.sleep(60)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    listen_to_news()