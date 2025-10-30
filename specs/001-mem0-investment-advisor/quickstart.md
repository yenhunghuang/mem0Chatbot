# 快速開始：個人化投顧助理整合指南

**版本**: v1.0  
**日期**: 2025-10-30  
**目標**: 幫助開發者快速理解系統整合流程和測試場景

## 目的

本文件提供：
1. 核心整合流程說明
2. 端到端測試場景
3. VS Code REST Client 測試範例
4. 常見問題排查

---

## 系統整合流程

### 整合架構圖

```
┌──────────────┐         HTTP           ┌──────────────┐
│              │  ──────────────────>   │              │
│   前端 SPA   │                        │ FastAPI 後端 │
│ (localStorage)│  <──────────────────  │   (Python)   │
└──────────────┘        JSON            └──────┬───────┘
                                               │
                                               │
                    ┌──────────────────────────┼───────────────────┐
                    │                          │                   │
                    v                          v                   v
            ┌───────────────┐       ┌──────────────┐     ┌─────────────┐
            │  Google       │       │   ChromaDB   │     │   SQLite    │
            │  Gemini API   │       │  (Mem0 整合) │     │  (短期記憶) │
            │  (LLM + 嵌入) │       │  (長期記憶)  │     │             │
            └───────────────┘       └──────────────┘     └─────────────┘
```

### 核心整合點

| 整合點                | 說明                                    | 實作模組                |
|-----------------------|-----------------------------------------|-------------------------|
| 前端 → 後端           | HTTP REST API                           | `api/routes/`           |
| 後端 → Gemini         | LLM 對話生成                            | `services/llm_service`  |
| 後端 → Mem0           | 記憶擷取與儲存                          | `services/memory_service` |
| Mem0 → Chroma         | 向量嵌入與檢索                          | Mem0 SDK 自動處理       |
| 後端 → SQLite         | 對話歷史持久化                          | `storage/database`      |

---

## 測試場景

### 場景 1: 首次對話（新使用者）

**目標**: 驗證使用者 UUID 建立、對話初始化、記憶擷取

**前置條件**:
- 後端伺服器運行於 `http://localhost:8000`
- 資料庫已初始化
- Google API 密鑰已設定

**測試步驟**:

1. **前端產生 UUID**:
   ```javascript
   const userId = crypto.randomUUID();
   localStorage.setItem('user_id', userId);
   // 範例: "550e8400-e29b-41d4-a716-446655440000"
   ```

2. **發送首則訊息**:
   ```http
   POST http://localhost:8000/api/v1/chat
   Content-Type: application/json

   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "message": "你好，我想了解美股投資"
   }
   ```

3. **預期回應**:
   ```json
   {
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "user_message": {
       "message_id": 1,
       "role": "user",
       "content": "你好，我想了解美股投資",
       "timestamp": "2025-01-15T10:30:00Z"
     },
     "assistant_message": {
       "message_id": 2,
       "role": "assistant",
       "content": "很高興為您介紹美股投資！美股市場是全球最大的...",
       "timestamp": "2025-01-15T10:30:02Z"
     },
     "memories_used": []
   }
   ```

4. **驗證點**:
   - ✓ `conversation_id` 為新的 UUID
   - ✓ `memories_used` 為空（新使用者無記憶）
   - ✓ 回應時間 < 2 秒（P95）
   - ✓ 回應內容為繁體中文

**後端驗證**:
```python
# 檢查資料庫
SELECT * FROM conversations WHERE user_id = '550e8400-e29b-41d4-a716-446655440000';
# 應返回 1 筆新對話

SELECT * FROM messages WHERE conversation_id = '660e8400-e29b-41d4-a716-446655440001';
# 應返回 2 筆訊息（user + assistant）
```

---

### 場景 2: 表達偏好與記憶擷取

**目標**: 驗證記憶自動擷取、儲存和檢索

**前置條件**:
- 沿用場景 1 的對話

**測試步驟**:

1. **使用者表達偏好**:
   ```http
   POST http://localhost:8000/api/v1/chat
   Content-Type: application/json

   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "message": "我偏好長期投資科技股，風險承受度中等"
   }
   ```

2. **預期回應**:
   ```json
   {
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "user_message": { ... },
     "assistant_message": {
       "content": "了解您的投資偏好！根據您的描述，您適合..."
     },
     "memories_used": []
   }
   ```

3. **檢查記憶是否儲存**:
   ```http
   GET http://localhost:8000/api/v1/memories?user_id=550e8400-e29b-41d4-a716-446655440000
   ```

   **預期回應**:
   ```json
   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "total": 2,
     "memories": [
       {
         "memory_id": "mem_abc123",
         "content": "使用者偏好長期投資科技股",
         "category": "preference",
         "created_at": "2025-01-15T10:32:00Z"
       },
       {
         "memory_id": "mem_def456",
         "content": "使用者風險承受度為中等",
         "category": "preference",
         "created_at": "2025-01-15T10:32:00Z"
       }
     ]
   }
   ```

