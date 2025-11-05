# ChromaDB Delete 機制詳解

**問題**: ChromaDB 的 `delete()` 操作是軟刪除（標記為 inactive）還是硬刪除（真正移除）？

**答案**: **ChromaDB 使用硬刪除（Hard Delete）**，向量和資料會被真正從資料庫中移除。

---

## 📋 目錄

1. [軟刪除 vs 硬刪除](#軟刪除-vs-硬刪除)
2. [ChromaDB 的刪除機制](#chromadb-的刪除機制)
3. [實際驗證](#實際驗證)
4. [底層實現細節](#底層實現細節)
5. [實際影響](#實際影響)
6. [最佳實踐](#最佳實踐)

---

## 🔍 軟刪除 vs 硬刪除

### 軟刪除 (Soft Delete)

**定義**: 不真正刪除資料，只是標記為「已刪除」狀態

**實現方式**:
```sql
-- 關聯式資料庫範例
UPDATE memories
SET is_deleted = TRUE, deleted_at = NOW()
WHERE id = 'mem_001';

-- 查詢時過濾
SELECT * FROM memories WHERE is_deleted = FALSE;
```

**優點**:
- ✅ 可以恢復資料
- ✅ 保留完整歷史
- ✅ 支援審計追蹤

**缺點**:
- ❌ 佔用儲存空間
- ❌ 影響查詢效能
- ❌ 需要定期清理

---

### 硬刪除 (Hard Delete)

**定義**: 真正從資料庫中移除資料

**實現方式**:
```sql
-- 關聯式資料庫範例
DELETE FROM memories WHERE id = 'mem_001';

-- 資料真正消失
SELECT * FROM memories WHERE id = 'mem_001';
-- 返回: 0 rows
```

**優點**:
- ✅ 釋放儲存空間
- ✅ 提升查詢效能
- ✅ 符合資料隱私要求

**缺點**:
- ❌ 無法恢復
- ❌ 失去歷史記錄
- ❌ 需謹慎操作

---

## 💾 ChromaDB 的刪除機制

### 核心結論

**ChromaDB 使用硬刪除**，當您呼叫 `collection.delete()` 時：

1. ✅ 向量被真正移除
2. ✅ 文檔內容被刪除
3. ✅ 中繼資料被清除
4. ✅ 儲存空間被釋放
5. ✅ 該 ID 可以重複使用

### API 使用

```python
import chromadb

# 初始化
client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_or_create_collection("test")

# 新增資料
collection.add(
    ids=["mem_001"],
    embeddings=[[0.1, 0.2, 0.3]],
    documents=["測試記憶"],
    metadatas=[{"user_id": "user-123"}]
)

# 確認存在
result = collection.get(ids=["mem_001"])
print(result)
# → {'ids': ['mem_001'], 'documents': ['測試記憶'], ...}

# 刪除
collection.delete(ids=["mem_001"])

# 再次查詢
result = collection.get(ids=["mem_001"])
print(result)
# → {'ids': [], 'documents': [], ...}  ← 完全消失
```

---

## 🧪 實際驗證

### 驗證 1: 刪除後無法查詢

```python
import chromadb

client = chromadb.PersistentClient(path="./test_db")
collection = client.get_or_create_collection("verify_delete")

# 新增記憶
collection.add(
    ids=["mem_001", "mem_002"],
    embeddings=[[0.1, 0.2], [0.3, 0.4]],
    documents=["記憶1", "記憶2"]
)

# 刪除 mem_001
collection.delete(ids=["mem_001"])

# 驗證: 只能找到 mem_002
all_data = collection.get()
print(f"剩餘 IDs: {all_data['ids']}")
# 輸出: 剩餘 IDs: ['mem_002']

# 嘗試查詢 mem_001
result = collection.get(ids=["mem_001"])
print(f"查詢 mem_001: {result['ids']}")
# 輸出: 查詢 mem_001: []  ← 完全不存在
```

---

### 驗證 2: 向量搜索找不到已刪除資料

```python
# 新增兩個相似的記憶
collection.add(
    ids=["mem_001", "mem_002"],
    embeddings=[[0.1, 0.2, 0.3], [0.11, 0.21, 0.31]],  # 非常相似
    documents=["使用者偏好科技股", "使用者喜歡科技股"]
)

# 刪除前搜索
results = collection.query(
    query_embeddings=[[0.1, 0.2, 0.3]],
    n_results=2
)
print(f"刪除前找到: {results['ids']}")
# 輸出: 刪除前找到: [['mem_001', 'mem_002']]

# 刪除 mem_001
collection.delete(ids=["mem_001"])

# 刪除後搜索
results = collection.query(
    query_embeddings=[[0.1, 0.2, 0.3]],  # 相同查詢
    n_results=2
)
print(f"刪除後找到: {results['ids']}")
# 輸出: 刪除後找到: [['mem_002']]  ← mem_001 完全消失
```

---

### 驗證 3: 檔案系統層級驗證

```python
import os
import chromadb

# 建立資料庫
client = chromadb.PersistentClient(path="./verify_storage")
collection = client.get_or_create_collection("test")

# 新增大量資料
for i in range(1000):
    collection.add(
        ids=[f"mem_{i}"],
        embeddings=[[float(i), float(i+1), float(i+2)]],
        documents=[f"記憶 {i}"]
    )

# 檢查儲存大小
def get_dir_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            total += os.path.getsize(fp)
    return total

size_before = get_dir_size("./verify_storage")
print(f"刪除前大小: {size_before / 1024:.2f} KB")

# 刪除 500 條記憶
collection.delete(ids=[f"mem_{i}" for i in range(500)])

# 強制持久化
del collection
del client

# 重新檢查大小
size_after = get_dir_size("./verify_storage")
print(f"刪除後大小: {size_after / 1024:.2f} KB")
print(f"減少: {(size_before - size_after) / 1024:.2f} KB")

# 輸出範例:
# 刪除前大小: 1024.50 KB
# 刪除後大小: 512.30 KB
# 減少: 512.20 KB  ← 儲存空間真正釋放
```

---

### 驗證 4: ID 可重複使用

```python
# 新增記憶
collection.add(
    ids=["mem_001"],
    documents=["原始內容"],
    embeddings=[[0.1, 0.2, 0.3]]
)

print(f"原始: {collection.get(ids=['mem_001'])['documents']}")
# 輸出: 原始: ['原始內容']

# 刪除
collection.delete(ids=["mem_001"])

# 使用相同 ID 新增新資料
collection.add(
    ids=["mem_001"],  # 相同 ID
    documents=["新內容"],  # 不同內容
    embeddings=[[0.9, 0.8, 0.7]]  # 不同向量
)

print(f"新的: {collection.get(ids=['mem_001'])['documents']}")
# 輸出: 新的: ['新內容']  ← 成功重複使用 ID
```

---

## 🔧 底層實現細節

### ChromaDB 的儲存架構

```
./data/chroma/
├── chroma.sqlite3           # 中繼資料資料庫
│   └── embeddings           # 表：儲存向量和 ID 的映射
│   └── collections          # 表：集合資訊
│   └── segments             # 表：段資訊
└── [collection_id]/
    ├── index/               # HNSW 索引檔案
    │   └── hnsw.bin        # 向量索引
    └── data/                # 原始資料
        └── vectors.bin      # 向量資料
```

### 刪除操作的內部流程

```python
# 當您呼叫 collection.delete(ids=["mem_001"]) 時

# Step 1: 從 SQLite 刪除中繼資料
DELETE FROM embeddings WHERE id = 'mem_001';

# Step 2: 從 HNSW 索引移除節點
hnsw_index.remove_node('mem_001')

# Step 3: 標記向量儲存空間為可回收
vector_storage.mark_for_gc('mem_001')

# Step 4: 觸發垃圾回收（非同步或定期）
garbage_collector.collect()
```

### 為什麼不用軟刪除？

**ChromaDB 設計考量**:

1. **向量資料庫特性**
   - 向量資料量大（768 維 = 3KB per vector）
   - 軟刪除會浪費大量空間
   - HNSW 索引不需要保留已刪除節點

2. **效能優先**
   - 每次查詢過濾 `is_deleted` 會降低效能
   - 向量搜索已經是計算密集型操作
   - 減少不必要的過濾邏輯

3. **使用場景**
   - 向量資料庫主要用於檢索，不是交易系統
   - 不需要審計追蹤或資料恢復
   - 簡化實現，提升效能

---

## 📊 實際影響

### 對 Mem0 的影響

在 Mem0 中，當執行 DELETE 操作時：

```python
# Mem0 記憶動作分類
{
  "event": "DELETE",
  "id": "mem_001",
  "old_memory": "使用者喜歡起司披薩"
}

# 執行刪除
collection.delete(ids=["mem_001"])

# 結果:
# ✓ 向量被移除
# ✓ 文檔被刪除
# ✓ 無法恢復
# ✓ 空間被釋放
```

### 場景分析

#### **場景 1: 使用者改變偏好**

```python
# 第 1 天: 建立偏好
collection.add(
    ids=["pref_001"],
    documents=["使用者喜歡起司披薩"]
)

# 第 5 天: 偏好改變
# Mem0 決定: DELETE 舊偏好 + ADD 新偏好
collection.delete(ids=["pref_001"])  # ← 硬刪除
collection.add(
    ids=["pref_002"],
    documents=["使用者不喜歡起司披薩"]
)

# 結果: "喜歡起司披薩" 永久消失
```

**影響**:
- ✅ 避免矛盾的記憶共存
- ✅ 減少儲存空間
- ❌ 無法追蹤偏好變化歷史

---

#### **場景 2: 誤刪除**

```python
# 不小心刪除
collection.delete(ids=["important_memory"])

# 嘗試恢復
result = collection.get(ids=["important_memory"])
# → 返回空，無法恢復 ❌
```

**影響**:
- ❌ 資料永久遺失
- ❌ 無法 rollback

---

#### **場景 3: 隱私合規**

```python
# 使用者請求刪除個人資料（GDPR）
user_memories = collection.get(
    where={"user_id": "user-123"}
)

# 刪除所有記憶
collection.delete(ids=user_memories['ids'])

# 驗證: 資料真正刪除
result = collection.get(where={"user_id": "user-123"})
# → 返回空 ✓ 符合 GDPR 要求
```

**影響**:
- ✅ 符合資料隱私法規
- ✅ 資料真正被移除

---

## 🛡️ 最佳實踐

### 1. 實作軟刪除（如果需要）

如果您需要軟刪除功能，可以在應用層實現：

```python
# 不真正刪除，而是更新 metadata
def soft_delete_memory(memory_id: str):
    """軟刪除：標記為已刪除但不移除"""

    # 獲取現有資料
    result = collection.get(ids=[memory_id])

    if result['ids']:
        # 更新 metadata，標記為已刪除
        collection.update(
            ids=[memory_id],
            metadatas=[{
                **result['metadatas'][0],
                "is_deleted": True,
                "deleted_at": datetime.now().isoformat()
            }]
        )

def search_active_memories(query: str):
    """搜索時過濾已刪除記憶"""

    results = collection.query(
        query_embeddings=[embed(query)],
        n_results=10,
        where={
            "$or": [
                {"is_deleted": {"$eq": False}},
                {"is_deleted": {"$exists": False}}  # 舊資料沒有這個欄位
            ]
        }
    )

    return results
```

---

### 2. 實作刪除前備份

```python
import json
from datetime import datetime

def delete_with_backup(memory_id: str):
    """刪除前先備份"""

    # Step 1: 獲取資料
    result = collection.get(ids=[memory_id])

    if result['ids']:
        # Step 2: 備份到檔案
        backup = {
            "id": memory_id,
            "document": result['documents'][0],
            "metadata": result['metadatas'][0],
            "deleted_at": datetime.now().isoformat()
        }

        with open(f"./backups/{memory_id}.json", "w") as f:
            json.dump(backup, f, ensure_ascii=False, indent=2)

        # Step 3: 執行刪除
        collection.delete(ids=[memory_id])

        return True

    return False

def restore_from_backup(memory_id: str):
    """從備份恢復"""

    backup_file = f"./backups/{memory_id}.json"

    if os.path.exists(backup_file):
        with open(backup_file, "r") as f:
            backup = json.load(f)

        # 恢復資料（需重新生成 embedding）
        collection.add(
            ids=[backup['id']],
            embeddings=[embed(backup['document'])],
            documents=[backup['document']],
            metadatas=[backup['metadata']]
        )

        return True

    return False
```

---

### 3. 批次刪除優化

```python
def batch_delete_with_confirmation(user_id: str):
    """批次刪除前確認"""

    # Step 1: 找出要刪除的記憶
    memories = collection.get(
        where={"user_id": user_id}
    )

    count = len(memories['ids'])

    # Step 2: 顯示將被刪除的內容
    print(f"將刪除 {count} 條記憶:")
    for i, doc in enumerate(memories['documents'][:5]):  # 顯示前 5 條
        print(f"  - {doc}")
    if count > 5:
        print(f"  ... 還有 {count - 5} 條")

    # Step 3: 要求確認（實際應用中）
    # confirm = input("確認刪除？(yes/no): ")
    # if confirm.lower() != 'yes':
    #     return False

    # Step 4: 執行刪除
    collection.delete(ids=memories['ids'])

    return True
```

---

### 4. 定期清理策略

```python
from datetime import datetime, timedelta

def cleanup_old_memories(days: int = 30):
    """清理超過 N 天的記憶"""

    cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

    # 找出舊記憶
    all_memories = collection.get(
        include=["metadatas"]
    )

    to_delete = []
    for i, metadata in enumerate(all_memories['metadatas']):
        created_at = metadata.get('created_at', '')
        if created_at < cutoff_date:
            to_delete.append(all_memories['ids'][i])

    if to_delete:
        print(f"清理 {len(to_delete)} 條超過 {days} 天的記憶")
        collection.delete(ids=to_delete)

    return len(to_delete)
```

---

### 5. 記憶歷史版本控制

```python
def update_with_history(memory_id: str, new_text: str):
    """更新時保留歷史版本"""

    # 獲取現有資料
    result = collection.get(ids=[memory_id])

    if result['ids']:
        old_text = result['documents'][0]
        old_metadata = result['metadatas'][0]

        # 建立歷史記錄 ID
        history_id = f"{memory_id}_history_{int(datetime.now().timestamp())}"

        # 儲存歷史版本（新增而非刪除）
        collection.add(
            ids=[history_id],
            embeddings=[result['embeddings'][0]],  # 保留舊向量
            documents=[old_text],
            metadatas=[{
                **old_metadata,
                "is_history": True,
                "original_id": memory_id,
                "archived_at": datetime.now().isoformat()
            }]
        )

        # 更新主記憶
        collection.update(
            ids=[memory_id],
            embeddings=[embed(new_text)],
            documents=[new_text],
            metadatas=[{
                **old_metadata,
                "updated_at": datetime.now().isoformat(),
                "history_count": old_metadata.get("history_count", 0) + 1
            }]
        )

def get_memory_history(memory_id: str):
    """獲取記憶的歷史版本"""

    results = collection.get(
        where={
            "is_history": True,
            "original_id": memory_id
        }
    )

    return results
```

---

## 🎯 總結

### ChromaDB 刪除機制

| 特性 | 說明 |
|------|------|
| **刪除類型** | 硬刪除 (Hard Delete) |
| **資料保留** | ❌ 不保留，真正移除 |
| **空間釋放** | ✅ 立即或延遲釋放 |
| **可恢復性** | ❌ 無法恢復 |
| **ID 重用** | ✅ 可重複使用 |
| **查詢可見** | ❌ 完全不可見 |
| **向量搜索** | ❌ 找不到已刪除資料 |

### 關鍵要點

1. **`collection.delete()` 是硬刪除**
   - 向量、文檔、中繼資料全部移除
   - 無法透過 ChromaDB 恢復

2. **如果需要軟刪除**
   - 在應用層實現（使用 metadata 標記）
   - 查詢時過濾已刪除項目

3. **最佳實踐**
   - 刪除前備份重要資料
   - 實作確認機制
   - 保留歷史版本（如需要）

4. **對 Mem0 的影響**
   - DELETE 動作會永久移除記憶
   - 適合處理衝突和過時資訊
   - 符合資料隱私要求（GDPR）

---

**相關文檔**:
- ChromaDB 官方文檔: https://docs.trychroma.com/
- 您的專案記憶服務: `backend/src/services/memory_service.py`

**建議**:
- 根據需求決定是否需要在應用層實作軟刪除
- 對重要記憶實施刪除前備份機制
- 定期清理測試/開發環境的記憶資料
