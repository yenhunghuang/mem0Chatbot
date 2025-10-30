# 資料模型設計：個人化投顧助理（Mem0 練習版）

**版本**: v1.0  
**日期**: 2025-10-30  
**狀態**: Draft

## 概述

本文件定義投顧助理系統的核心資料實體、關係和驗證規則。

## 領域模型圖

```
┌─────────────┐       1:N      ┌──────────────────┐
│   User      │───────────────>│  Conversation    │
│  (UUID)     │                │   Session        │
└─────────────┘                └──────────────────┘
       │                              │
       │ 1:N                          │ 1:N
       │                              │
       v                              v
┌─────────────┐                ┌──────────────────┐
│  Memory     │                │    Message       │
│  Fragment   │                │                  │
└─────────────┘                └──────────────────┘
```

## 資料實體

### 1. User (使用者)

**描述**: 代表一個匿名使用者，由前端 UUID 識別

**欄位**:

| 欄位名稱      | 類型     | 必填 | 說明                                    |
|---------------|----------|------|-----------------------------------------|
| `user_id`     | String   | ✓    | UUID v4，前端產生                       |
| `created_at`  | DateTime | ✓    | 首次建立時間                            |
| `last_seen`   | DateTime | ✓    | 最後活動時間                            |

**驗證規則**:
- `user_id`: 必須符合 UUID v4 格式 (RFC 4122)
- `created_at` ≤ `last_seen`

**資料來源**: 前端 localStorage

**備註**: 此實體在 SQLite 中可能不需要獨立資料表，因為所有資料都以 `user_id` 為 foreign key 關聯

---

### 2. ConversationSession (對話會話)

**描述**: 一次完整的對話流程，包含多個訊息往返

**欄位**:

| 欄位名稱          | 類型     | 必填 | 說明                                    |
|-------------------|----------|------|-----------------------------------------|
| `conversation_id` | String   | ✓    | UUID v4，對話唯一識別碼                 |
| `user_id`         | String   | ✓    | 關聯使用者 ID                           |
| `created_at`      | DateTime | ✓    | 對話開始時間                            |
| `last_activity`   | DateTime | ✓    | 最後一則訊息時間                        |
| `status`          | Enum     | ✓    | `active`, `archived`, `expired`         |
| `message_count`   | Integer  | ✓    | 訊息總數（含使用者和助理）              |

**驗證規則**:
- `conversation_id`: UUID v4 格式
- `user_id`: 必須存在對應的 user
- `message_count` ≥ 0
- `status`: 僅允許 `active`, `archived`, `expired`
- `created_at` ≤ `last_activity`

**索引**: 
- Primary Key: `conversation_id`
- Foreign Key: `user_id`
- Index: `(user_id, last_activity DESC)` — 快速查詢使用者最近對話

**生命週期**:
1. **active**: 對話進行中
2. **archived**: 使用者主動歸檔或 30 天無活動
3. **expired**: TTL 觸發，待清理

---

### 3. Message (訊息)

**描述**: 對話中的單一訊息，可能來自使用者或助理

**欄位**:

| 欄位名稱          | 類型     | 必填 | 說明                                    |
|-------------------|----------|------|-----------------------------------------|
| `message_id`      | Integer  | ✓    | 自動遞增 ID                             |
| `conversation_id` | String   | ✓    | 所屬對話                                |
| `role`            | Enum     | ✓    | `user` 或 `assistant`                   |
| `content`         | Text     | ✓    | 訊息內容                                |
| `timestamp`       | DateTime | ✓    | 訊息時間                                |
| `token_count`     | Integer  |      | LLM token 用量（僅 assistant）          |

**驗證規則**:
- `role`: 僅允許 `user` 或 `assistant`
- `content`: 長度 1-10000 字元
- `token_count`: 僅當 `role == assistant` 時必填

