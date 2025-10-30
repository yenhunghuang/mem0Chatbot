import chromadb
from pathlib import Path

# ChromaDB 路徑
chroma_path = Path('backend/data/chroma')

print("=" * 60)
print("🧠 檢查 Mem0/ChromaDB 記憶")
print("=" * 60)

if not chroma_path.exists():
    print(f"\n❌ ChromaDB 資料夾不存在：{chroma_path}")
    print("\n💡 這表示還未有記憶被寫入")
    exit(1)

print(f"\n✅ ChromaDB 路徑：{chroma_path}")

try:
    # 連接 ChromaDB
    client = chromadb.PersistentClient(path=str(chroma_path))
    
    # 列出所有集合
    collections = client.list_collections()
    print(f"\n📚 集合數量：{len(collections)}")
    
    if not collections:
        print("\n❌ 未找到任何記憶集合")
        print("\n💡 這表示 Mem0 還未成功寫入任何記憶到 ChromaDB")
        exit(1)
    
    total_memories = 0
    for collection in collections:
        print(f"\n📦 集合名稱：{collection.name}")
        
        # 取得集合中的所有記憶
        results = collection.get(include=['documents', 'metadatas'])
        
        memory_count = len(results['ids'])
        total_memories += memory_count
        print(f"   記憶數量：{memory_count}")
        
        if memory_count > 0:
            print(f"\n   📝 記憶內容：")
            for i, (doc_id, doc, metadata) in enumerate(zip(
                results['ids'], 
                results['documents'], 
                results['metadatas']
            ), 1):
                if doc:
                    content = doc[:80] + "..." if len(doc) > 80 else doc
                    print(f"      [{i}] {content}")
                else:
                    print(f"      [{i}] (empty)")
                if metadata:
                    print(f"          元資料: {metadata}")
    
    print("\n" + "=" * 60)
    if total_memories > 0:
        print(f"✅ 已成功寫入 {total_memories} 個記憶到 ChromaDB！")
        print("=" * 60)
        exit(0)
    else:
        print("❌ 未找到任何記憶")
        print("=" * 60)
        exit(1)
    
except Exception as e:
    print(f"\n❌ 錯誤：{e}")
    exit(1)
