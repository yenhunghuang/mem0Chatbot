#!/usr/bin/env python3
"""
測試 Mem0 記憶搜索修復

驗證 search_memories() 是否正確返回記憶內容
"""

import sys
sys.path.insert(0, 'backend')

from src.config import settings
from src.services.memory_service import MemoryService
import uuid

# 初始化 Mem0 服務
print("🔄 初始化 Mem0 服務...")
MemoryService.initialize()

# 使用現有的使用者 ID
user_id = "d531dbe9-ba7d-4f66-a6f6-b84f09e358c1"

print(f"\n👤 使用者 ID: {user_id}\n")

# 測試 1: 搜索特定查詢
print("=" * 60)
print("測試 1: 搜索「科技股」")
print("=" * 60)

results = MemoryService.search_memories(
    user_id=user_id,
    query="科技股",
    top_k=5
)

print(f"\n✅ 找到 {len(results)} 個記憶\n")
for i, memory in enumerate(results, 1):
    print(f"[{i}] 內容: {memory['content'][:60]}")
    print(f"    ID: {memory['id']}")
    print(f"    相關度: {memory['metadata'].get('relevance', 'N/A'):.2f}")
    if memory['metadata'].get('created_at'):
        print(f"    建立時間: {memory['metadata']['created_at']}")
    print()

# 測試 2: 搜索另一個查詢
print("=" * 60)
print("測試 2: 搜索「AI」")
print("=" * 60)

results = MemoryService.search_memories(
    user_id=user_id,
    query="AI",
    top_k=5
)

print(f"\n✅ 找到 {len(results)} 個記憶\n")
for i, memory in enumerate(results, 1):
    print(f"[{i}] 內容: {memory['content'][:60]}")
    print(f"    ID: {memory['id']}")
    print(f"    相關度: {memory['metadata'].get('relevance', 'N/A'):.2f}")
    print()

# 測試 3: 搜索投資風險
print("=" * 60)
print("測試 3: 搜索「風險」")
print("=" * 60)

results = MemoryService.search_memories(
    user_id=user_id,
    query="風險",
    top_k=5
)

print(f"\n✅ 找到 {len(results)} 個記憶\n")
for i, memory in enumerate(results, 1):
    print(f"[{i}] 內容: {memory['content'][:60]}")
    print(f"    ID: {memory['id']}")
    print(f"    相關度: {memory['metadata'].get('relevance', 'N/A'):.2f}")
    print()

print("\n" + "=" * 60)
print("✅ 記憶搜索修復驗證完成！")
print("=" * 60)
print("\n💡 重點:")
print("   • content 欄位應該包含實際的記憶文本")
print("   • 每個記憶都有 id 和 metadata")
print("   • 相關度應該是 0-1 之間的浮點數")