**索引**:
- Primary Key: `message_id`
- Foreign Key: `conversation_id`
- Index: `(conversation_id, timestamp ASC)` — 按時間順序檢索訊息

**業務邏輯**:
- 使用者訊息和助理回應必須交替出現（先 user 後 assistant）
- 每次儲存 assistant 訊息時更新 `conversation.last_activity`

---

### 4. MemoryFragment (記憶片段)

**描述**: 從對話中提取的長期記憶，由 Mem0 管理

**欄位**:

| 欄位名稱        | 類型       | 必填 | 說明                                    |
|-----------------|------------|------|-----------------------------------------|
| `memory_id`     | String     | ✓    | Mem0 產生的 ID                          |
| `user_id`       | String     | ✓    | 記憶所屬使用者                          |
| `content`       | Text       | ✓    | 記憶內容（自然語言描述）                |
| `category`      | Enum       |      | `preference`, `fact`, `behavior`        |
| `source_msg_id` | Integer    |      | 來源訊息 ID                             |
| `created_at`    | DateTime   | ✓    | 建立時間                                |
| `updated_at`    | DateTime   |      | 更新時間（記憶可能被修正）              |
| `relevance`     | Float      |      | 相關性分數 (0.0-1.0)                    |
| `embedding`     | Vector     | ✓    | 向量嵌入（由 Chroma 管理）              |

**驗證規則**:
- `content`: 長度 1-500 字元
- `category`: 可選值為 `preference`, `fact`, `behavior`
- `relevance`: 範圍 0.0 ~ 1.0

**儲存層**:
- **元資料**: SQLite (user_id, content, category, created_at)
- **向量**: ChromaDB (embedding + metadata)
- **整合**: Mem0 SDK 自動同步兩者

**索引**:
- Primary Key: `memory_id`
- Foreign Key: `user_id`
- Vector Index: Chroma 自動建立 HNSW 索引

**業務邏輯**:
- 每個使用者最多儲存 1000 條記憶（達到後清理低相關性記憶）
- 記憶提取觸發條件：
  - 使用者明確表達偏好（例如：「我喜歡...」）
  - 助理詢問後使用者回答
  - 使用者提供個人資訊（風險承受度、投資目標等）

---

### 5. UserPreference (使用者偏好總結)

**描述**: 高階偏好總結，從記憶片段彙總而來（選用實體）

**欄位**:

| 欄位名稱              | 類型     | 必填 | 說明                                    |
|-----------------------|----------|------|-----------------------------------------|
| `user_id`             | String   | ✓    | 關聯使用者                              |
| `investment_goal`     | String   |      | 投資目標（例如：退休規劃）              |
| `risk_tolerance`      | Enum     |      | `low`, `medium`, `high`                 |
| `preferred_sectors`   | Array    |      | 偏好產業（例如：["科技", "醫療"]）      |
| `last_updated`        | DateTime | ✓    | 最後更新時間                            |

**驗證規則**:
- `risk_tolerance`: 僅允許 `low`, `medium`, `high`
- `preferred_sectors`: 最多 5 個產業

**備註**: 此實體為選用，可在 MVP 階段省略，直接使用 MemoryFragment 即可

---

## 資料關係

### 主要關聯

```sql
User (1) ─────────── (N) ConversationSession
         ─────────── (N) MemoryFragment

ConversationSession (1) ─────────── (N) Message

MemoryFragment (N) ─────────── (1) Message (optional)
```

### 外鍵約束

- `ConversationSession.user_id` → `User.user_id`
- `Message.conversation_id` → `ConversationSession.conversation_id`
- `MemoryFragment.user_id` → `User.user_id`
- `MemoryFragment.source_msg_id` → `Message.message_id` (nullable)

---

## Pydantic 模型定義

### API 請求/回應模型

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, List
from enum import Enum

