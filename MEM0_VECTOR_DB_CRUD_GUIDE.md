# Mem0 向量資料庫 CRUD 詳解

**文件目的**: 深入解析 Mem0 如何使用向量資料庫實現記憶的 CRUD 操作
**版本**: 1.0.0
**日期**: 2025-11-05

---

## 📋 目錄

1. [核心概念：向量相似度搜索](#核心概念向量相似度搜索)
2. [記憶動作分類機制](#記憶動作分類機制)
3. [ChromaDB CRUD 實現](#chromadb-crud-實現)
4. [完整流程實例](#完整流程實例)
5. [實際程式碼分析](#實際程式碼分析)
6. [效能優化](#效能優化)

---

## 🔍 核心概念：向量相似度搜索

### 什麼是向量相似度？

在理解 CRUD 之前，先理解向量搜索的基礎。

**向量化**:
```python
# 文本 → 向量（高維空間中的點）
text1 = "使用者偏好科技股"
embedding1 = embed(text1)
# → [0.23, -0.45, 0.67, 0.12, -0.89, ...]  (768 維)

text2 = "使用者喜歡科技類股票"  # 語義相似
embedding2 = embed(text2)
# → [0.21, -0.43, 0.65, 0.14, -0.87, ...]  (向量相近)

text3 = "明天要去吃飯"  # 語義不同
embedding3 = embed(text3)
# → [0.78, 0.34, -0.56, -0.23, 0.45, ...]  (向量距離遠)
```

**相似度計算**:
```python
# 餘弦相似度 (Cosine Similarity)
similarity(embedding1, embedding2) = 0.95  # 非常相似
similarity(embedding1, embedding3) = 0.12  # 不相似
```

**為什麼重要？**
- 找出語義相似的記憶
- 決定是新增還是更新現有記憶
- 檢測記憶衝突

---

## 🎯 記憶動作分類機制

### 階段 2 的核心：決定 ADD/UPDATE/DELETE/NONE

當 Mem0 提取出新事實後，需要決定如何處理。這是通過**第二次 LLM 呼叫**實現的。

### 2.1 完整流程

```
[階段 1] 提取事實
   ↓
新事實: "使用者偏好 AI 相關科技股"
   ↓
[階段 2] 搜索相似記憶
   ↓
步驟 2.1: 生成查詢向量
query_embedding = embed("使用者偏好 AI 相關科技股")
   ↓
步驟 2.2: 在 ChromaDB 中搜索
similar_memories = chroma.search(
    embedding=query_embedding,
    n_results=5,
    where={"user_id": "user-123"}
)
   ↓
找到相似記憶:
[
  {
    "id": "mem_001",
    "content": "使用者偏好科技股",
    "distance": 0.15  # 相似度高
  },
  {
    "id": "mem_002",
    "content": "使用者風險承受度為中等",
    "distance": 0.65  # 相似度低
  }
]
   ↓
步驟 2.3: 呼叫 LLM 分類動作
   ↓
LLM Prompt:
"""
現有記憶:
[
  {"id": "mem_001", "text": "使用者偏好科技股"},
  {"id": "mem_002", "text": "使用者風險承受度為中等"}
]

新提取的事實:
["使用者偏好 AI 相關科技股"]

請對每個事實決定動作:
- ADD: 全新信息
- UPDATE: 更新現有記憶（保留 id，更新 text）
- DELETE: 刪除衝突記憶
- NONE: 已存在，不需改變

返回 JSON:
{
  "actions": [
    {
      "event": "UPDATE",
      "id": "mem_001",
      "text": "使用者偏好 AI 相關科技股",
      "old_memory": "使用者偏好科技股"
    }
  ]
}
"""
   ↓
LLM 返回決策
   ↓
步驟 2.4: 執行 CRUD 操作
```

---

### 2.2 動作分類的詳細規則

#### **ADD (新增)**

**觸發條件**:
```
新事實包含「全新信息」，現有記憶中沒有相關內容
```

**判斷邏輯**:
```python
# Prompt 中的指示
"""
如果新事實是全新信息，不在現有記憶中，則 ADD。

範例:
現有記憶: ["使用者偏好科技股"]
新事實: "使用者計劃在 2025 年投資 10 萬元"
動作: ADD  ← 完全不同的主題
"""
```

**執行操作**:
```python
# 生成新 ID
new_id = uuid.uuid4()

# 添加到 ChromaDB
chroma.add(
    ids=[str(new_id)],
    embeddings=[embed(new_fact)],
    documents=[new_fact],
    metadatas=[{
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z"
    }]
)
```

**實際範例**:
```json
{
  "event": "ADD",
  "id": "mem_003",  // 新生成的 ID
  "text": "使用者計劃在 2025 年投資 10 萬元"
}
```

---

#### **UPDATE (更新)**

**觸發條件**:
```
新事實是對現有記憶的「細化」或「補充」
```

**判斷邏輯**:
```python
# Prompt 中的指示
"""
如果新事實包含更詳細的信息，則 UPDATE。

範例 1: 細化
現有記憶: "使用者偏好科技股"
新事實: "使用者偏好 AI 相關科技股"
動作: UPDATE  ← 更具體的信息

範例 2: 補充
現有記憶: "使用者喜歡披薩"
新事實: "使用者喜歡起司和雞肉披薩"
動作: UPDATE  ← 添加了細節

範例 3: 不該更新
現有記憶: "使用者喜歡披薩"
新事實: "使用者愛披薩"
動作: NONE  ← 語義相同，只是措辭不同
"""
```

**執行操作**:
```python
# 更新 ChromaDB（保留原 ID）
chroma.update(
    ids=["mem_001"],
    embeddings=[embed(new_text)],  # 重新生成向量
    documents=[new_text],
    metadatas=[{
        "user_id": "user-123",
        "category": "preference",
        "updated_at": "2025-11-05T10:30:00Z",
        "old_memory": old_text  # 保存舊內容
    }]
)
```

**實際範例**:
```json
{
  "event": "UPDATE",
  "id": "mem_001",  // 保留原始 ID
  "text": "使用者偏好 AI 相關科技股",
  "old_memory": "使用者偏好科技股"  // 記錄舊值
}
```

---

#### **DELETE (刪除)**

**觸發條件**:
```
新事實與現有記憶「衝突」或「否定」
```

**判斷邏輯**:
```python
# Prompt 中的指示
"""
如果新事實與現有記憶矛盾，則 DELETE 舊記憶。

範例 1: 偏好改變
現有記憶: "使用者喜歡起司披薩"
新事實: "使用者不喜歡起司披薩"
動作: DELETE  ← 明確否定

範例 2: 風險承受度改變
現有記憶: "使用者風險承受度為高"
新事實: "使用者現在傾向保守投資，風險承受度為低"
動作: DELETE 舊記憶 + ADD 新記憶
"""
```

**執行操作**:
```python
# 刪除 ChromaDB 中的記憶
chroma.delete(
    ids=["mem_001"]
)

# 通常會搭配 ADD 新記憶
chroma.add(
    ids=["mem_004"],
    embeddings=[embed(new_fact)],
    documents=[new_fact],
    metadatas=[{...}]
)
```

**實際範例**:
```json
{
  "event": "DELETE",
  "id": "mem_001",  // 要刪除的記憶 ID
  "old_memory": "使用者喜歡起司披薩"
}
```

---

#### **NONE (不改變)**

**觸發條件**:
```
新事實與現有記憶「語義相同」，只是措辭不同
```

**判斷邏輯**:
```python
# Prompt 中的指示
"""
如果新事實與現有記憶表達相同意思，則 NONE。

範例 1: 同義表達
現有記憶: "使用者喜歡披薩"
新事實: "使用者愛披薩"
動作: NONE  ← 喜歡 = 愛

範例 2: 重複陳述
現有記憶: "使用者偏好科技股"
新事實: "我喜歡科技股"
動作: NONE  ← 已經記錄過了
"""
```

**執行操作**:
```python
# 不執行任何 CRUD 操作
pass
```

**實際範例**:
```json
{
  "event": "NONE",
  "reason": "信息已存在於記憶中"
}
```

---

### 2.3 記憶動作分類的 Prompt

**完整 Prompt 結構**:

```python
MEMORY_UPDATE_PROMPT = """
您是一個記憶管理系統。您的任務是決定如何處理新提取的事實。

## 輸入
1. 現有記憶列表:
   [
     {"id": "mem_001", "text": "使用者偏好科技股"},
     {"id": "mem_002", "text": "使用者風險承受度為中等"}
   ]

2. 新提取的事實:
   ["使用者偏好 AI 相關科技股"]

## 決策規則

### ADD (新增)
- 條件: 新事實是全新信息，與現有記憶無關
- 操作: 生成新 ID，添加記憶
- 範例:
  現有: ["使用者偏好科技股"]
  新的: ["使用者計劃投資房地產"]
  → ADD (不同主題)

### UPDATE (更新)
- 條件: 新事實是對現有記憶的細化或補充
- 操作: 保留原 ID，更新文本，記錄舊值
- 範例:
  現有: ["使用者偏好科技股"]
  新的: ["使用者偏好 AI 相關科技股"]
  → UPDATE (更具體)

### DELETE (刪除)
- 條件: 新事實與現有記憶衝突或否定
- 操作: 刪除衝突的記憶
- 範例:
  現有: ["使用者喜歡起司披薩"]
  新的: ["使用者不喜歡起司披薩"]
  → DELETE

### NONE (不改變)
- 條件: 新事實與現有記憶語義相同
- 操作: 不執行任何操作
- 範例:
  現有: ["使用者喜歡披薩"]
  新的: ["使用者愛披薩"]
  → NONE (同義)

## 輸出格式

請以 JSON 格式返回決策:

{
  "actions": [
    {
      "event": "UPDATE",
      "id": "mem_001",
      "text": "使用者偏好 AI 相關科技股",
      "old_memory": "使用者偏好科技股"
    }
  ]
}

## 重要規則
1. 保留原始 ID (除了 ADD 操作)
2. UPDATE 時必須記錄 old_memory
3. 優先選擇更保守的動作 (NONE > UPDATE > ADD)
4. 只在明確衝突時使用 DELETE
"""
```

---

## 💾 ChromaDB CRUD 實現

### 3.1 ChromaDB 基礎架構

**初始化**:

```python
# Mem0 初始化 ChromaDB
import chromadb

# 方式 1: 本地持久化
client = chromadb.PersistentClient(path="./data/chroma")

# 方式 2: 記憶體模式 (測試用)
client = chromadb.Client()

# 建立或獲取集合
collection = client.get_or_create_collection(
    name="investment_memories",
    metadata={"description": "投資偏好記憶"}
)
```

**您的專案配置**:
```python
# backend/src/services/memory_service.py:54-60
"vector_store": {
    "provider": "chroma",
    "config": {
        "collection_name": "investment_memories",
        "path": settings.chroma_path,  # ./data/chroma
    },
}
```

---

### 3.2 Create (新增記憶)

**操作**: 添加新的向量和文檔到集合

```python
def add_memory(text: str, user_id: str, metadata: dict = None):
    """新增記憶"""

    # Step 1: 生成唯一 ID
    memory_id = str(uuid.uuid4())

    # Step 2: 生成向量嵌入
    embedding = embeddings_api.embed(text)
    # → [0.234, -0.456, 0.678, ..., 0.123]  (768 維)

    # Step 3: 準備中繼資料
    meta = {
        "user_id": user_id,
        "category": metadata.get("category", "general"),
        "created_at": datetime.now().isoformat(),
        **(metadata or {})
    }

    # Step 4: 添加到 ChromaDB
    collection.add(
        ids=[memory_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[meta]
    )

    return memory_id
```

**實際範例**:
```python
# 新增記憶
memory_id = add_memory(
    text="使用者偏好科技股",
    user_id="user-123",
    metadata={"category": "preference"}
)

# ChromaDB 儲存的結構
{
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "embedding": [0.234, -0.456, 0.678, ...],
    "document": "使用者偏好科技股",
    "metadata": {
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z"
    }
}
```

---

### 3.3 Read (搜索記憶)

**操作**: 使用向量相似度搜索找出相關記憶

```python
def search_memories(query: str, user_id: str, top_k: int = 5):
    """搜索相關記憶"""

    # Step 1: 生成查詢向量
    query_embedding = embeddings_api.embed(query)

    # Step 2: 在 ChromaDB 中搜索
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={
            "user_id": user_id  # 只搜索該使用者的記憶
        },
        include=["documents", "metadatas", "distances"]
    )

    # Step 3: 處理結果
    memories = []
    for i in range(len(results['ids'][0])):
        memories.append({
            "id": results['ids'][0][i],
            "content": results['documents'][0][i],
            "metadata": results['metadatas'][0][i],
            "distance": results['distances'][0][i],  # 越小越相似
            "relevance": 1 - results['distances'][0][i]  # 轉換為相關性分數
        })

    return memories
```

**實際範例**:
```python
# 搜索記憶
memories = search_memories(
    query="投資建議",
    user_id="user-123",
    top_k=5
)

# 返回結果
[
    {
        "id": "mem_001",
        "content": "使用者偏好科技股",
        "metadata": {"category": "preference"},
        "distance": 0.12,  # 相似度高
        "relevance": 0.88
    },
    {
        "id": "mem_002",
        "content": "使用者風險承受度為中等",
        "metadata": {"category": "preference"},
        "distance": 0.18,
        "relevance": 0.82
    },
    ...
]
```

**向量搜索的工作原理**:

```
查詢: "投資建議"
   ↓
生成查詢向量: [0.25, -0.47, 0.69, ...]
   ↓
在 ChromaDB 中計算所有記憶向量的相似度:
   mem_001: [0.23, -0.45, 0.67, ...] → distance: 0.12 ✓ 相似
   mem_002: [0.28, -0.48, 0.71, ...] → distance: 0.18 ✓ 相似
   mem_003: [0.78, 0.34, -0.56, ...] → distance: 0.89 ✗ 不相似
   ↓
返回 top_k=5 個最相似的記憶 (distance 最小的)
```

---

### 3.4 Update (更新記憶)

**操作**: 更新現有記憶的內容和向量

```python
def update_memory(memory_id: str, new_text: str, old_text: str = None):
    """更新記憶"""

    # Step 1: 生成新的向量嵌入
    new_embedding = embeddings_api.embed(new_text)

    # Step 2: 準備更新的中繼資料
    updated_metadata = {
        "updated_at": datetime.now().isoformat(),
    }

    # 如果提供了舊文本，保存它
    if old_text:
        updated_metadata["old_memory"] = old_text

    # Step 3: 更新 ChromaDB
    collection.update(
        ids=[memory_id],
        embeddings=[new_embedding],  # 新向量
        documents=[new_text],        # 新文本
        metadatas=[updated_metadata]
    )

    return memory_id
```

**實際範例**:
```python
# 更新前
{
    "id": "mem_001",
    "document": "使用者偏好科技股",
    "embedding": [0.23, -0.45, 0.67, ...]
}

# 執行更新
update_memory(
    memory_id="mem_001",
    new_text="使用者偏好 AI 相關科技股",
    old_text="使用者偏好科技股"
)

# 更新後
{
    "id": "mem_001",  # ID 不變
    "document": "使用者偏好 AI 相關科技股",  # 文本更新
    "embedding": [0.31, -0.52, 0.71, ...],  # 向量重新生成
    "metadata": {
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z",
        "updated_at": "2025-11-05T14:20:00Z",
        "old_memory": "使用者偏好科技股"  # 保存舊值
    }
}
```

**為什麼需要重新生成向量？**
```
舊文本: "使用者偏好科技股"
舊向量: [0.23, -0.45, 0.67, ...]

新文本: "使用者偏好 AI 相關科技股"
新向量: [0.31, -0.52, 0.71, ...]  ← 語義不同，向量也不同

如果不更新向量:
- 搜索 "AI 相關投資" 時找不到這條記憶
- 因為舊向量對應的是 "科技股"，不包含 "AI" 的語義
```

---

### 3.5 Delete (刪除記憶)

**操作**: 從 ChromaDB 中移除記憶

```python
def delete_memory(memory_id: str):
    """刪除記憶"""

    # 從 ChromaDB 刪除
    collection.delete(
        ids=[memory_id]
    )

    return True
```

**實際範例**:
```python
# 刪除前
collection.get(ids=["mem_001"])
# → {"id": "mem_001", "document": "使用者喜歡起司披薩", ...}

# 執行刪除
delete_memory("mem_001")

# 刪除後
collection.get(ids=["mem_001"])
# → 拋出異常或返回空結果
```

**批次刪除**:
```python
def delete_all_memories(user_id: str):
    """刪除某使用者的所有記憶"""

    # Step 1: 找出該使用者的所有記憶
    results = collection.get(
        where={"user_id": user_id}
    )

    # Step 2: 批次刪除
    if results['ids']:
        collection.delete(
            ids=results['ids']
        )

    return len(results['ids'])
```

---

### 3.6 Get (獲取單一記憶)

**操作**: 根據 ID 獲取特定記憶

```python
def get_memory(memory_id: str):
    """獲取單一記憶"""

    result = collection.get(
        ids=[memory_id],
        include=["documents", "metadatas", "embeddings"]
    )

    if not result['ids']:
        return None

    return {
        "id": result['ids'][0],
        "content": result['documents'][0],
        "metadata": result['metadatas'][0],
        "embedding": result['embeddings'][0]
    }
```

---

## 🔄 完整流程實例

### 場景：使用者表達投資偏好的完整過程

讓我們追蹤一次完整的記憶處理流程。

---

### **第 1 天：首次對話**

**使用者輸入**:
```
"我偏好科技股，風險承受度中等"
```

#### 步驟 1: 事實提取

```python
# Mem0 呼叫 Gemini 提取事實
facts = [
    "使用者偏好科技股",
    "使用者風險承受度為中等"
]
```

#### 步驟 2: 處理第一個事實

**2.1 搜索現有記憶**:
```python
query_embedding = embed("使用者偏好科技股")

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": "user-123"}
)

# 返回: [] (空，因為是首次對話)
```

**2.2 LLM 決策**:
```python
# Prompt
"""
現有記憶: []
新事實: "使用者偏好科技股"
決定動作?
"""

# LLM 返回
{
  "event": "ADD",
  "text": "使用者偏好科技股"
}
```

**2.3 執行 ADD**:
```python
collection.add(
    ids=["mem_001"],
    embeddings=[embed("使用者偏好科技股")],
    documents=["使用者偏好科技股"],
    metadatas=[{
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z"
    }]
)
```

#### 步驟 3: 處理第二個事實

同樣流程，最終執行 ADD:
```python
collection.add(
    ids=["mem_002"],
    embeddings=[embed("使用者風險承受度為中等")],
    documents=["使用者風險承受度為中等"],
    metadatas=[{...}]
)
```

#### 結果：ChromaDB 中的記憶

```python
collection.get()
# 返回:
[
    {
        "id": "mem_001",
        "document": "使用者偏好科技股",
        "embedding": [0.23, -0.45, 0.67, ...],
        "metadata": {"user_id": "user-123", ...}
    },
    {
        "id": "mem_002",
        "document": "使用者風險承受度為中等",
        "embedding": [0.28, -0.48, 0.71, ...],
        "metadata": {"user_id": "user-123", ...}
    }
]
```

---

### **第 2 天：細化偏好**

**使用者輸入**:
```
"我現在特別看好 AI 相關的科技股"
```

#### 步驟 1: 事實提取

```python
facts = ["使用者偏好 AI 相關科技股"]
```

#### 步驟 2: 搜索現有記憶

```python
query_embedding = embed("使用者偏好 AI 相關科技股")

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": "user-123"}
)

# 返回:
[
    {
        "id": "mem_001",
        "document": "使用者偏好科技股",
        "distance": 0.15  # 非常相似！
    },
    {
        "id": "mem_002",
        "document": "使用者風險承受度為中等",
        "distance": 0.68  # 不太相關
    }
]
```

#### 步驟 3: LLM 決策

```python
# Prompt
"""
現有記憶:
[
  {"id": "mem_001", "text": "使用者偏好科技股"},
  {"id": "mem_002", "text": "使用者風險承受度為中等"}
]

新事實: "使用者偏好 AI 相關科技股"

決定動作?
"""

# LLM 分析
# "使用者偏好 AI 相關科技股" 是對 "使用者偏好科技股" 的細化
# 提供了更具體的信息（AI 相關）

# LLM 返回
{
  "event": "UPDATE",
  "id": "mem_001",
  "text": "使用者偏好 AI 相關科技股",
  "old_memory": "使用者偏好科技股"
}
```

#### 步驟 4: 執行 UPDATE

```python
collection.update(
    ids=["mem_001"],
    embeddings=[embed("使用者偏好 AI 相關科技股")],
    documents=["使用者偏好 AI 相關科技股"],
    metadatas=[{
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z",
        "updated_at": "2025-11-06T14:20:00Z",
        "old_memory": "使用者偏好科技股"
    }]
)
```

#### 結果：記憶已更新

```python
collection.get(ids=["mem_001"])
# 返回:
{
    "id": "mem_001",  # ID 不變
    "document": "使用者偏好 AI 相關科技股",  # 內容更新
    "embedding": [0.31, -0.52, 0.71, ...],  # 向量重新生成
    "metadata": {
        "updated_at": "2025-11-06T14:20:00Z",
        "old_memory": "使用者偏好科技股"
    }
}
```

---

### **第 3 天：偏好改變**

**使用者輸入**:
```
"我現在不想投資科技股了，想轉向價值股"
```

#### 步驟 1: 事實提取

```python
facts = ["使用者不再偏好科技股", "使用者偏好價值股"]
```

#### 步驟 2: 處理第一個事實 - 衝突檢測

```python
query_embedding = embed("使用者不再偏好科技股")

results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": "user-123"}
)

# 返回:
[
    {
        "id": "mem_001",
        "document": "使用者偏好 AI 相關科技股",
        "distance": 0.12  # 相關但衝突！
    }
]
```

#### 步驟 3: LLM 決策

```python
# Prompt
"""
現有記憶:
[{"id": "mem_001", "text": "使用者偏好 AI 相關科技股"}]

新事實: "使用者不再偏好科技股"

決定動作?
"""

# LLM 分析
# 新事實與現有記憶直接衝突
# "不再偏好" 否定了 "偏好"

# LLM 返回
{
  "event": "DELETE",
  "id": "mem_001",
  "old_memory": "使用者偏好 AI 相關科技股"
}
```

#### 步驟 4: 執行 DELETE

```python
collection.delete(ids=["mem_001"])
```

#### 步驟 5: 處理第二個事實

```python
# "使用者偏好價值股" 是新信息
# 執行 ADD

collection.add(
    ids=["mem_003"],
    embeddings=[embed("使用者偏好價值股")],
    documents=["使用者偏好價值股"],
    metadatas=[{...}]
)
```

#### 結果：記憶已替換

```python
collection.get(where={"user_id": "user-123"})
# 返回:
[
    {
        "id": "mem_002",
        "document": "使用者風險承受度為中等"  # 保留
    },
    {
        "id": "mem_003",
        "document": "使用者偏好價值股"  # 新增
    }
    # mem_001 已刪除
]
```

---

## 💻 實際程式碼分析

### 您專案中的實現

#### 搜索記憶：`backend/src/services/memory_service.py:108-227`

```python
@classmethod
def search_memories(
    cls,
    user_id: str,
    query: str,
    top_k: int = 5,
) -> List[Dict]:
    """搜索記憶"""

    # Step 1: 呼叫 Mem0 API
    results = cls._mem0_client.search(
        query=query,
        user_id=user_id,
        limit=top_k,
    )

    # Step 2: Mem0 內部執行
    # 2.1 生成查詢向量
    query_embedding = google_embeddings.embed(query)

    # 2.2 在 ChromaDB 中搜索
    chroma_results = chroma_collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where={"user_id": user_id}
    )

    # 2.3 返回結果
    return chroma_results
```

**實際呼叫**:
```python
# backend/src/services/conversation_service.py
memories = MemoryService.search_memories(
    user_id="user-123",
    query="投資建議",  # 使用者訊息作為查詢
    top_k=5
)

# 返回相關記憶
# [
#   {"id": "mem_001", "content": "使用者偏好科技股", ...},
#   {"id": "mem_002", "content": "使用者風險承受度為中等", ...}
# ]
```

---

#### 添加記憶：`backend/src/services/memory_service.py:276-366`

```python
@classmethod
def add_memory_from_message(
    cls,
    user_id: str,
    message_content: str,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """從訊息中自動擷取並儲存記憶"""

    # 呼叫 Mem0
    result = cls._mem0_client.add(
        messages=[{
            "role": "user",
            "content": message_content,
        }],
        user_id=user_id,
        metadata=metadata,
    )

    # Mem0 內部流程:
    # 1. LLM 提取事實
    # 2. 對每個事實:
    #    2.1 搜索現有記憶 (向量搜索)
    #    2.2 LLM 決策動作 (ADD/UPDATE/DELETE/NONE)
    #    2.3 執行 ChromaDB CRUD 操作

    return result.get("memory_id")
```

---

## ⚡ 效能優化

### 向量搜索優化

#### 1. HNSW 索引算法

ChromaDB 使用 HNSW (Hierarchical Navigable Small World) 算法：

```
傳統搜索: O(n) - 需要比較所有向量
HNSW: O(log n) - 使用圖結構快速導航

範例:
1,000,000 個向量
- 傳統: 需要 1,000,000 次比較
- HNSW: 約 20-30 次比較

速度提升: ~50,000x
```

#### 2. 批次操作

```python
# 不好: 逐個添加
for fact in facts:
    collection.add(ids=[id], embeddings=[embed(fact)], ...)

# 好: 批次添加
collection.add(
    ids=ids,
    embeddings=[embed(f) for f in facts],
    documents=facts,
    metadatas=metas
)
```

#### 3. 過濾優化

```python
# 使用 where 子句過濾
results = collection.query(
    query_embeddings=[query_embedding],
    where={"user_id": "user-123"},  # 先過濾再搜索
    n_results=5
)
```

---

### 記憶管理優化

#### 1. 限制記憶數量

```python
# 定期清理舊記憶
def cleanup_old_memories(user_id: str, keep_latest: int = 1000):
    # 獲取所有記憶
    all_memories = collection.get(
        where={"user_id": user_id}
    )

    # 如果超過限制
    if len(all_memories['ids']) > keep_latest:
        # 按時間排序，刪除最舊的
        sorted_by_time = sorted(
            all_memories['metadatas'],
            key=lambda x: x['created_at']
        )

        to_delete = sorted_by_time[:-keep_latest]
        collection.delete(ids=[m['id'] for m in to_delete])
```

#### 2. 記憶壓縮

```python
# 定期合併相似記憶
def merge_similar_memories(user_id: str, threshold: float = 0.95):
    memories = collection.get(where={"user_id": user_id})

    for i, mem1 in enumerate(memories):
        for mem2 in memories[i+1:]:
            similarity = compute_similarity(
                mem1['embedding'],
                mem2['embedding']
            )

            if similarity > threshold:
                # 合併記憶
                merged_text = llm.merge(mem1['text'], mem2['text'])
                update_memory(mem1['id'], merged_text)
                delete_memory(mem2['id'])
```

---

## 🎯 總結

### Mem0 向量資料庫 CRUD 的核心機制

1. **Create (ADD)**:
   - 生成向量 → ChromaDB.add()
   - 用於全新信息

2. **Read (SEARCH)**:
   - 查詢向量 → ChromaDB.query()
   - 使用 HNSW 快速搜索
   - 返回最相似的記憶

3. **Update (UPDATE)**:
   - 保留 ID → 重新生成向量 → ChromaDB.update()
   - 用於細化或補充現有記憶

4. **Delete (DELETE)**:
   - ChromaDB.delete()
   - 用於處理衝突或過時記憶

### 決策流程

```
新事實 → 向量搜索 → 找到相似記憶 → LLM 比較 → 決定動作
   ↓
ADD: 全新信息
UPDATE: 細化補充
DELETE: 衝突否定
NONE: 重複相同
```

### 關鍵優勢

- ✅ **智能去重**: 自動檢測重複記憶
- ✅ **自動更新**: 記憶隨時間演進
- ✅ **衝突解決**: 自動處理矛盾信息
- ✅ **高效搜索**: HNSW 算法快速檢索

---

**參考資源**:
- ChromaDB 文檔: https://docs.trychroma.com/
- Mem0 GitHub: https://github.com/mem0ai/mem0
- 您的專案: `backend/src/services/memory_service.py`

**下一步建議**:
- 實際觀察 ChromaDB 資料庫內容: `./data/chroma/`
- 測試不同場景的記憶操作
- 優化向量搜索參數 (top_k, threshold)
- 實作記憶清理和壓縮機制
