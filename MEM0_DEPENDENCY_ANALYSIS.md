# 🎯 mem0Chatbot 專案進度報告

**日期**: 2025-10-30  
**報告重點**: Mem0 套件依賴分析與後續移除計劃

---

## 📊 整體進度總覽

| 里程碑 | 狀態 | 完成度 | Mem0 依賴度 |
|--------|------|--------|------------|
| **US1** 多輪對話 + 記憶寫入 | ✅ 完成 | 100% | 🔴 高度依賴 |
| **US2** 記憶檢索 + 個人化回應 | ✅ 完成 | 100% | 🔴 高度依賴 |
| **US3** 記憶 CRUD 管理 | ⏳ 規劃中 | 0% | 🔴 高度依賴 |
| **Phase 4** 移除 Mem0 依賴 | ⏳ 待規劃 | 0% | ✅ 完全獨立 |

---

## 🔍 Mem0 套件依賴詳細分析

### 📍 依賴位置清單

| 文件路徑 | 依賴項目 | 使用方式 | 替代難度 |
|---------|---------|---------|---------|
| `backend/src/services/memory_service.py` | `from mem0 import Memory` | 初始化 Mem0 客戶端 | 🟡 中等 |
| `backend/src/services/memory_service.py#L22` | `Memory.from_config()` | 配置 LLM/Embedder/VectorStore | 🟡 中等 |
| `backend/src/services/memory_service.py#L63` | `_memory_instance.add()` | 記憶寫入（含自動提取） | 🔴 困難 |
| `backend/src/services/memory_service.py#L110` | `_memory_instance.search()` | 向量搜索 | 🟢 簡單 |
| `backend/src/services/memory_service.py#L177` | `_memory_instance.delete()` | 記憶刪除 | 🟢 簡單 |
| `backend/requirements.txt#L5` | `mem0ai` | 套件依賴 | - |

### 🔴 高度依賴區域（需完全重寫）

#### 1. **記憶寫入邏輯** (`add_memory_from_message`)

**當前實作**:
```python
@staticmethod
def add_memory_from_message(
    user_id: str,
    message: str,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """從使用者訊息提取投資偏好並儲存到 Mem0"""
    # 🔴 依賴 Mem0 SDK 的核心邏輯
    memory_id = MemoryService._memory_instance.add(
        messages=[{"role": "user", "content": message}],
        user_id=user_id,
        metadata=full_metadata,
    )
    # Mem0 內部：
    # 1. 呼叫 LLM 提取偏好
    # 2. 呼叫 Embedding API 向量化
    # 3. 寫入 ChromaDB
```

**Mem0 內部黑盒操作**:
1. ✅ LLM 分析訊息提取投資偏好
2. ✅ 使用 Google Embedding API 向量化
3. ✅ 自動去重和相似記憶合併
4. ✅ 寫入 ChromaDB

**替代實作需求**:
- 🔧 建立 `MemoryExtractionService` (使用自己的 LLM prompt)
- 🔧 建立 `EmbeddingService` (直接呼叫 Google Embedding API)
- 🔧 直接操作 ChromaDB 客戶端
- 🔧 實作去重邏輯

**估計工作量**: 2-3 天

---

#### 2. **Mem0 初始化配置** (`initialize`)

**當前實作**:
```python
@classmethod
def initialize(cls):
    """初始化 Mem0 和 ChromaDB"""
    # 🔴 依賴 Mem0 的統一配置接口
    cls._memory_instance = Memory.from_config(
        config={
            "llm": {
                "provider": "google",
                "config": {"model": "gemini-2.0-flash-exp", ...},
            },
            "embedder": {
                "provider": "google",
                "config": {"model": "models/embedding-001"},
            },
            "vectorstore": {
                "provider": "chroma",
                "config": {
                    "collection_name": "investment_memories",
                    "path": str(settings.chroma_path),
                },
            },
        }
    )
```

**Mem0 提供的便利**:
- ✅ 統一配置 LLM + Embedder + VectorStore
- ✅ 自動處理連接和錯誤重試
- ✅ 版本管理和遷移

