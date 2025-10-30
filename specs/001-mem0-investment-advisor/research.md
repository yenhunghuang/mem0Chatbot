# 技術研究：個人化投顧助理（Mem0 練習版）

**日期**: 2025-10-30  
**目的**: 研究並確認核心技術選型與整合方案

## 研究領域

### 1. Mem0 記憶系統整合

**決策**: 使用 Mem0 Python SDK 作為長期記憶層，整合 Google Embeddings 和 Chroma 向量資料庫

**理由**:
- Mem0 提供開箱即用的記憶管理 API，包含自動擷取、儲存和檢索
- 原生支援多種向量資料庫後端（Chroma, Pinecone, Qdrant 等）
- 與 LLM 整合良好，可自動從對話中提取記憶點
- Python SDK 文件完整，社群活躍

**考慮的替代方案**:
- **LangChain Memory**: 功能較為基礎，需要更多自定義程式碼
- **自建向量搜索系統**: 開發成本高，練習專案不適合
- **LlamaIndex**: 偏重文檔檢索，不適合對話記憶場景

**實作要點**:
```python
from mem0 import Memory

# 初始化 Mem0 with Chroma backend
memory = Memory(
    config={
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "investment_memories",
                "path": "./data/chroma"
            }
        },
        "embedder": {
            "provider": "google",
            "config": {
                "model": "gemini-embedding-001"
            }
        }
    }
)
```

### 2. Google Gemini 2.5 Flash 整合

**決策**: 使用 Google Generative AI Python SDK 直接整合 Gemini 2.5 Flash

**理由**:
- Gemini 2.5 Flash 提供優秀的繁體中文支援
- 回應速度快（適合對話場景）
- API 定價合理，適合練習專案
- 支援 function calling（未來可擴展）

**考慮的替代方案**:
- **OpenAI GPT-4**: 成本較高，繁中支援不如 Gemini
- **Anthropic Claude**: API 在台灣可用性較低
- **本地模型**: 部署複雜度高，不適合練習

**實作要點**:
```python
import google.generativeai as genai

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash')

# 整合記憶上下文
def generate_with_memory(user_input, memories):
    context = f"使用者偏好：\n" + "\n".join(memories)
    prompt = f"{context}\n\n使用者：{user_input}\n助理："
    response = model.generate_content(prompt)
    return response.text
```

### 3. 向量嵌入與語義搜索

**決策**: 使用 Google Embeddings API (gemini-embedding-001) + ChromaDB

**理由**:
- Google Embeddings 與 Gemini 同一生態系，整合順暢
- Chroma 本地執行，無需外部服務，適合練習
- Chroma 支援持久化儲存，重啟後資料保留
- 向量維度自動處理，減少配置複雜度

**考慮的替代方案**:
- **OpenAI Embeddings**: 需要額外 API 密鑰和成本
- **Sentence Transformers**: 本地執行但需要模型下載
- **FAISS**: 較低階，需要更多自定義程式碼

**實作要點**:
```python
import chromadb

# 初始化 Chroma 客戶端
client = chromadb.PersistentClient(path="./data/chroma")
collection = client.get_or_create_collection(
    name="investment_memories",
    metadata={"description": "User investment preferences"}
)

# Mem0 自動處理嵌入和儲存
```

### 4. 短期記憶與 SQLite

**決策**: 使用 SQLite 儲存對話歷史、使用者會話和中繼資料

**理由**:
- 無需額外服務，Python 內建支援
- 輕量且高效，適合單機部署
- 支援 ACID 事務，資料可靠
- 易於備份和遷移（單一檔案）

**考慮的替代方案**:
- **PostgreSQL**: 過於重量級，練習不需要
- **Redis**: 規格明確排除，且記憶體限制
- **JSON 檔案**: 缺乏查詢能力和並發控制

**實作要點**:
```python
import sqlite3
from datetime import datetime, timedelta

# Schema 設計
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'user' or 'assistant'
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

# 延遲 TTL 實作
def cleanup_expired_conversations(ttl_days=30):
    cutoff = datetime.now() - timedelta(days=ttl_days)
    conn.execute(
        "DELETE FROM conversations WHERE last_activity < ?",
        (cutoff,)
    )
```

