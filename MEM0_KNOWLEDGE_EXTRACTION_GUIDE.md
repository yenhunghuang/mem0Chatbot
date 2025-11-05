# Mem0 知識提取與標準化機制 - 深度解析

**文件目的**: 詳細解釋 Mem0 如何從對話中「提取知識 → 標準化」
**版本**: 1.0.0
**日期**: 2025-11-05

---

## 📋 目錄

1. [核心流程概覽](#核心流程概覽)
2. [階段一：事實提取 (Fact Extraction)](#階段一事實提取-fact-extraction)
3. [階段二：記憶動作分類 (Memory Action Classification)](#階段二記憶動作分類-memory-action-classification)
4. [階段三：向量化與儲存](#階段三向量化與儲存)
5. [Prompt 工程詳解](#prompt-工程詳解)
6. [實際範例演示](#實際範例演示)
7. [您專案中的運作](#您專案中的運作)
8. [與傳統 RAG 的對比](#與傳統-rag-的對比)

---

## 🔄 核心流程概覽

### 完整流程圖

```
使用者對話
"我偏好科技股，風險承受度中等，我明天要去吃飯"
   ↓
┌─────────────────────────────────────────────────────────┐
│  階段 1: 事實提取 (Fact Extraction)                      │
│  使用 LLM + 特殊 Prompt                                  │
└─────────────────────────────────────────────────────────┘
   ↓
提取結果 (JSON):
{
  "facts": [
    "使用者偏好科技股",
    "使用者風險承受度為中等"
  ]
  // 注意: "明天要去吃飯" 被過濾掉了
}
   ↓
┌─────────────────────────────────────────────────────────┐
│  階段 2: 記憶動作分類 (Memory Action Classification)     │
│  比較新事實 vs 現有記憶                                  │
└─────────────────────────────────────────────────────────┘
   ↓
動作決策:
- "使用者偏好科技股" → ADD (新記憶)
- "使用者風險承受度為中等" → ADD (新記憶)
   ↓
┌─────────────────────────────────────────────────────────┐
│  階段 3: 向量化與儲存                                     │
│  Embeddings + ChromaDB                                   │
└─────────────────────────────────────────────────────────┘
   ↓
儲存到向量資料庫:
{
  "id": "mem_001",
  "content": "使用者偏好科技股",
  "embedding": [0.23, -0.45, 0.67, ...],
  "metadata": {
    "user_id": "user-123",
    "category": "preference",
    "created_at": "2025-11-05T10:30:00Z"
  }
}
```

---

## 📖 階段一：事實提取 (Fact Extraction)

### 1.1 工作原理

當您呼叫 `memory.add()` 時，Mem0 會：

```python
# 您的程式碼
memory.add(
    messages=[{
        "role": "user",
        "content": "我偏好科技股，風險承受度中等，明天要去吃飯"
    }],
    user_id="user-123"
)
```

**Mem0 內部執行**:

```python
# Step 1: 生成提取 prompt
system_prompt, user_prompt = get_fact_retrieval_messages(
    message="我偏好科技股，風險承受度中等，明天要去吃飯",
    is_agent_memory=False  # 使用者記憶模式
)

# Step 2: 呼叫 LLM (您專案中是 Gemini)
response = llm.generate(
    system=system_prompt,
    user=user_prompt
)

# Step 3: 解析 JSON 結果
facts = parse_json(response)
# 返回: {"facts": ["使用者偏好科技股", "使用者風險承受度為中等"]}
```

### 1.2 關鍵：Prompt Engineering

**系統提示詞 (USER_MEMORY_EXTRACTION_PROMPT)**:

```
您是一個專門從對話中提取使用者個人資訊的 AI 助理。

## 任務
從使用者訊息中提取值得長期記住的事實，並以 JSON 格式返回。

## 提取類別
請關注以下 7 類信息：

1. 個人偏好 (Personal Preferences)
   - 食物、產品、活動偏好
   - 喜歡/不喜歡的事物

2. 重要個人細節 (Important Personal Details)
   - 姓名、關係、日期
   - 個人背景資訊

3. 計劃與意圖 (Plans and Intentions)
   - 活動、旅行、目標

4. 活動/服務偏好 (Activity/Service Preferences)
   - 用餐、旅遊、嗜好

5. 健康與保健偏好 (Health and Wellness)

6. 專業細節 (Professional Details)
   - 職位、職業目標

7. 其他資訊 (Miscellaneous)
   - 喜愛的媒體、品牌等

## 重要規則

⚠️ **只從使用者訊息中提取事實**
⚠️ **不要包含助理或系統訊息的信息**
⚠️ **過濾掉無關緊要的信息**

## 輸出格式

{
  "facts": [
    "fact 1",
    "fact 2",
    ...
  ]
}

## 範例

輸入: "我正在尋找舊金山的一家餐廳"
輸出: {"facts": ["使用者正在尋找舊金山的餐廳"]}

輸入: "今天天氣真好"
輸出: {"facts": []}  // 無個人相關信息

輸入: "我偏好科技股，風險承受度中等，明天要去吃飯"
輸出: {
  "facts": [
    "使用者偏好科技股",
    "使用者風險承受度為中等"
  ]
}
// 注意: "明天要去吃飯" 不是長期值得記住的投資偏好，被過濾
```

### 1.3 為什麼能做到「標準化」？

關鍵在於 **Prompt 指示 LLM 轉換表達方式**：

**原始對話** → **標準化事實**

| 使用者原話 | Mem0 提取的標準化事實 |
|-----------|---------------------|
| "我喜歡科技股" | "使用者偏好科技股" |
| "我對科技類股票感興趣" | "使用者偏好科技股" |
| "科技股是我的菜" | "使用者偏好科技股" |
| "我比較保守，不想太激進" | "使用者風險承受度為中等" |
| "我的風險承受度大概中等吧" | "使用者風險承受度為中等" |

**標準化的好處**:
1. ✅ 統一表達方式
2. ✅ 方便去重和比對
3. ✅ 更好的檢索效果
4. ✅ 減少冗餘儲存

---

## 🔍 階段二：記憶動作分類 (Memory Action Classification)

### 2.1 為什麼需要這個階段？

提取事實後，Mem0 需要決定：
- 這是**新記憶**嗎？→ ADD
- 這是**更新**現有記憶？→ UPDATE
- 這個記憶**過時**了？→ DELETE
- **不需要**改變？→ NONE

### 2.2 工作流程

```python
# Step 1: 提取事實
new_facts = [
    "使用者偏好科技股",
    "使用者風險承受度為中等"
]

# Step 2: 搜索現有記憶
for fact in new_facts:
    # 使用向量搜索找相似記憶
    existing_memories = vector_db.search(
        query_embedding=embed(fact),
        user_id="user-123",
        limit=5
    )

    # Step 3: 呼叫 LLM 比較
    action = llm.classify_memory_action(
        new_fact=fact,
        existing_memories=existing_memories
    )

    # Step 4: 執行動作
    if action == "ADD":
        vector_db.add(fact)
    elif action == "UPDATE":
        vector_db.update(existing_memory_id, fact)
    elif action == "DELETE":
        vector_db.delete(existing_memory_id)
    # NONE: 什麼都不做
```

### 2.3 實際範例

**場景 1: 新記憶 (ADD)**
```
現有記憶: []
新事實: "使用者偏好科技股"
動作: ADD
→ 儲存為新記憶
```

**場景 2: 更新記憶 (UPDATE)**
```
現有記憶: ["使用者偏好科技股"]
新事實: "使用者偏好美股科技股，特別是 AI 相關"
動作: UPDATE
→ 更新現有記憶為更詳細版本
```

**場景 3: 刪除記憶 (DELETE)**
```
現有記憶: ["使用者偏好科技股"]
新事實: "我現在不想投資科技股了"
動作: DELETE
→ 刪除舊記憶
```

**場景 4: 不需改變 (NONE)**
```
現有記憶: ["使用者偏好科技股"]
新事實: "我喜歡科技股"  // 語義相同
動作: NONE
→ 不重複儲存
```

---

## 💾 階段三：向量化與儲存

### 3.1 Embedding 生成

```python
# 標準化事實
fact = "使用者偏好科技股"

# 使用 Google Embeddings API 生成向量
embedding = embeddings_api.embed(
    text=fact,
    model="models/text-embedding-004"
)

# 返回 768 維向量
# embedding = [0.234, -0.456, 0.678, ..., 0.123]
```

### 3.2 儲存到 ChromaDB

```python
# 儲存記憶
chroma_collection.add(
    ids=["mem_001"],
    embeddings=[embedding],
    documents=[fact],
    metadatas=[{
        "user_id": "user-123",
        "category": "preference",
        "created_at": "2025-11-05T10:30:00Z",
        "source": "user_message"
    }]
)
```

### 3.3 檢索時的運作

```python
# 使用者查詢: "給我投資建議"
query = "給我投資建議"

# 1. 生成查詢向量
query_embedding = embeddings_api.embed(query)

# 2. 在 ChromaDB 中進行向量相似度搜索
results = chroma_collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"user_id": "user-123"}  # 只搜索該使用者的記憶
)

# 3. 返回最相關的記憶
# results = [
#     {"content": "使用者偏好科技股", "distance": 0.12},  # 最相關
#     {"content": "使用者風險承受度為中等", "distance": 0.18},
#     ...
# ]
```

---

## 🎨 Prompt 工程詳解

### USER_MEMORY_EXTRACTION_PROMPT 的設計哲學

#### 設計要點 1: 明確分類指引

```
## 提取類別
1. 個人偏好 (Personal Preferences)
2. 重要個人細節 (Important Personal Details)
3. 計劃與意圖 (Plans and Intentions)
...
```

**為什麼這樣設計？**
- 給 LLM 明確的提取框架
- 避免提取無關信息
- 確保提取的信息有長期價值

#### 設計要點 2: 嚴格過濾規則

```
⚠️ 只從使用者訊息中提取事實
⚠️ 不要包含助理或系統訊息的信息
```

**為什麼重複強調？**
- LLM 容易混淆對話來源
- 防止將助理的回應誤認為使用者偏好
- 確保記憶的準確性

#### 設計要點 3: Few-Shot 範例

```
## 範例

輸入: "我正在尋找舊金山的一家餐廳"
輸出: {"facts": ["使用者正在尋找舊金山的餐廳"]}

輸入: "今天天氣真好"
輸出: {"facts": []}  // 無個人相關信息
```

**為什麼需要範例？**
- 展示標準化的格式
- 教導 LLM 什麼該提取、什麼不該提取
- 提高提取品質和一致性

#### 設計要點 4: 語言自適應

```
檢測使用者輸入語言，並以該語言記錄事實
```

**為什麼重要？**
- 支援多語言場景
- 保持原始語意
- 您的專案使用繁體中文，這確保了中文記憶

---

## 💡 實際範例演示

### 範例 1: 投資偏好提取

**使用者輸入**:
```
"嗨！我最近對投資很感興趣，特別是科技股。
我的風險承受度大概中等吧，不想太激進。
對了，我明天要去吃日本料理。"
```

**Mem0 內部處理**:

#### Step 1: LLM 提取事實

**發送給 LLM 的 Prompt**:
```
System: [USER_MEMORY_EXTRACTION_PROMPT 的完整內容]

User:
Input:
嗨！我最近對投資很感興趣，特別是科技股。
我的風險承受度大概中等吧，不想太激進。
對了，我明天要去吃日本料理。
```

**LLM 回應**:
```json
{
  "facts": [
    "使用者對投資感興趣",
    "使用者偏好科技股",
    "使用者風險承受度為中等"
  ]
}
```

**分析**:
- ✅ "對投資感興趣" → 提取（長期偏好）
- ✅ "特別是科技股" → 標準化為 "使用者偏好科技股"
- ✅ "風險承受度大概中等" → 標準化為 "使用者風險承受度為中等"
- ❌ "明天要去吃日本料理" → **過濾掉**（短期計劃，與投資無關）

#### Step 2: 記憶動作分類

對每個提取的事實，檢查現有記憶：

```
事實 1: "使用者對投資感興趣"
現有記憶: (無)
動作: ADD
→ 新增記憶

事實 2: "使用者偏好科技股"
現有記憶: (無)
動作: ADD
→ 新增記憶

事實 3: "使用者風險承受度為中等"
現有記憶: (無)
動作: ADD
→ 新增記憶
```

#### Step 3: 儲存結果

最終儲存到 ChromaDB 的記憶：

```json
[
  {
    "id": "mem_001",
    "content": "使用者對投資感興趣",
    "embedding": [0.23, -0.45, ...],
    "metadata": {
      "user_id": "user-123",
      "category": "preference",
      "created_at": "2025-11-05T10:30:00Z"
    }
  },
  {
    "id": "mem_002",
    "content": "使用者偏好科技股",
    "embedding": [0.31, -0.52, ...],
    "metadata": {
      "user_id": "user-123",
      "category": "preference",
      "created_at": "2025-11-05T10:30:01Z"
    }
  },
  {
    "id": "mem_003",
    "content": "使用者風險承受度為中等",
    "embedding": [0.28, -0.48, ...],
    "metadata": {
      "user_id": "user-123",
      "category": "preference",
      "created_at": "2025-11-05T10:30:02Z"
    }
  }
]
```

---

### 範例 2: 記憶更新

**第一天 - 使用者輸入**:
```
"我偏好科技股"
```

**Mem0 儲存**:
```json
{
  "id": "mem_001",
  "content": "使用者偏好科技股"
}
```

---

**第二天 - 使用者輸入**:
```
"我現在特別看好 AI 相關的科技股"
```

**Mem0 處理**:

1. **提取事實**: "使用者偏好 AI 相關科技股"

2. **搜索現有記憶**:
   ```
   查詢向量: embed("使用者偏好 AI 相關科技股")
   找到相似記憶: "使用者偏好科技股" (相似度 0.85)
   ```

3. **LLM 分類動作**:
   ```
   Prompt:
   現有記憶: "使用者偏好科技股"
   新事實: "使用者偏好 AI 相關科技股"

   請決定動作: ADD / UPDATE / DELETE / NONE

   LLM 回應: UPDATE
   理由: 新事實是對現有記憶的細化和擴充
   ```

4. **執行更新**:
   ```json
   {
     "id": "mem_001",
     "content": "使用者偏好 AI 相關科技股",  // 更新
     "metadata": {
       "updated_at": "2025-11-06T10:30:00Z"
     }
   }
   ```

---

### 範例 3: 記憶衝突解決

**現有記憶**:
```
"使用者風險承受度為高"
```

**新輸入**:
```
"我現在比較保守了，不想冒太大風險"
```

**Mem0 處理**:

1. **提取事實**: "使用者風險承受度為低"

2. **檢測衝突**:
   ```
   現有: "使用者風險承受度為高"
   新的: "使用者風險承受度為低"
   → 衝突！
   ```

3. **LLM 決策**:
   ```
   動作: UPDATE
   理由: 使用者偏好改變，應更新為最新資訊
   ```

4. **執行**:
   ```json
   {
     "id": "mem_005",
     "content": "使用者風險承受度為低",  // 替換舊記憶
     "metadata": {
       "updated_at": "2025-11-07T10:30:00Z",
       "previous_value": "使用者風險承受度為高"
     }
   }
   ```

---

## 🔧 您專案中的運作

### 在您的專案中，Mem0 如何配置？

**位置**: `backend/src/services/memory_service.py:36-62`

```python
cls._mem0_client = Memory.from_config(
    {
        "llm": {
            "provider": "gemini",  # 使用 Google Gemini
            "config": {
                "model": settings.mem0_llm_model,  # gemini-2.0-flash-exp
                "temperature": 0.7,
                "max_tokens": 2000,
                "api_key": settings.google_api_key,
            },
        },
        "embedder": {
            "provider": "gemini",  # 使用 Google Embeddings
            "config": {
                "model": f"models/{settings.mem0_embedder_model}",  # text-embedding-004
                "api_key": settings.google_api_key,
            },
        },
        "vector_store": {
            "provider": "chroma",  # 使用 ChromaDB
            "config": {
                "collection_name": "investment_memories",
                "path": settings.chroma_path,  # ./data/chroma
            },
        },
    }
)
```

### 完整運作流程

當使用者發送訊息時：

```python
# 1. 使用者訊息: backend/src/api/routes/chat.py:108
user_message = "我偏好科技股，風險承受度中等"

# 2. 處理訊息: backend/src/services/conversation_service.py
result = ConversationService.process_message(
    user_id="user-123",
    message=user_message
)

# 3. 提取記憶: backend/src/services/memory_service.py:276
MemoryService.add_memory_from_message(
    user_id="user-123",
    message_content=user_message
)
```

**內部執行** (自動):

```
[步驟 1] 呼叫 Mem0.add()
   ↓
[步驟 2] Mem0 使用 Gemini LLM 分析訊息
   使用 USER_MEMORY_EXTRACTION_PROMPT
   ↓
[步驟 3] Gemini 返回提取的事實
   {"facts": ["使用者偏好科技股", "使用者風險承受度為中等"]}
   ↓
[步驟 4] 對每個事實使用 Google Embeddings 生成向量
   "使用者偏好科技股" → [0.23, -0.45, ...]
   ↓
[步驟 5] 搜索 ChromaDB 檢查是否有相似記憶
   ↓
[步驟 6] Gemini 分類動作 (ADD/UPDATE/DELETE/NONE)
   ↓
[步驟 7] 執行動作並儲存到 ChromaDB
   collection: "investment_memories"
   path: "./data/chroma"
```

### 檢索記憶時

```python
# backend/src/services/memory_service.py:108
memories = MemoryService.search_memories(
    user_id="user-123",
    query="投資建議",
    top_k=5
)
```

**內部執行**:

```
[步驟 1] 生成查詢向量
   "投資建議" → embed() → [0.25, -0.47, ...]
   ↓
[步驟 2] ChromaDB 向量搜索
   找到最相似的 5 個記憶
   ↓
[步驟 3] 返回排序後的記憶
   [
     {"content": "使用者偏好科技股", "relevance": 0.92},
     {"content": "使用者風險承受度為中等", "relevance": 0.85},
     ...
   ]
```

---

## 🆚 與傳統 RAG 的對比

### 對比表

| 項目 | 傳統 RAG | Mem0 |
|------|---------|------|
| **文本處理** | 機械切分 chunks | LLM 智能分析 |
| **儲存內容** | 原始文本 | 提煉的標準化事實 |
| **提取方式** | `text.split(chunk_size)` | LLM + Extraction Prompt |
| **標準化** | 無 | 自動標準化表達 |
| **過濾** | 無 | 智能過濾無關信息 |
| **更新機制** | 手動 | 自動 ADD/UPDATE/DELETE |
| **去重** | 無 | 自動去重 |
| **衝突解決** | 無 | 自動處理 |

### 實際對比範例

**輸入**: "我喜歡科技股，風險承受度中等，明天吃飯"

#### 傳統 RAG

```python
# 切分
chunks = [
    "我喜歡科技股，",
    "風險承受度中等，",
    "明天吃飯"
]

# 全部儲存
for chunk in chunks:
    vector_db.add(chunk)

# 查詢 "投資建議"
results = vector_db.search("投資建議")
# 可能返回: ["我喜歡科技股，", "明天吃飯"]  ← 包含無關內容
```

#### Mem0

```python
# 智能提取
memory.add(message="我喜歡科技股，風險承受度中等，明天吃飯")

# Mem0 內部處理
facts = llm_extract([
    "使用者偏好科技股",      # ✓ 標準化
    "使用者風險承受度為中等"  # ✓ 標準化
    # "明天吃飯" 被過濾 ✗
])

# 儲存提煉的事實
vector_db.add(facts)

# 查詢 "投資建議"
results = memory.search("投資建議")
# 返回: ["使用者偏好科技股", "使用者風險承受度為中等"]  ← 只有相關內容
```

---

## 📊 效能優勢的來源

### 為什麼 Mem0 能達到這些指標？

| 指標 | 數值 | 原因 |
|------|------|------|
| **準確度** | +26% | 提煉的事實更精準，減少雜訊 |
| **速度** | 91% 更快 | 儲存量少，檢索更快 |
| **Token** | 90% 減少 | 只注入相關記憶，不是完整對話 |

### Token 使用對比

**傳統 RAG**:
```
原始對話 (1000 tokens) + 檢索 chunks (500 tokens) = 1500 tokens
```

**Mem0**:
```
提煉事實 (50 tokens) + 檢索記憶 (100 tokens) = 150 tokens
→ 減少 90%
```

---

## 🎯 總結

### Mem0 的「提取知識 → 標準化」流程

1. **智能提取**: 使用 LLM + 特殊 Prompt 分析對話
2. **自動過濾**: 只保留有長期價值的信息
3. **標準化表達**: 統一不同措辭的相同概念
4. **動作分類**: 決定 ADD/UPDATE/DELETE/NONE
5. **向量儲存**: 使用 Embeddings + ChromaDB
6. **智能檢索**: 語義搜索找相關記憶

### 核心創新

- ✅ **不是儲存原始文本，而是儲存知識**
- ✅ **不是機械切分，而是智能提取**
- ✅ **不是靜態儲存，而是動態管理**
- ✅ **不是全部檢索，而是相關過濾**

這就是 Mem0 超越傳統 RAG 的關鍵所在！

---

**參考資源**:
- Mem0 官方文檔: https://docs.mem0.ai
- Mem0 GitHub: https://github.com/mem0ai/mem0
- 您的專案: `backend/src/services/memory_service.py`

**下一步建議**:
- 實際測試不同輸入，觀察記憶提取結果
- 查看 ChromaDB 儲存的記憶內容
- 調整 Prompt 以適應特定領域需求