**替代實作需求**:
- 🔧 直接初始化 `chromadb.PersistentClient`
- 🔧 配置 Google Generative AI SDK
- 🔧 配置 Google AI Python SDK (Embeddings)
- 🔧 手動錯誤處理和重試邏輯

**估計工作量**: 1 天

---

### 🟡 中度依賴區域（需改寫接口）

#### 3. **記憶搜索** (`search_memories`)

**當前實作**:
```python
@staticmethod
def search_memories(user_id: str, query: str, top_k: int = 5) -> List[Dict]:
    """搜索相關記憶"""
    # 🟡 依賴 Mem0 的搜索接口
    results = MemoryService._memory_instance.search(
        query=query,
        user_id=user_id,
        limit=top_k,
    )
    # Mem0 內部：
    # 1. 將查詢向量化
    # 2. 在 ChromaDB 中搜索
    # 3. 過濾 user_id
    # 4. 返回結果
```

**Mem0 提供的功能**:
- ✅ 自動查詢向量化
- ✅ ChromaDB 查詢封裝
- ✅ 用戶過濾

**替代實作需求**:
- 🔧 使用 `EmbeddingService.embed_query()` 向量化
- 🔧 直接呼叫 `chroma_collection.query()`
- 🔧 手動 `where={"user_id": user_id}` 過濾

**估計工作量**: 1 天

---

### 🟢 低度依賴區域（簡單替代）

#### 4. **記憶刪除** (`delete_memory` - US3)

**當前實作**:
```python
@staticmethod
def delete_memory(memory_id: str, user_id: str) -> bool:
    """刪除記憶"""
    # 🟢 簡單的 Mem0 刪除接口
    MemoryService._memory_instance.delete(
        memory_id=memory_id,
        user_id=user_id,
    )
```

**替代實作**:
```python
# 直接操作 ChromaDB
chroma_collection.delete(ids=[memory_id])
```

**估計工作量**: 0.5 天

---

## 📋 移除 Mem0 依賴的完整計劃

### Phase 4: 獨立實作記憶系統

| 階段 | 任務 | 文件 | 估計工時 | 優先級 |
|------|------|------|---------|--------|
| **4.1** | 建立 `EmbeddingService` | `backend/src/services/embedding_service.py` | 1 天 | P1 |
| **4.2** | 建立 `MemoryExtractionService` | `backend/src/services/memory_extraction_service.py` | 2 天 | P1 |
| **4.3** | 重構 `MemoryService.initialize()` | `backend/src/services/memory_service.py` | 1 天 | P1 |
| **4.4** | 重構 `MemoryService.add_memory_from_message()` | `backend/src/services/memory_service.py` | 2 天 | P1 |
| **4.5** | 重構 `MemoryService.search_memories()` | `backend/src/services/memory_service.py` | 1 天 | P2 |
| **4.6** | 重構 `MemoryService.delete_memory()` | `backend/src/services/memory_service.py` | 0.5 天 | P2 |
| **4.7** | 建立 `MemoryCRUDService` (US3 支援) | `backend/src/services/memory_crud_service.py` | 2 天 | P2 |
| **4.8** | 移除 `from mem0 import Memory` | 所有文件 | 0.5 天 | P3 |
| **4.9** | 更新 `requirements.txt` | 移除 `mem0ai` | 0.1 天 | P3 |
| **4.10** | 完整測試套件 | `tests/unit/test_memory_*.py` | 2 天 | P1 |

**總估計工時**: 12-15 天

---

## 🔧 關鍵實作檔案預覽

### 1. `EmbeddingService` (Phase 4.1)

```python
"""
向量化服務 - 直接呼叫 Google Embedding API
替代 Mem0 的 embedder 配置
"""
import google.generativeai as genai
from typing import List

class EmbeddingService:
    """向量化服務"""
    
    @staticmethod
    def embed_text(text: str) -> List[float]:
        """將文本轉換為向量（用於儲存）"""
        result = genai.embed_content(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return result['embedding']
    
    @staticmethod
    def embed_query(query: str) -> List[float]:
        """將查詢轉換為向量（用於搜索）"""
        result = genai.embed_content(
            model="models/embedding-001",
            content=query,
            task_type="retrieval_query"
        )
        return result['embedding']
```

