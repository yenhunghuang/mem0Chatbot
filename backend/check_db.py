#!/usr/bin/env python3
"""快速檢查數據庫狀態"""

import chromadb
import sqlite3
import json

print("=" * 60)
print("📊 數據庫檢查報告")
print("=" * 60)

# 檢查 SQLite
print("\n🗄️ SQLite Database (data/app.db)")
print("-" * 60)
conn = sqlite3.connect('data/app.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM conversations")
conv_count = cursor.fetchone()[0]
print(f"✅ Conversations: {conv_count}")

cursor.execute("SELECT COUNT(*) FROM messages")
msg_count = cursor.fetchone()[0]
print(f"✅ Messages: {msg_count}")

cursor.execute("SELECT COUNT(*) FROM memory_metadata")
mem_meta_count = cursor.fetchone()[0]
print(f"✅ Memory Metadata: {mem_meta_count}")

# 查詢最新的對話
cursor.execute("""
    SELECT id, user_id, message_count, created_at 
    FROM conversations 
    ORDER BY created_at DESC LIMIT 1
""")
latest_conv = cursor.fetchone()
if latest_conv:
    print(f"\n📌 最新對話:")
    print(f"   ID: {latest_conv[0]}")
    print(f"   User: {latest_conv[1]}")
    print(f"   Messages: {latest_conv[2]}")
    print(f"   Created: {latest_conv[3]}")

conn.close()

# 檢查 ChromaDB
print("\n\n🔍 ChromaDB Vector Store (data/chroma)")
print("-" * 60)
try:
    client = chromadb.PersistentClient(path='./data/chroma')
    collections = client.list_collections()
    print(f"✅ Collections: {len(collections)}")
    
    for col in collections:
        result = col.get(limit=100)
        print(f"\n   📚 Collection: {col.name}")
        print(f"      Records: {len(result['ids'])}")
        
        if len(result['ids']) > 0 and result.get('metadatas'):
            # Show last 3 memories
            print(f"      Latest memories:")
            for i in range(min(3, len(result['ids']))):
                idx = len(result['ids']) - 1 - i
                mem_id = result['ids'][idx]
                metadata = result['metadatas'][idx] if result['metadatas'][idx] else {}
                content = result['documents'][idx] if result.get('documents') and result['documents'][idx] else "N/A"
                
                print(f"        [{i+1}] {mem_id[:20]}...")
                print(f"            Content: {str(content)[:60]}")
                if 'data' in metadata:
                    print(f"            Data: {str(metadata['data'])[:60]}")
                    
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
