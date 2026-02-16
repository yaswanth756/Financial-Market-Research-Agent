
import os
import warnings
from qdrant_client import QdrantClient
from user_config import QDRANT_URL, QDRANT_API_KEY, QDRANT_COLLECTION

# Suppress warnings
warnings.filterwarnings('ignore')
os.environ['HF_HUB_DISABLE_SSL_VERIFY'] = '1'
os.environ['CURL_CA_BUNDLE'] = ''

def check_qdrant():
    print("🔄 Connecting to Qdrant Cloud...")
    try:
        client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        
        # Check if collection exists
        collections = client.get_collections()
        exists = any(c.name == QDRANT_COLLECTION for c in collections.collections)
        
        if not exists:
            print(f"❌ Collection '{QDRANT_COLLECTION}' not found!")
            return

        print(f"✅ Collection '{QDRANT_COLLECTION}' found!")
        
        # Get stats
        count_result = client.count(QDRANT_COLLECTION)
        count = count_result.count
        print(f"📊 Total documents in DB: {count}")
        
        if count > 0:
            print("\nFetching sample documents...")
            points, _ = client.scroll(
                collection_name=QDRANT_COLLECTION,
                limit=50,
                with_payload=True,
                with_vectors=False
            )
            
            sources = {}
            for point in points:
                payload = point.payload or {}
                meta = payload.get('metadata', {})
                # Handle flattened or nested metadata
                src = meta.get('source') if isinstance(meta, dict) else payload.get('source', 'Unknown')
                
                sources[src] = sources.get(src, 0) + 1
                
            print("\nSource Breakdown (based on sample of 50):")
            for src, c in sources.items():
                print(f"- {src}: {c}")

    except Exception as e:
        print(f"❌ Error inspecting DB: {e}")

if __name__ == "__main__":
    check_qdrant()