---

### 2. `MemoryExtractionService` (Phase 4.2)

```python
"""
記憶提取服務 - 使用 LLM 從訊息中提取投資偏好
替代 Mem0 的自動提取邏輯
"""
import google.generativeai as genai
from typing import List, Dict
import json

class MemoryExtractionService:
    """記憶提取服務"""
    
    @staticmethod
    def extract_investment_preferences(message: str) -> List[Dict]:
        """
        從使用者訊息提取投資偏好
        
        Returns:
            [
                {
                    "content": "偏好投資科技股",
                    "category": "investment_type",
                    "confidence": 0.95
                }
            ]
        """
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = f"""
你是投資偏好分析專家。從以下使用者訊息中提取**明確的投資相關偏好**。

使用者訊息：{message}

請以 JSON 格式返回，包含：
- content: 偏好的完整描述
- category: 分類（investment_type|risk_tolerance|time_horizon|sector_preference）
- confidence: 信心分數 (0.0-1.0)

如果沒有投資偏好，返回空列表 []。
"""
        
        response = model.generate_content(prompt)
        return json.loads(response.text.strip("```json\n").strip("\n```"))
```

---

### 3. 重構後的 `add_memory_from_message()` (Phase 4.4)

```python
@staticmethod
def add_memory_from_message(
    user_id: str,
    message: str,
    metadata: Optional[Dict] = None
) -> List[str]:
    """從訊息提取記憶並儲存（完全獨立實作）"""
    
    # 1. 使用自己的 LLM 提取投資偏好
    preferences = MemoryExtractionService.extract_investment_preferences(message)
    
    if not preferences:
        return []
    
    memory_ids = []
    
    for pref in preferences:
        # 2. 向量化偏好內容
        embedding = EmbeddingService.embed_text(pref['content'])
        
        # 3. 準備 metadata
        memory_id = str(uuid.uuid4())
        full_metadata = {
            "user_id": user_id,
            "category": pref['category'],
            "confidence": pref['confidence'],
            "created_at": datetime.utcnow().isoformat(),
            "source": "user_message",
            **(metadata or {})
        }
        
        # 4. 直接寫入 ChromaDB
        MemoryService._collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[pref['content']],
            metadatas=[full_metadata]
        )
        
        memory_ids.append(memory_id)
    
    return memory_ids
```

---

## 📊 Mem0 依賴度矩陣

| 功能模組 | Mem0 依賴項目 | 影響範圍 | 替代方案 | 風險評估 |
|---------|-------------|---------|---------|---------|
| **記憶提取** | `Memory.add()` | 核心功能 | `MemoryExtractionService` | 🔴 高 |
| **向量化** | Mem0 內部 Embedder | 核心功能 | `EmbeddingService` | 🟡 中 |
| **記憶搜索** | `Memory.search()` | 核心功能 | ChromaDB 直接查詢 | 🟢 低 |
| **初始化** | `Memory.from_config()` | 基礎設施 | 直接初始化各服務 | 🟡 中 |
| **記憶刪除** | `Memory.delete()` | US3 功能 | ChromaDB 直接刪除 | 🟢 低 |

---

## 🎯 建議執行順序

### **階段 1: 完成原計劃（US3）** [當前優先]
⏱️ **估計時間**: 1-2 週

**目標**: 使用 Mem0 完成所有計劃功能

| 任務 | 說明 | Mem0 依賴 |
|------|------|----------|
| T044-T052 | 記憶列表 API | ✅ 使用 Mem0 |
| T053-T060 | 記憶更新 API | ✅ 使用 Mem0 |
| T061-T070 | 記憶刪除 API + 前端 | ✅ 使用 Mem0 |

**優點**:
- ✅ 快速交付完整功能
- ✅ 驗證業務邏輯正確性
- ✅ 獲得使用者反饋

