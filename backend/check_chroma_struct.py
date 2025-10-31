import chromadb
import json

client = chromadb.PersistentClient(path='./data/chroma')
collections = client.list_collections()

print("="*70)
print("ChromaDB 詳細結構分析")
print("="*70)

for col in collections:
    result = col.get(limit=100)
    print(f"\n📚 Collection: {col.name}")
    print(f"   記錄數: {len(result['ids'])}")
    
    if result['ids'] and len(result['ids']) > 0:
        print(f"\n   分析第一個記錄:")
        print(f"   - ID: {result['ids'][0][:20]}...")
        
        # 檢查 documents
        doc = result['documents'][0] if result.get('documents') else None
        print(f"   - Document: {type(doc).__name__} = {str(doc)[:80] if doc else '[NULL]'}")
        
        # 檢查 metadata
        meta = result['metadatas'][0] if result.get('metadatas') else {}
        print(f"   - Metadata type: {type(meta).__name__}")
        print(f"   - Metadata keys: {list(meta.keys()) if meta else 'None'}")
        if 'data' in meta:
            print(f"   - metadata.data: {meta['data'][:80]}")
        
        # 檢查 embedding
        emb = result['embeddings'][0] if result.get('embeddings') else None
        if emb:
            print(f"   - Embedding dim: {len(emb)}")
        else:
            print(f"   - Embedding: [NULL]")

print("\n" + "="*70)