4. **驗證點**:
   - ✓ Mem0 自動從對話中提取至少 2 條記憶
   - ✓ 記憶內容為中文自然語言描述
   - ✓ `category` 正確標註為 `preference`

---

### 場景 3: 記憶召回（個性化回應）

**目標**: 驗證對話中使用歷史記憶提供個性化回應

**前置條件**:
- 沿用場景 2，使用者已有記憶

**測試步驟**:

1. **詢問相關問題**:
   ```http
   POST http://localhost:8000/api/v1/chat
   Content-Type: application/json

   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "message": "最近有哪些值得關注的股票？"
   }
   ```

2. **預期回應**:
   ```json
   {
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "assistant_message": {
       "content": "根據您偏好長期投資科技股且風險承受度中等，以下是適合的標的：..."
     },
     "memories_used": [
       "使用者偏好長期投資科技股",
       "使用者風險承受度為中等"
     ]
   }
   ```

3. **驗證點**:
   - ✓ `memories_used` 包含相關記憶
   - ✓ 助理回應提及使用者偏好（例如「科技股」「中等風險」）
   - ✓ 回應個性化，非通用建議

---

### 場景 4: 對話歷史檢索

**目標**: 驗證對話歷史完整保存與檢索

**測試步驟**:

1. **檢索對話列表**:
   ```http
   GET http://localhost:8000/api/v1/conversations?user_id=550e8400-e29b-41d4-a716-446655440000
   ```

   **預期回應**:
   ```json
   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "total": 1,
     "conversations": [
       {
         "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
         "created_at": "2025-01-15T10:30:00Z",
         "last_activity": "2025-01-15T10:35:00Z",
         "status": "active",
         "message_count": 6
       }
     ]
   }
   ```

2. **檢索完整對話**:
   ```http
   GET http://localhost:8000/api/v1/conversations/660e8400-e29b-41d4-a716-446655440001
   ```

   **預期回應**:
   ```json
   {
     "conversation_id": "660e8400-e29b-41d4-a716-446655440001",
     "messages": [
       {
         "message_id": 1,
         "role": "user",
         "content": "你好，我想了解美股投資",
         "timestamp": "2025-01-15T10:30:00Z"
       },
       {
         "message_id": 2,
         "role": "assistant",
         "content": "很高興為您介紹美股投資！...",
         "timestamp": "2025-01-15T10:30:02Z"
       },
       ...
     ]
   }
   ```

3. **驗證點**:
   - ✓ 訊息按時間順序排列
   - ✓ `message_count` 與實際訊息數一致
   - ✓ 使用者和助理訊息交替出現

---

### 場景 5: 記憶管理

**目標**: 驗證記憶更新與刪除功能

**測試步驟**:

1. **更新記憶內容**:
   ```http
   PUT http://localhost:8000/api/v1/memories/mem_abc123
   Content-Type: application/json

   {
     "content": "使用者偏好長期投資美股科技股，特別是 AI 相關企業",
     "category": "preference"
   }
   ```

   **預期回應**: `200 OK` 並返回更新後的記憶

2. **刪除單一記憶**:
   ```http
   DELETE http://localhost:8000/api/v1/memories/mem_def456
   ```

   **預期回應**: `204 No Content`

3. **驗證刪除**:
   ```http
   GET http://localhost:8000/api/v1/memories?user_id=550e8400-e29b-41d4-a716-446655440000
   ```

   **預期回應**: `total` 減少 1，`mem_def456` 不再出現

4. **批量刪除所有記憶**:
   ```http
   POST http://localhost:8000/api/v1/memories/batch-delete
   Content-Type: application/json

   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000"
   }
   ```

   **預期回應**:
   ```json
   {
     "deleted_count": 1,
     "message": "已成功刪除 1 條記憶"
   }
   ```

---

### 場景 6: 錯誤處理

**目標**: 驗證各種錯誤情境的處理

**測試案例**:

1. **無效的 UUID**:
   ```http
   POST http://localhost:8000/api/v1/chat
   Content-Type: application/json

   {
     "user_id": "invalid-uuid",
     "message": "測試訊息"
   }
   ```

   **預期回應**: `400 Bad Request`
   ```json
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "user_id 必須為有效的 UUID v4"
     }
   }
   ```

2. **空訊息**:
   ```http
   POST http://localhost:8000/api/v1/chat
   Content-Type: application/json

   {
     "user_id": "550e8400-e29b-41d4-a716-446655440000",
     "message": ""
   }
   ```

   **預期回應**: `400 Bad Request`
   ```json
   {
     "error": {
       "code": "VALIDATION_ERROR",
       "message": "訊息內容不可為空"
     }
   }
   ```