---

### **階段 2: 移除 Mem0 依賴（Phase 4）** [後續規劃]
⏱️ **估計時間**: 2-3 週

**目標**: 完全獨立實作記憶系統

**執行順序**:
1. **Week 1**: 建立基礎服務
   - Day 1-2: `EmbeddingService` (Phase 4.1)
   - Day 3-5: `MemoryExtractionService` (Phase 4.2)

2. **Week 2**: 重構核心邏輯
   - Day 1-2: 重構 `add_memory_from_message()` (Phase 4.4)
   - Day 3: 重構 `search_memories()` (Phase 4.5)
   - Day 4-5: 測試與驗證 (Phase 4.10)

3. **Week 3**: 完成與整合
   - Day 1-2: `MemoryCRUDService` (Phase 4.7)
   - Day 3: 重構 `delete_memory()` (Phase 4.6)
   - Day 4: 移除依賴 (Phase 4.8-4.9)
   - Day 5: 完整回歸測試

**優點**:
- ✅ 完全掌控記憶邏輯
- ✅ 深入理解向量資料庫
- ✅ 學習價值最大化
- ✅ 可客製化記憶提取規則

---

## 📈 技術債務追蹤

### 當前技術債務

| 項目 | 債務描述 | 影響 | 優先級 |
|------|---------|------|--------|
| **Mem0 黑盒邏輯** | 無法控制記憶提取品質 | 中 | P2 |
| **API 配額依賴** | Mem0 內部呼叫消耗配額 | 低 | P3 |
| **版本鎖定** | 依賴 Mem0 版本更新 | 低 | P3 |
| **除錯困難** | 無法追蹤 Mem0 內部流程 | 中 | P2 |

### Phase 4 完成後收益

| 項目 | 改進 | 價值 |
|------|------|------|
| **完全控制** | 可調整提取邏輯和 prompt | 高 |
| **成本優化** | 直接控制 API 呼叫次數 | 中 |
| **除錯能力** | 完整日誌和錯誤追蹤 | 高 |
| **學習價值** | 深入理解 RAG 架構 | 高 |
| **可擴展性** | 易於新增自訂功能 | 中 |

---

## 📝 總結與建議

### ✅ **建議路徑：先完成 → 再重構**

**理由**:
1. **業務優先** - 先驗證產品可行性
2. **風險控制** - 有可運作版本再重構
3. **學習最大化** - 先理解 Mem0 原理，再獨立實作
4. **時間效益** - US3 (1-2週) vs Phase 4 (2-3週)

**具體執行**:
```
當前 → US3 完成 (使用 Mem0) → Phase 4 規劃 → 獨立實作 → 完全移除 Mem0
      [1-2 週]                    [2-3 週]      [完成]
```

---

### 📋 下一步行動

**立即行動** (本週):
- ✅ 完成 US3 規劃文檔（tasks.md）
- ✅ 實作 T044-T052（記憶列表 API）
- ✅ 前端記憶管理介面

**短期計劃** (2 週內):
- ✅ 完成 US3 所有功能
- ✅ 撰寫 Phase 4 詳細技術設計文檔
- ✅ 準備 Mem0 依賴移除的測試計劃

**中期計劃** (1 個月內):
- 🔧 執行 Phase 4.1-4.5（基礎服務重構）
- 🔧 完成核心邏輯獨立化
- 🔧 並行運行雙版本驗證

---

## 🎓 學習價值評估

| 使用 Mem0 | 獨立實作 Phase 4 |
|----------|-----------------|
| ✅ 快速理解 RAG 架構 | ✅ 深入掌握向量資料庫 |
| ✅ 學習最佳實踐 | ✅ LLM prompt 工程實戰 |
| ✅ 專注業務邏輯 | ✅ 完整系統設計能力 |
| ❌ 黑盒操作 | ✅ 完全可控 |

**結論**: **兩階段方法獲得最大學習價值** 🎯

---

**報告生成時間**: 2025-10-30  
**下次更新**: US3 完成後或 Phase 4 啟動前
