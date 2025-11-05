# 個人化投顧助理專案 - 完整教學文件

**專案名稱**: Mem0 個人化投資顧問聊天機器人
**技術棧**: FastAPI + Python 3.12 + Google Gemini + Mem0 + ChromaDB + SQLite
**版本**: 1.0.0
**最後更新**: 2025-11-05

---

## 📋 目錄

1. [專案概述](#專案概述)
2. [核心概念](#核心概念)
3. [技術架構](#技術架構)
4. [資料流程](#資料流程)
5. [安裝與設置](#安裝與設置)
6. [啟動與測試](#啟動與測試)
7. [核心功能詳解](#核心功能詳解)
8. [API 端點說明](#api-端點說明)
9. [專案結構](#專案結構)
10. [開發與擴充](#開發與擴充)
11. [常見問題](#常見問題)

---

## 📖 專案概述

### 什麼是這個專案?

這是一個**基於 Mem0 記憶系統的個人化投資顧問聊天機器人**,能夠:

1. **記住使用者的投資偏好** - 自動從對話中擷取並儲存使用者的投資偏好(如風險承受度、產業偏好等)
2. **提供個人化建議** - 根據儲存的記憶為使用者提供量身定制的投資建議
3. **持續學習** - 隨著對話進行,系統會持續更新對使用者的理解

### 核心特色

- ✅ **無需註冊登入** - 使用瀏覽器 localStorage 的 UUID 識別使用者
- ✅ **長期記憶** - 使用 Mem0 + ChromaDB 實現語義記憶搜索
- ✅ **短期記憶** - 使用 SQLite 儲存對話歷史
- ✅ **智能對話** - 使用 Google Gemini 2.5 Flash 模型
- ✅ **向量搜索** - 使用 Google Embeddings 進行語義相似性搜索
- ✅ **繁體中文** - 完整支援繁體中文介面和回應

### 使用場景

**場景 1: 建立偏好記憶**
```
使用者: "我偏好長期投資科技股,風險承受度中等"
系統: [自動擷取並儲存兩條記憶]
      - 使用者偏好長期投資科技股
      - 使用者風險承受度為中等
```

**場景 2: 個人化回應**
```
使用者: "最近有哪些值得關注的股票?"
系統: [檢索記憶] → [找到科技股偏好和中等風險]
回應: "根據您偏好長期投資科技股且風險承受度中等,
       以下是適合的標的: NVIDIA(AI晶片)、Microsoft(雲端)..."
```

---

## 🧠 核心概念

### 1. Mem0 記憶系統

**Mem0** 是一個專門為 AI 應用設計的記憶管理系統,提供:

- **自動記憶提取**: 從對話中自動識別和提取值得記住的信息
- **語義搜索**: 使用向量嵌入進行相似性搜索
- **記憶管理**: 自動處理記憶的儲存、更新、刪除

**工作原理**:
```python
# 1. 新增記憶 (自動提取)
memory.add(
    messages=[{"role": "user", "content": "我偏好科技股"}],
    user_id="user-123"
)
# Mem0 會自動:
# - 使用 LLM 分析訊息
# - 提取關鍵信息: "使用者偏好科技股"
# - 使用 Embeddings 生成向量
# - 儲存到 ChromaDB

# 2. 搜索記憶
results = memory.search(
    query="使用者的投資偏好",
    user_id="user-123",
    limit=5
)
# 返回最相關的 5 條記憶
```

### 2. 向量嵌入 (Embeddings)

**向量嵌入** 是將文字轉換為高維向量的技術,使得語義相似的文字在向量空間中距離更近。

```
"科技股投資" → [0.23, -0.45, 0.67, ...] (768 維向量)
"投資科技產業" → [0.21, -0.43, 0.65, ...] (相似向量)
```

**使用場景**:
- 即使使用者用不同措辭詢問,系統也能找到相關記憶
- 例如: "投資偏好" 和 "喜歡的股票類型" 會被視為相似查詢

### 3. ChromaDB 向量資料庫

**ChromaDB** 是本地向量資料庫,用於:
- 儲存向量嵌入
- 執行高效的相似性搜索 (使用 HNSW 算法)
- 與 Mem0 深度整合

### 4. 短期 vs 長期記憶

| 類型 | 儲存位置 | 內容 | 保留時間 |
|------|---------|------|----------|
| **短期記憶** | SQLite | 完整對話歷史 | 30 天 |
| **長期記憶** | ChromaDB (via Mem0) | 提取的偏好/事實 | 永久 |

---

## 🏗 技術架構

### 系統架構圖

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Frontend)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ HTML/CSS │  │  app.js  │  │ storage  │                  │
│  │          │  │          │  │(localStorage)│               │
│  └──────────┘  └──────────┘  └──────────┘                  │
└───────────────────────┬─────────────────────────────────────┘
                        │ HTTP/JSON
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    後端 FastAPI (Python)                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              API Layer (routes/chat.py)              │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │                  Service Layer                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐ │  │
│  │  │ Conversation│  │   Memory    │  │     LLM      │ │  │
│  │  │  Service    │  │  Service    │  │   Service    │ │  │
│  │  └─────────────┘  └─────────────┘  └──────────────┘ │  │
│  └──────────────────────┬───────────────────────────────┘  │
│                         │                                    │
│  ┌──────────────────────┴───────────────────────────────┐  │
│  │              Storage & External APIs                  │  │
│  │  ┌─────────┐  ┌─────────┐  ┌──────────────────────┐ │  │
│  │  │ SQLite  │  │  Mem0   │  │   Google Gemini API  │ │  │
│  │  │         │  │ ChromaDB│  │  (LLM + Embeddings)  │ │  │
│  │  └─────────┘  └─────────┘  └──────────────────────┘ │  │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### 技術棧詳解

#### 後端框架
- **FastAPI** (0.104.1)
  - 高效能異步 Python Web 框架
  - 自動生成 API 文件 (Swagger UI)
  - 內建資料驗證 (Pydantic)

#### 語言模型
- **Google Gemini 2.5 Flash**
  - 用於對話生成
  - 支援繁體中文
  - 低延遲、高品質回應

#### 嵌入模型
- **Google Embeddings** (gemini-embedding-001)
  - 生成 768 維向量
  - 支援多語言語義理解

#### 記憶系統
- **Mem0** (0.0.10)
  - 自動記憶提取和管理
  - 整合 LLM + Embeddings + Vector DB

#### 資料庫
- **SQLite**
  - 輕量級關聯式資料庫
  - 儲存對話歷史和中繼資料

- **ChromaDB**
  - 向量資料庫
  - 高效語義搜索

---

## 🔄 資料流程

### 完整對話流程

```
1. 使用者發送訊息
   ↓
2. 前端透過 API 發送到後端
   POST /api/v1/chat
   {
     "user_id": "uuid-123",
     "message": "我偏好科技股"
   }
   ↓
3. ConversationService.process_message()
   ├─ 3.1 儲存使用者訊息到 SQLite
   ├─ 3.2 從 Mem0 搜索相關記憶
   │      MemoryService.search_memories()
   │      ↓
   │      Mem0 → Embeddings API → ChromaDB 向量搜索
   │      ↓
   │      返回: ["使用者偏好科技股", "風險承受度中等"]
   │
   ├─ 3.3 組合上下文 (對話歷史 + 記憶)
   │      context = conversation_history + memories
   │
   ├─ 3.4 呼叫 LLM 生成回應
   │      LLMService.generate_response(context)
   │      ↓
   │      Google Gemini API
   │      ↓
   │      返回: "根據您偏好科技股..."
   │
   ├─ 3.5 儲存助理回應到 SQLite
   │
   └─ 3.6 從使用者訊息提取新記憶
          MemoryService.add_memory_from_message()
          ↓
          Mem0.add() → 自動提取 → 儲存到 ChromaDB
   ↓
4. 返回回應給前端
   {
     "conversation_id": "conv-456",
     "assistant_message": {...},
     "memories_used": [...]
   }
```

### 記憶提取流程

```
使用者訊息: "我偏好長期投資科技股，風險承受度中等"
   ↓
Mem0.add(messages=[{"role": "user", "content": "..."}])
   ↓
內部流程:
1. LLM 分析訊息 (Gemini)
   → 識別: 包含投資偏好信息

2. 提取關鍵信息
   → "使用者偏好長期投資科技股"
   → "使用者風險承受度為中等"

3. 生成向量嵌入 (Google Embeddings)
   → embedding_1: [0.23, -0.45, ...]
   → embedding_2: [0.31, -0.52, ...]

4. 儲存到 ChromaDB
   → collection: "investment_memories"
   → metadata: {user_id, created_at, category}
   ↓
返回: memory_id
```

---

## 🚀 安裝與設置

### 前置需求

- Python 3.12+
- Google Cloud 帳號 (用於 Gemini API)
- Git

### 步驟 1: 複製專案

```bash
git clone <repository-url>
cd mem0Chatbot
```

### 步驟 2: 設置 Python 環境

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安裝依賴
cd backend
pip install -r requirements.txt
```

### 步驟 3: 取得 Google API 金鑰

1. 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 點擊 "Create API Key"
3. 複製 API 金鑰

### 步驟 4: 設置環境變數

在 `backend/` 目錄下建立 `.env` 檔案:

```bash
# backend/.env
GOOGLE_API_KEY=your_api_key_here

# 資料庫設定
DATABASE_URL=sqlite:///./data/app.db
CHROMA_PATH=./data/chroma

# Mem0 設定
MEM0_LLM_MODEL=gemini-2.0-flash-exp
MEM0_EMBEDDER_MODEL=text-embedding-004

# CORS 設定
CORS_ORIGINS=["http://localhost:3000", "http://127.0.0.1:3000"]

# 日誌設定
LOG_LEVEL=INFO
```

### 步驟 5: 初始化資料庫

```bash
# 確保在 backend/ 目錄下
mkdir -p data/chroma

# 資料庫會在首次啟動時自動建立
```

---

## 🎮 啟動與測試

### 啟動後端伺服器

```bash
cd backend
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

成功啟動後會看到:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     應用程式啟動中...
INFO:     資料庫已初始化
INFO:     嵌入服務已初始化
INFO:     LLM 服務已初始化
INFO:     記憶服務已初始化
```

### 啟動前端

```bash
# 在專案根目錄
cd frontend

# 使用 Python 內建 HTTP 伺服器
python -m http.server 3000
```

前端會在 `http://localhost:3000` 啟動

### 測試 API 端點

#### 方法 1: 使用瀏覽器測試前端

1. 開啟 `http://localhost:3000`
2. 輸入訊息測試對話
3. 觀察側邊欄顯示的記憶

#### 方法 2: 使用 curl 測試 API

```bash
# 健康檢查
curl http://localhost:8000/health

# 發送聊天訊息
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "我偏好科技股"
  }'
```

#### 方法 3: 使用 VS Code REST Client

在專案中建立 `test.http` 檔案:

```http
### 變數定義
@baseUrl = http://localhost:8000/api/v1
@userId = 550e8400-e29b-41d4-a716-446655440000

### 1. 健康檢查
GET http://localhost:8000/health

### 2. 發送首則訊息
POST {{baseUrl}}/chat
Content-Type: application/json

{
  "user_id": "{{userId}}",
  "message": "你好，我想了解美股投資"
}

### 3. 延續對話並表達偏好
POST {{baseUrl}}/chat
Content-Type: application/json

{
  "user_id": "{{userId}}",
  "conversation_id": "從上一個回應取得",
  "message": "我偏好長期投資科技股，風險承受度中等"
}
```

---

## 🎯 核心功能詳解

### 功能 1: 自動記憶提取

**位置**: `backend/src/services/memory_service.py:276`

```python
def add_memory_from_message(
    cls,
    user_id: str,
    message_content: str,
    metadata: Optional[Dict] = None,
) -> Optional[str]:
    """從訊息中自動擷取並儲存記憶"""

    # 呼叫 Mem0 API
    result = cls._mem0_client.add(
        messages=[
            {
                "role": "user",
                "content": message_content,
            }
        ],
        user_id=user_id,
        metadata=meta,
    )
```

**工作原理**:
1. 接收使用者訊息
2. 使用 Mem0 的 `add()` API
3. Mem0 內部使用 LLM 分析訊息
4. 自動識別值得記住的信息
5. 生成向量並儲存到 ChromaDB

**何時觸發**:
- 每次使用者發送訊息後
- 在 LLM 回應生成之後
- 不會阻塞對話流程(即使失敗也繼續)

### 功能 2: 語義記憶搜索

**位置**: `backend/src/services/memory_service.py:108`

```python
def search_memories(
    cls,
    user_id: str,
    query: str,
    top_k: int = 5,
) -> List[Dict]:
    """搜索相關記憶"""

    # 使用 Mem0 搜索
    results = cls._mem0_client.search(
        query=query,
        user_id=user_id,
        limit=top_k,
    )
```

**搜索流程**:
```
1. 查詢文字: "使用者的投資偏好"
   ↓
2. 生成查詢向量 (Google Embeddings)
   query_vector = [0.25, -0.47, ...]
   ↓
3. ChromaDB 向量搜索 (HNSW)
   找出最相似的 5 個向量
   ↓
4. 計算相似度分數
   memory_1: 0.92 (最相關)
   memory_2: 0.85
   memory_3: 0.78
   ...
   ↓
5. 返回排序後的記憶列表
```

**特色**:
- **語義理解**: "投資偏好" 和 "喜歡的股票" 會被視為相似
- **相關性排序**: 最相關的記憶排在前面
- **用戶隔離**: 只搜索該使用者的記憶

### 功能 3: 對話歷史管理

**位置**: `backend/src/services/conversation_service.py`

```python
def process_message(
    user_id: str,
    conversation_id: Optional[int],
    message: str,
) -> Dict:
    """處理使用者訊息的完整流程"""

    # 1. 取得或建立對話
    conversation = get_or_create_conversation(user_id, conversation_id)

    # 2. 儲存使用者訊息
    user_msg = save_message(conversation.id, "user", message)

    # 3. 搜索相關記憶
    memories = MemoryService.search_memories(user_id, message)

    # 4. 構建上下文
    history = get_conversation_history(conversation.id, limit=10)
    context = build_context(history, memories)

    # 5. 生成 LLM 回應
    response = LLMService.generate_response(context)

    # 6. 儲存助理回應
    assistant_msg = save_message(conversation.id, "assistant", response)

    # 7. 提取新記憶
    MemoryService.add_memory_from_message(user_id, message)

    return {
        "conversation_id": conversation.id,
        "assistant_message": assistant_msg,
        "memories_used": memories
    }
```

### 功能 4: LLM 回應生成

**位置**: `backend/src/services/llm_service.py`

```python
def generate_response(
    cls,
    messages: List[Dict],
    memories: List[Dict] = None,
) -> str:
    """使用 Google Gemini 生成回應"""

    # 準備系統提示
    system_prompt = """
    你是一位專業的投資顧問助理。
    請使用繁體中文回應。
    根據使用者的偏好提供個性化建議。
    """

    # 注入記憶到上下文
    if memories:
        memory_context = "\n".join([
            f"- {mem['content']}"
            for mem in memories
        ])
        system_prompt += f"\n\n使用者的偏好:\n{memory_context}"

    # 呼叫 Gemini API
    response = cls._gemini_client.generate_content(
        contents=[
            {"role": "system", "content": system_prompt},
            *messages
        ],
        temperature=0.7,
    )

    return response.text
```

**上下文組合策略**:
```
最終 Prompt = 系統提示 + 使用者記憶 + 對話歷史 + 當前訊息

範例:
"""
[系統提示]
你是一位專業的投資顧問助理...

[使用者記憶]
- 使用者偏好長期投資科技股
- 使用者風險承受度為中等

[對話歷史]
User: 你好，我想了解美股投資
Assistant: 很高興為您介紹...

[當前訊息]
User: 最近有哪些值得關注的股票?
"""
```

---

## 🔌 API 端點說明

### 基本資訊

- **Base URL**: `http://localhost:8000/api/v1`
- **Content-Type**: `application/json`
- **編碼**: UTF-8

### 端點列表

#### 1. 健康檢查

```http
GET /health
```

**回應**:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

#### 2. 發送聊天訊息

```http
POST /api/v1/chat
```

**請求體**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "conversation_id": "可選，首次留空",
  "message": "我偏好科技股"
}
```

**回應**:
```json
{
  "code": "SUCCESS",
  "message": "聊天回應已生成",
  "data": {
    "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
    "user_message": {
      "id": 1,
      "role": "user",
      "content": "我偏好科技股",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    "assistant_message": {
      "id": 2,
      "role": "assistant",
      "content": "了解您的投資偏好！根據您對科技股的興趣...",
      "timestamp": "2025-01-15T10:30:02Z"
    },
    "memories_used": [
      {
        "id": "mem_abc123",
        "content": "使用者偏好科技股",
        "metadata": {
          "relevance": 0.92,
          "category": "preference"
        }
      }
    ]
  }
}
```

---

#### 3. 建立新對話

```http
POST /api/v1/conversations
```

**請求體**:
```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**回應**:
```json
{
  "code": "SUCCESS",
  "data": {
    "id": "conv-123",
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2025-01-15T10:30:00Z",
    "status": "active",
    "message_count": 0
  }
}
```

---

#### 4. 取得對話訊息

```http
GET /api/v1/conversations/{conversation_id}/messages?limit=50
```

**回應**:
```json
{
  "code": "SUCCESS",
  "data": [
    {
      "id": 1,
      "conversation_id": "conv-123",
      "role": "user",
      "content": "你好",
      "timestamp": "2025-01-15T10:30:00Z"
    },
    {
      "id": 2,
      "conversation_id": "conv-123",
      "role": "assistant",
      "content": "您好！我是您的投資顧問助理...",
      "timestamp": "2025-01-15T10:30:02Z"
    }
  ],
  "meta": {
    "total": 2,
    "count": 2
  }
}
```

---

### 錯誤回應格式

```json
{
  "code": "VALIDATION_ERROR",
  "message": "user_id 必須為有效的 UUID v4",
  "details": {},
  "request_id": "req-abc123"
}
```

**常見錯誤碼**:
- `400 VALIDATION_ERROR` - 請求驗證失敗
- `404 NOT_FOUND` - 資源未找到
- `500 MEMORY_ERROR` - 記憶操作失敗
- `500 DATABASE_ERROR` - 資料庫錯誤
- `503 LLM_ERROR` - LLM 服務不可用

---

## 📁 專案結構

```
mem0Chatbot/
├── backend/                    # 後端程式碼
│   ├── src/
│   │   ├── main.py            # FastAPI 應用程式入口
│   │   ├── config/
│   │   │   └── settings.py    # 設定檔 (環境變數)
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   └── chat.py    # 聊天 API 路由
│   │   │   └── schemas/
│   │   │       └── chat.py    # Pydantic 資料模型
│   │   ├── services/
│   │   │   ├── conversation_service.py  # 對話管理
│   │   │   ├── memory_service.py        # Mem0 記憶服務
│   │   │   ├── llm_service.py           # Gemini LLM 服務
│   │   │   └── embedding_service.py     # 嵌入服務
│   │   ├── storage/
│   │   │   ├── database.py              # SQLite 資料庫
│   │   │   └── storage_service.py       # 儲存服務
│   │   ├── models/
│   │   │   └── conversation.py          # 資料模型
│   │   └── utils/
│   │       ├── logger.py                # 日誌工具
│   │       └── exceptions.py            # 自定義例外
│   ├── tests/                 # 測試檔案
│   │   ├── unit/             # 單元測試
│   │   ├── integration/      # 整合測試
│   │   └── conftest.py       # pytest 設定
│   ├── data/                 # 資料目錄
│   │   ├── app.db           # SQLite 資料庫
│   │   └── chroma/          # ChromaDB 向量儲存
│   ├── requirements.txt      # Python 依賴
│   └── .env                 # 環境變數 (需自行建立)
│
├── frontend/                 # 前端程式碼
│   ├── index.html           # 主頁面
│   ├── css/
│   │   └── style.css        # 樣式
│   └── js/
│       ├── app.js           # 主應用邏輯
│       ├── api.js           # API 呼叫
│       └── storage.js       # localStorage 管理
│
├── specs/                    # 功能規格文件
│   └── 001-mem0-investment-advisor/
│       ├── spec.md          # 功能規格書
│       ├── quickstart.md    # 快速開始指南
│       ├── data-model.md    # 資料模型
│       └── plan.md          # 實作計畫
│
└── PROJECT_TUTORIAL.md       # 本教學文件
```

### 關鍵檔案說明

| 檔案 | 用途 |
|------|------|
| `backend/src/main.py` | FastAPI 應用程式入口，設定路由和中介軟體 |
| `backend/src/services/memory_service.py` | Mem0 整合，處理記憶提取和搜索 |
| `backend/src/services/conversation_service.py` | 對話流程的核心邏輯 |
| `backend/src/services/llm_service.py` | Google Gemini API 整合 |
| `backend/src/storage/database.py` | SQLite 資料庫操作 |
| `backend/src/config/settings.py` | 環境變數和設定管理 |
| `frontend/js/app.js` | 前端主邏輯，處理 UI 互動 |

---

## 🛠 開發與擴充

### 執行測試

```bash
cd backend

# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/unit/test_memory_service.py

# 執行測試並顯示覆蓋率
pytest --cov=src tests/

# 執行整合測試
pytest tests/integration/
```

### 新增 API 端點

**步驟 1**: 在 `backend/src/api/schemas/chat.py` 定義資料模型

```python
class NewFeatureRequest(BaseModel):
    user_id: str
    parameter: str
```

**步驟 2**: 在 `backend/src/api/routes/chat.py` 新增路由

```python
@router.post("/new-feature")
async def new_feature(request: Request, payload: NewFeatureRequest):
    # 實作邏輯
    return {"result": "success"}
```

### 自定義記憶提取邏輯

修改 `backend/src/services/memory_service.py`:

```python
def add_memory_from_message(cls, user_id: str, message_content: str):
    # 新增自定義過濾邏輯
    if "關鍵字" in message_content:
        # 特殊處理
        pass

    # 呼叫 Mem0
    result = cls._mem0_client.add(...)
```

### 更換 LLM 模型

修改 `backend/.env`:

```bash
# 使用不同的 Gemini 模型
MEM0_LLM_MODEL=gemini-1.5-pro

# 或使用其他提供商 (需修改程式碼)
```

### 新增前端功能

修改 `frontend/js/app.js`:

```javascript
// 新增按鈕事件
document.getElementById('newButton').addEventListener('click', async () => {
    // 呼叫 API
    const response = await fetch('/api/v1/new-feature', {
        method: 'POST',
        body: JSON.stringify({...})
    });
});
```

---

## ❓ 常見問題

### Q1: 啟動時出現 "Mem0 初始化失敗"

**原因**: Google API 金鑰無效或未設定

**解決方法**:
1. 檢查 `.env` 檔案中的 `GOOGLE_API_KEY`
2. 確認金鑰有效: 訪問 https://makersuite.google.com/app/apikey
3. 確認已啟用 Gemini API

### Q2: 記憶未正確儲存

**原因**: ChromaDB 路徑錯誤或權限問題

**解決方法**:
```bash
# 確認目錄存在
mkdir -p backend/data/chroma

# 檢查權限
chmod -R 755 backend/data/
```

### Q3: LLM 回應超時

**原因**: 網路連線問題或 API 配額用盡

**解決方法**:
1. 檢查網路連線
2. 訪問 Google Cloud Console 檢查配額
3. 增加 timeout 設定

### Q4: CORS 錯誤

**原因**: 前端網域未加入 CORS 允許清單

**解決方法**:
修改 `backend/.env`:
```bash
CORS_ORIGINS=["http://localhost:3000", "你的前端網域"]
```

### Q5: 對話歷史遺失

**原因**: SQLite 資料庫檔案被刪除

**解決方法**:
- 資料庫位於 `backend/data/app.db`
- 確保該目錄有寫入權限
- 使用備份恢復 (如果有)

### Q6: 記憶搜索結果不相關

**原因**: 向量嵌入品質問題或搜索參數不當

**解決方法**:
```python
# 調整搜索參數
memories = MemoryService.search_memories(
    user_id=user_id,
    query=query,
    top_k=10  # 增加返回數量
)
```

### Q7: 如何清除所有資料重新開始?

```bash
# 停止伺服器
# 刪除資料庫和向量儲存
rm -rf backend/data/app.db
rm -rf backend/data/chroma/

# 重新啟動伺服器
uvicorn src.main:app --reload
```

---

## 📚 延伸閱讀

### 官方文件

- **Mem0 文件**: https://docs.mem0.ai/
- **Google Gemini API**: https://ai.google.dev/docs
- **FastAPI 文件**: https://fastapi.tiangolo.com/
- **ChromaDB 文件**: https://docs.trychroma.com/

### 相關概念

- **向量嵌入 (Embeddings)**: 將文字轉換為數值向量
- **語義搜索 (Semantic Search)**: 基於語義相似性的搜索
- **RAG (Retrieval-Augmented Generation)**: 檢索增強生成
- **HNSW 算法**: 高效向量搜索算法

### 專案內文件

- `specs/001-mem0-investment-advisor/spec.md` - 完整功能規格
- `specs/001-mem0-investment-advisor/quickstart.md` - 快速開始指南
- `specs/001-mem0-investment-advisor/data-model.md` - 資料模型設計
- `TESTING_GUIDE.md` - 測試指南

---

## 🎓 學習路徑建議

### 初學者

1. **理解核心概念** (1-2 小時)
   - 閱讀本文件的「核心概念」章節
   - 了解 Mem0、向量嵌入、ChromaDB 的作用

2. **安裝並執行專案** (30 分鐘)
   - 按照「安裝與設置」步驟操作
   - 成功啟動前後端

3. **測試基本功能** (1 小時)
   - 使用前端介面發送訊息
   - 觀察記憶的提取和使用
   - 使用 curl 測試 API

4. **閱讀關鍵程式碼** (2-3 小時)
   - `backend/src/services/memory_service.py`
   - `backend/src/services/conversation_service.py`
   - `backend/src/api/routes/chat.py`

### 進階開發者

1. **深入理解架構** (2-3 小時)
   - 閱讀完整資料流程
   - 理解各層職責 (API → Service → Storage)
   - 研究錯誤處理機制

2. **實作擴充功能** (4-6 小時)
   - 新增自定義記憶類別
   - 實作記憶更新/刪除 API
   - 新增對話摘要功能

3. **效能優化** (3-4 小時)
   - 分析記憶搜索效能
   - 優化資料庫查詢
   - 實作快取機制

4. **生產部署** (2-3 小時)
   - 設置 Docker 容器
   - 部署到雲端平台
   - 設定監控和日誌

---

## 📞 支援與貢獻

### 回報問題

如發現 bug 或有功能建議:
1. 檢查是否為已知問題
2. 提供詳細重現步驟
3. 附上錯誤日誌

### 貢獻程式碼

1. Fork 專案
2. 建立功能分支
3. 撰寫測試
4. 提交 Pull Request

---

## 📄 授權

本專案為教學用途，請遵循相關授權條款。

---

**最後更新**: 2025-11-05
**版本**: 1.0.0
**維護者**: mem0Chatbot Team

如有任何問題,歡迎提出! 🚀