class RoleEnum(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"

class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    EXPIRED = "expired"

class MessageCreate(BaseModel):
    """建立新訊息的請求"""
    user_id: str = Field(..., description="使用者 UUID")
    conversation_id: Optional[str] = Field(None, description="對話 ID（首次留空）")
    content: str = Field(..., min_length=1, max_length=10000)
    
    @validator('user_id')
    def validate_uuid(cls, v):
        import uuid
        try:
            uuid.UUID(v, version=4)
        except ValueError:
            raise ValueError('user_id 必須為有效的 UUID v4')
        return v

class MessageResponse(BaseModel):
    """助理回應"""
    message_id: int
    conversation_id: str
    role: RoleEnum
    content: str
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    """對話請求"""
    user_id: str
    conversation_id: Optional[str] = None
    message: str = Field(..., min_length=1, max_length=10000)

class ChatResponse(BaseModel):
    """對話回應"""
    conversation_id: str
    user_message: MessageResponse
    assistant_message: MessageResponse
    memories_used: List[str] = Field(default_factory=list, description="使用的記憶內容")

class MemoryResponse(BaseModel):
    """記憶片段回應"""
    memory_id: str
    content: str
    category: Optional[str]
    created_at: datetime
    relevance: Optional[float]

class MemoryListResponse(BaseModel):
    """記憶列表回應"""
    user_id: str
    memories: List[MemoryResponse]
    total: int
```

### 資料庫模型 (內部使用)

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class ConversationDB:
    """對應 SQLite conversations 資料表"""
    conversation_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    status: str
    message_count: int

@dataclass
class MessageDB:
    """對應 SQLite messages 資料表"""
    message_id: int
    conversation_id: str
    role: str
    content: str
    timestamp: datetime
    token_count: Optional[int] = None
```

---

## 資料遷移策略

### 階段 1: MVP (Phase 2)
- 實作 `ConversationSession`, `Message`, `MemoryFragment`
- 省略 `User` 獨立資料表（user_id 作為 foreign key 即可）
- 省略 `UserPreference` 總結實體

### 階段 2: 優化 (Phase 3+)
- 新增 `User` 資料表記錄使用者統計
- 新增 `UserPreference` 快取常用偏好

### 資料庫遷移工具
- 使用 Alembic 管理 SQLite schema 變更
- 版本化遷移腳本存放於 `backend/alembic/versions/`

---

## 效能考量

### 查詢優化
1. **最近對話查詢**:
   ```sql
   SELECT * FROM conversations 
   WHERE user_id = ? AND status = 'active'
   ORDER BY last_activity DESC
   LIMIT 10;
   ```
   索引: `(user_id, last_activity DESC)`

2. **對話訊息載入**:
   ```sql
   SELECT * FROM messages
   WHERE conversation_id = ?
   ORDER BY timestamp ASC;
   ```
   索引: `(conversation_id, timestamp ASC)`

3. **記憶向量搜索**:
   - 使用 Chroma 的 HNSW 索引
   - 預設 top_k=5，平衡精確度和速度

### 資料清理策略
- **短期記憶 TTL**: 30 天無活動的對話標記為 `expired`
- **長期記憶上限**: 每使用者最多 1000 條，超過時刪除低 relevance 記憶
- **定期清理任務**: 每日執行一次 cleanup job

---

## 資料隱私與安全

### 匿名性保護
- 不收集真實姓名、Email、電話
- UUID 無法反向識別使用者
- localStorage 清除後所有資料失去關聯

### 資料保留政策
- 短期記憶: 30 天後自動刪除
- 長期記憶: 無期限（除非使用者清除 localStorage）
- 使用者可隨時清除所有記憶（提供 DELETE /api/memories API）

---

## 驗證清單

- [x] 所有實體定義完整
- [x] 關係與外鍵清晰
- [x] 驗證規則詳細
- [x] Pydantic 模型與憲法原則一致
- [x] 效能索引已規劃
- [x] 資料隱私符合規格

---

**下一步**: 定義 API 合約 (contracts/)