### 5. FastAPI 架構模式

**決策**: 採用三層架構 (Models / Services / API)，遵循依賴注入模式

**理由**:
- 符合 FastAPI 最佳實踐
- 清晰的職責分離，易於測試
- 支援依賴注入，便於 mock 和測試
- 適合團隊協作和程式碼維護

**架構層次**:
1. **Models**: Pydantic 模型，定義資料結構和驗證
2. **Services**: 業務邏輯層，整合 LLM、Mem0、儲存
3. **API Routes**: HTTP 端點，處理請求/回應

**實作模式**:
```python
# services/memory_service.py
class MemoryService:
    def __init__(self, mem0_client, storage):
        self.mem0 = mem0_client
        self.storage = storage
    
    async def add_memory(self, user_id: str, content: str):
        # 業務邏輯
        pass

# api/routes/chat.py
from fastapi import Depends

def get_memory_service() -> MemoryService:
    return MemoryService(mem0_client, storage)

@router.post("/chat")
async def chat(
    request: ChatRequest,
    memory_service: MemoryService = Depends(get_memory_service)
):
    # 端點邏輯
    pass
```

### 6. 前端 UUID 管理策略

**決策**: 在前端使用 JavaScript 生成 UUID v4，儲存於 localStorage

**理由**:
- 無需後端會話管理，簡化架構
- localStorage 持久化，瀏覽器關閉後保留
- UUID v4 碰撞機率極低，適合臨時識別
- 符合規格中「無登入流程」的要求

**實作要點**:
```javascript
// storage.js
function getUserId() {
    let userId = localStorage.getItem('user_id');
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem('user_id', userId);
    }
    return userId;
}

// 每次 API 請求帶上 userId
fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        user_id: getUserId(),
        message: userInput
    })
});
```

### 7. 測試策略

**決策**: 使用 pytest + pytest-asyncio + httpx 進行多層測試

**測試層次**:
1. **單元測試**: 測試個別服務邏輯（mock 外部依賴）
2. **整合測試**: 測試 LLM + Mem0 + 儲存的整合
3. **API 測試**: 使用 TestClient 測試端點
4. **手動測試**: VS Code REST Client (.http 檔案)

**實作要點**:
```python
# tests/conftest.py
@pytest.fixture
def mock_mem0():
    return MagicMock(spec=Memory)

@pytest.fixture
def memory_service(mock_mem0):
    return MemoryService(mem0_client=mock_mem0, storage=mock_storage)

# tests/unit/test_memory_service.py
def test_add_memory(memory_service, mock_mem0):
    memory_service.add_memory("user123", "我偏好科技股")
    mock_mem0.add.assert_called_once()
```

## 技術風險與緩解策略

### 風險 1: Google API 配額限制
**緩解**: 
- 實作請求速率限制（rate limiting）
- 記錄 API 使用量並監控
- 提供降級模式（當配額用盡時使用簡單規則回應）

### 風險 2: Chroma 向量資料庫效能
**緩解**:
- 限制記憶數量上限（例如每使用者最多 1000 條）
- 定期清理低相關性記憶
- 使用索引優化搜索效能

### 風險 3: SQLite 並發限制
**緩解**:
- 使用 WAL 模式提升並發性能
- 短期記憶不需要極高並發（50 使用者規格內）
- 必要時可遷移至 PostgreSQL（但規格不需要）

## 依賴清單

```txt
# backend/requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
pydantic==2.5.0
pydantic-settings==2.1.0
mem0ai==0.0.10
google-generativeai==0.3.1
google-ai-python==0.1.0
chromadb==0.4.18
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1
```

## 結論

所有技術決策已確認，無 NEEDS CLARIFICATION 項目。技術棧選擇符合專案目標：
- 重點展示 LLM + 記憶系統整合
- 簡化部署和開發複雜度
- 適合練習和快速迭代

可進入 Phase 1 (設計與合約階段)。
