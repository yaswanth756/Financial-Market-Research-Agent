
import os
import warnings
from langchain_chroma import Chroma
from sentence_transformers import SentenceTransformer

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
os.environ['CURL_CA_BUNDLE'] = ''

# Custom embedding class that works offline (same as in news_stream.py)
class LocalEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        print("🔄 Loading local embedding model...")
        self.model = SentenceTransformer(model_name)
    
    def embed_documents(self, texts):
        return self.model.encode(texts).tolist()
    
    def embed_query(self, text):
        return self.model.encode(text).tolist()

try:
    print("Connecting to ChromaDB...")
    embeddings = LocalEmbeddings()
    db = Chroma(persist_directory="./market_mind_db", embedding_function=embeddings)
    
    # Get all documents
    print("Fetching collection stats...")
    collection_data = db.get()
    count = len(collection_data['ids'])
    print(f"Total documents in DB: {count}")
    
    if count > 0:
        print("\nLast 3 added documents (by ID order, approximation):")
        # Chroma IDs are usually hashes, so order isn't guaranteed chronologically by ID, 
        # but let's see what metadata we have
        metadatas = collection_data['metadatas']
        sources = {}
        for m in metadatas:
            src = m.get('source', 'Unknown')
            sources[src] = sources.get(src, 0) + 1
            
        print("\nSource Breakdown:")
        for src, count in sources.items():
            print(f"- {src}: {count}")

except Exception as e:
    print(f"Error inspecting DB: {e}")