3. **不存在的對話**:
   ```http
   GET http://localhost:8000/api/v1/conversations/999999999999
   ```

   **預期回應**: `404 Not Found`

---

## VS Code REST Client 測試範例

將以下內容儲存為 `.http` 檔案並使用 VS Code REST Client 擴充功能執行：

```http
### 變數定義
@baseUrl = http://localhost:8000/api/v1
@userId = 550e8400-e29b-41d4-a716-446655440000
@conversationId = 660e8400-e29b-41d4-a716-446655440001

### 1. 健康檢查
GET {{baseUrl}}/health

### 2. 詳細健康檢查
GET {{baseUrl}}/health/detailed

### 3. 發送首則訊息
POST {{baseUrl}}/chat
Content-Type: application/json

{
  "user_id": "{{userId}}",
  "message": "你好，我想了解美股投資"
}

### 4. 延續對話
POST {{baseUrl}}/chat
Content-Type: application/json

{
  "user_id": "{{userId}}",
  "conversation_id": "{{conversationId}}",
  "message": "我偏好長期投資科技股，風險承受度中等"
}

### 5. 檢索記憶
GET {{baseUrl}}/memories?user_id={{userId}}

### 6. 語義搜索記憶
POST {{baseUrl}}/memories/search
Content-Type: application/json

{
  "user_id": "{{userId}}",
  "query": "使用者的投資偏好",
  "top_k": 5
}

### 7. 檢索對話列表
GET {{baseUrl}}/conversations?user_id={{userId}}

### 8. 檢索完整對話
GET {{baseUrl}}/conversations/{{conversationId}}

### 9. 刪除所有記憶
POST {{baseUrl}}/memories/batch-delete
Content-Type: application/json

{
  "user_id": "{{userId}}"
}
```

---

## 效能驗證

### 關鍵指標

| 指標                    | 憲法要求     | 驗證方法                          |
|-------------------------|--------------|-----------------------------------|
| LLM 回應時間 (P95)      | < 2 秒       | 測量 `/chat` 端點回應時間         |
| 記憶檢索時間 (P95)      | < 500 毫秒   | 測量 Mem0 `search()` 執行時間     |
| 對話載入時間 (P95)      | < 5 秒       | 測量載入 50 條訊息的時間          |

### 測試工具

使用 `pytest-benchmark` 進行效能測試：

```python
# tests/performance/test_benchmarks.py
def test_chat_response_time(benchmark, client, test_user_id):
    def chat():
        return client.post("/api/v1/chat", json={
            "user_id": test_user_id,
            "message": "測試訊息"
        })
    
    result = benchmark(chat)
    assert result.status_code == 200
    # benchmark 自動記錄執行時間
```

---

## 常見問題排查

### 問題 1: LLM 回應超時

**症狀**: `/chat` 端點超過 5 秒未回應

**可能原因**:
- Google API 配額用盡
- 網路連線不穩定
- Prompt 過長

**排查步驟**:
1. 檢查 Google API 配額：https://console.cloud.google.com/
2. 測試 LLM 連線：`GET /health/detailed`
3. 檢查日誌：搜尋 `google.api_core.exceptions`

---

### 問題 2: 記憶未正確擷取

**症狀**: 對話後查詢 `/memories` 為空

**可能原因**:
- 使用者訊息未明確表達偏好
- Mem0 配置錯誤
- ChromaDB 連線失效

**排查步驟**:
1. 檢查 Mem0 配置：確認 `vector_store.provider` 為 `chroma`
2. 測試 Chroma 連線：檢查 `./data/chroma` 目錄是否存在
3. 手動觸發記憶擷取：
   ```python
   memory.add(
       "使用者明確說：我喜歡科技股",
       user_id=test_user_id
   )
   ```

---

### 問題 3: 對話歷史遺失

**症狀**: 重啟後對話列表為空

**可能原因**:
- SQLite 資料庫未持久化
- 資料庫路徑錯誤

**排查步驟**:
1. 檢查資料庫檔案：`ls ./data/app.db`
2. 驗證資料庫連線字串：應為 `sqlite:///./data/app.db`（注意三個斜線）
3. 檢查檔案權限：確保應用程式可寫入 `./data` 目錄

---

## 下一步

完成測試後，進入 Phase 2（任務分解階段）：
1. 使用 `/speckit.tasks` 生成 `tasks.md`
2. 根據任務清單實作功能
3. 每完成一個任務，執行對應測試場景驗證

---

**相關文件**:
- [API 合約](./contracts/)
- [資料模型](./data-model.md)
- [實作計畫](./plan.md)
