# Tasks: 個人化投顧助理（Mem0 練習版）

**Input**: 設計文件來自 `/specs/001-mem0-investment-advisor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: 根據憲法測試標準原則，測試為必需項目。所有功能必須有 90%+ 測試覆蓋率。單元測試必須在實作前撰寫（TDD 方法）。

**Organization**: 任務依使用者故事分組，以實現每個故事的獨立實作與測試。

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 可平行執行（不同檔案，無依賴）
- **[Story]**: 任務屬於哪個使用者故事（例如 US1, US2, US3）
- 描述中包含確切的檔案路徑

## Phase 1: Setup（共享基礎設施）

**Purpose**: 專案初始化與基本結構建立

- [x] T001 依照實作計劃建立專案目錄結構（backend/src/, frontend/, tests/, data/）
- [x] T002 初始化 Python 3.12 專案，建立 backend/requirements.txt 包含 FastAPI, Mem0, Google SDKs, ChromaDB, SQLite, pytest 依賴
- [x] T003 [P] 建立 backend/.env.example 範本檔案，包含 GOOGLE_API_KEY, DATABASE_URL, CHROMA_PATH 環境變數
- [x] T004 [P] 建立 backend/src/config/settings.py 使用 pydantic-settings 載入環境變數
- [x] T005 [P] 配置 ruff 和 black 格式化工具（backend/pyproject.toml）
- [x] T006 [P] 建立 .gitignore 排除 data/, .env, __pycache__, .pytest_cache

---

## Phase 2: Foundational（阻塞性前置條件）

**Purpose**: 所有使用者故事實作前必須完成的核心基礎設施

**⚠️ CRITICAL**: 在此階段完成前，任何使用者故事工作都不能開始

- [x] T007 建立 backend/src/utils/logger.py 實作統一日誌記錄器
- [x] T008 [P] 建立 backend/src/utils/exceptions.py 定義自訂例外類別（ValidationError, MemoryError, LLMError）
- [x] T009 建立 backend/src/storage/database.py 實作 SQLite 連線管理與 WAL 模式設定
- [x] T010 [P] 建立 backend/src/storage/schema.sql 定義 conversations 和 messages 資料表結構
- [x] T011 實作 backend/src/storage/database.py 中的 init_database() 函式執行 schema.sql
- [x] T012 [P] 建立 backend/src/services/embedding_service.py 整合 Google Embeddings API (gemini-embedding-001)
- [x] T013 [P] 建立 backend/src/services/llm_service.py 整合 Google Gemini 2.5 Flash SDK
- [x] T014 建立 backend/src/services/memory_service.py 初始化 Mem0 客戶端（Chroma backend + Google Embeddings）
- [x] T015 建立 backend/src/api/schemas/__init__.py 和 backend/src/api/schemas/common.py 定義錯誤回應 schema
- [x] T016 建立 backend/src/main.py FastAPI 應用入口，設定 CORS, exception handlers, 註冊路由
- [x] T017 [P] 建立 backend/tests/conftest.py 配置 pytest fixtures（mock_mem0, mock_llm, test_db, test_client）

**Checkpoint**: 基礎就緒 - 使用者故事實作現在可以平行開始

---

## Phase 3: User Story 1 - 基礎對話與記憶建立 (Priority: P1) 🎯 MVP

**Goal**: 使用者可直接開始對話，系統自動從自然語言中擷取投資偏好並儲存至 Mem0

**Independent Test**: 發送包含投資偏好的訊息（如「我偏好科技股」），檢查 Mem0 是否正確儲存記憶，並可查詢到該記憶

### Tests for User Story 1 (REQUIRED per Constitution) ⚠️

> **NOTE: 先寫這些測試，確保在實作前它們會 FAIL**

- [x] T018 [P] [US1] 建立 backend/tests/unit/test_memory_service.py，測試 add_memory() 方法正確呼叫 Mem0 SDK
- [x] T019 [P] [US1] 建立 backend/tests/unit/test_storage_service.py，測試 save_conversation() 和 save_message() 的 SQLite 操作
- [x] T020 [P] [US1] 建立 backend/tests/integration/test_chat_flow.py，測試完整對話流程（使用者訊息 → 記憶擷取 → LLM 回應 → 儲存）
- [x] T021 [P] [US1] 建立 backend/tests/api/test_chat_endpoints.py，測試 POST /api/v1/chat 端點的請求/回應格式

### Implementation for User Story 1

- [x] T022 [P] [US1] 建立 backend/src/models/conversation.py 定義 ConversationDB, MessageDB dataclass
- [x] T023 [P] [US1] 建立 backend/src/api/schemas/chat.py 定義 ChatRequest, ChatResponse, MessageResponse Pydantic 模型
- [x] T024 [US1] 實作 backend/src/storage/storage_service.py 的 create_conversation(), save_message(), get_conversation() 方法
- [x] T025 [US1] 實作 backend/src/services/memory_service.py 的 add_memory_from_message() 方法（呼叫 Mem0.add()）
- [x] T026 [US1] 實作 backend/src/services/conversation_service.py 協調對話流程（儲存訊息 → 擷取記憶 → 呼叫 LLM → 儲存回應）
- [x] T027 [US1] 實作 backend/src/api/routes/chat.py 的 POST /chat 端點，整合 conversation_service
- [x] T028 [US1] 在 conversation_service 中加入輸入驗證（UUID 格式、訊息長度 1-10000 字元）
- [x] T029 [US1] 在 chat.py 端點加入錯誤處理（400 驗證錯誤, 500 內部錯誤, 503 LLM 不可用）
- [x] T030 [US1] 在 conversation_service 關鍵操作加入日誌記錄（對話建立、記憶擷取、LLM 呼叫）
- [x] T031 [P] [US1] 建立 frontend/js/storage.js 實作 getUserId() 使用 crypto.randomUUID() 和 localStorage
- [x] T032 [P] [US1] 建立 frontend/js/api.js 實作 sendMessage(userId, conversationId, message) API 客戶端
- [x] T033 [US1] 建立 frontend/index.html 和 frontend/css/style.css 簡單聊天介面（訊息列表 + 輸入框）
- [x] T034 [US1] 建立 frontend/js/app.js 整合 storage.js 和 api.js，處理使用者輸入和顯示回應

**Checkpoint**: 此時使用者故事 1 應完全可用並可獨立測試

---

## Phase 4: User Story 2 - 記憶檢索與個人化回應 (Priority: P2) ✅ COMPLETED

**Goal**: 使用者詢問投資建議時，系統從 Mem0 檢索相關偏好並提供個人化回應

**Independent Test**: 在已建立記憶的基礎上，發送投資建議請求（如「幫我推薦股票」），檢查回應是否提及先前儲存的偏好

### Tests for User Story 2 (REQUIRED per Constitution) ⚠️ ✅

- [x] T035 [P] [US2] 建立 backend/tests/unit/test_memory_service_search.py，測試 search_memories() 方法正確呼叫 Mem0.search() - 11/11 tests passed
- [x] T036 [P] [US2] 建立 backend/tests/integration/test_memory_retrieval.py，測試記憶檢索與 LLM 上下文整合流程 - 10/10 tests passed
- [x] T037 [P] [US2] 在 backend/tests/api/test_chat_endpoints.py 新增測試案例，驗證 memories_used 欄位包含相關記憶 - 10/10 tests passed

### Implementation for User Story 2 ✅

- [x] T038 [US2] 實作 backend/src/services/memory_service.py 的 search_memories(user_id, query, top_k) 方法 - 支援 Mem0.search()、詳細的結果處理、fallback
- [x] T039 [US2] 修改 backend/src/services/llm_service.py 的 generate_response() 加入 memories 參數，構建包含記憶上下文的 prompt - 支援字典格式記憶、相關度徽章、安全設定
- [x] T040 [US2] 修改 backend/src/services/conversation_service.py 的對話流程，在呼叫 LLM 前先檢索最新 N 條記憶（N=5） - 完整步驟 5 實作，日誌記錄詳細
- [x] T041 [US2] 修改 backend/src/api/schemas/chat.py 的 ChatResponse，確保 memories_used 欄位包含使用的記憶內容清單 - MemoryUsedResponse 模型、ChatDataResponse 包含 memories_used
- [x] T042 [US2] 在 conversation_service 加入記憶檢索失敗時的降級處理（返回通用投資教育內容） - search_memories() 返回空列表、LLM 使用通用回應
- [x] T043 [US2] 修改 frontend/js/app.js 顯示 memories_used 資訊（選用，可在開發工具 console 顯示） - updateMemoriesDisplay() 支援字典和字串格式、相關度百分比、console 日誌

**Test Results Summary**:
- Unit tests (T035): 11 PASSED ✅
- Integration tests (T036): 10 PASSED ✅
- API tests for memories_used (T037): 10 PASSED ✅
- **Total Phase 4 Tests: 31 PASSED** ✅

**Checkpoint**: 此時使用者故事 1 和 2 都應獨立運作 ✅ VERIFIED

---

## Phase 5: User Story 3 - 記憶回顧與更新 (Priority: P3)

**Goal**: 使用者可查看已儲存的投資偏好，並可更新或修正這些資訊

**Independent Test**: 呼叫 GET /api/v1/memories API 查看記憶列表，使用 PUT /api/v1/memories/{id} 更新記憶內容，驗證變更成功

### Tests for User Story 3 (REQUIRED per Constitution) ⚠️

- [x] T044 [P] [US3] 建立 backend/tests/api/test_memory_endpoints.py，測試 GET /memories, GET /memories/{id}, PUT /memories/{id}, DELETE /memories/{id} 端點
- [x] T045 [P] [US3] 在 backend/tests/unit/test_memory_service.py 新增 update_memory() 和 delete_memory() 測試案例
- [x] T046 [P] [US3] 建立 backend/tests/integration/test_memory_crud.py，測試完整的記憶 CRUD 流程

### Implementation for User Story 3

- [x] T047 [P] [US3] 建立 backend/src/api/schemas/memory.py 定義 MemoryResponse, MemoryListResponse, MemoryUpdateRequest, BatchDeleteRequest Pydantic 模型
- [x] T048 [US3] 實作 backend/src/services/memory_service.py 的 get_memories(user_id, limit, category) 方法
- [x] T049 [US3] 實作 backend/src/services/memory_service.py 的 get_memory_by_id(memory_id) 方法
- [x] T050 [US3] 實作 backend/src/services/memory_service.py 的 update_memory(memory_id, content, category) 方法
- [x] T051 [US3] 實作 backend/src/services/memory_service.py 的 delete_memory(memory_id) 和 batch_delete_memories(user_id, category) 方法
- [x] T052 [US3] 建立 backend/src/api/routes/memory.py 實作 GET /memories 端點
- [x] T053 [P] [US3] 在 backend/src/api/routes/memory.py 實作 GET /memories/{memory_id} 端點
- [x] T054 [P] [US3] 在 backend/src/api/routes/memory.py 實作 PUT /memories/{memory_id} 端點
- [x] T055 [P] [US3] 在 backend/src/api/routes/memory.py 實作 DELETE /memories/{memory_id} 端點
- [x] T056 [P] [US3] 在 backend/src/api/routes/memory.py 實作 POST /memories/batch-delete 端點
- [x] T057 [P] [US3] 在 backend/src/api/routes/memory.py 實作 POST /memories/search 端點（語義搜索）
- [x] T058 [US3] 在 memory.py 所有端點加入錯誤處理（404 記憶不存在, 400 驗證錯誤）
- [x] T059 [US3] 在 backend/src/main.py 註冊 memory.py 路由
- [x] T060 [P] [US3] 建立 frontend/js/memory.js 實作記憶管理 API 客戶端（listMemories, deleteMemory, updateMemory）
- [x] T061 [US3] 修改 frontend/index.html 新增「查看我的偏好」按鈕和記憶顯示區域
- [x] T062 [US3] 在 frontend/js/app.js 整合 memory.js，實作顯示記憶列表和刪除功能

**Checkpoint**: 所有使用者故事應獨立可用

---

## Phase 6: 健康檢查與監控 (支援所有故事)

**Goal**: 提供系統健康檢查端點，用於監控和除錯

- [ ] T063 [P] 建立 backend/src/api/routes/health.py 實作 GET /health 基本健康檢查端點
- [ ] T064 [P] 在 backend/src/api/routes/health.py 實作 GET /health/detailed 詳細依賴檢查（SQLite, Chroma, Gemini API, Mem0）
- [ ] T065 [P] 在 backend/src/api/routes/health.py 實作 GET /metrics 系統效能指標端點
- [ ] T066 在 backend/src/main.py 註冊 health.py 路由
- [ ] T067 [P] 建立 backend/tests/api/test_health_endpoints.py 測試健康檢查端點

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: 憲法合規性與影響多個使用者故事的改進

- [ ] T068 [P] 實作 backend/src/storage/database.py 的 cleanup_expired_conversations(ttl_days=30) 方法清理過期對話
- [ ] T069 [P] 在 backend/src/services/memory_service.py 實作記憶數量上限檢查（每使用者最多 1000 條）
- [ ] T070 實作 API 速率限制中介層（chat 端點 10 req/min, 其他端點 50 req/min）
- [ ] T071 [P] 在所有 API 回應加入 X-Request-Id header 用於追蹤
- [ ] T072 效能測試：驗證 LLM 回應時間 P95 < 2 秒（使用 pytest-benchmark）
- [ ] T073 [P] 效能測試：驗證記憶檢索時間 P95 < 500 毫秒
- [ ] T074 [P] 並發測試：驗證系統支援 50 並發對話會話
- [ ] T075 測試覆蓋率檢查：執行 pytest --cov 驗證 ≥ 90% 覆蓋率
- [ ] T076 [P] 程式碼品質審查：執行 ruff check . 確保無警告
- [ ] T077 [P] 文件完整性驗證：確認所有服務和模型有 docstrings 和型別註解
- [ ] T078 UX 一致性驗證：確認所有錯誤訊息為繁體中文且使用者友善
- [ ] T079 [P] 繁體中文本地化檢查：驗證所有使用者面向內容（前端、API 回應、錯誤訊息）使用 zh-TW
- [ ] T080 [P] 文件語言合規檢查：確認所有 specs/ 和 README.md 使用繁體中文
- [ ] T081 安全審查：驗證無敏感資訊洩漏、輸入驗證完整
- [ ] T082 [P] 建立 backend/http/api-test.http VS Code REST Client 測試檔案，涵蓋所有 API 端點
- [ ] T083 執行 specs/001-mem0-investment-advisor/quickstart.md 中的 6 個測試場景驗證

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 無依賴 - 可立即開始
- **Foundational (Phase 2)**: 依賴 Setup 完成 - 阻塞所有使用者故事
- **User Stories (Phase 3-5)**: 全部依賴 Foundational 階段完成
  - 使用者故事可平行進行（如有人力）
  - 或依優先順序循序進行（P1 → P2 → P3）
- **Health Check (Phase 6)**: 可在任何使用者故事完成後開始
- **Polish (Phase 7)**: 依賴所有期望的使用者故事完成

### User Story Dependencies

- **User Story 1 (P1)**: 可在 Foundational (Phase 2) 後開始 - 無其他故事依賴
- **User Story 2 (P2)**: 可在 Foundational (Phase 2) 後開始 - 輕度依賴 US1（需要記憶已存在），但應可獨立測試
- **User Story 3 (P3)**: 可在 Foundational (Phase 2) 後開始 - 輕度依賴 US1（需要記憶 API），但應可獨立測試

### Within Each User Story

- 測試必須先寫並在實作前 FAIL
- Models before services
- Services before endpoints
- 核心實作 before 整合
- 故事完成 before 移至下一優先級

### Parallel Opportunities

- 所有標記 [P] 的 Setup 任務可平行執行
- 所有標記 [P] 的 Foundational 任務可平行執行（在 Phase 2 內）
- Foundational 階段完成後，所有使用者故事可平行開始（如團隊容量允許）
- 故事內所有標記 [P] 的測試可平行執行
- 故事內標記 [P] 的 models 可平行執行
- 不同使用者故事可由不同團隊成員平行處理

---

## Parallel Example: User Story 1

```bash
# 同時啟動使用者故事 1 的所有測試：
Task: "建立 backend/tests/unit/test_memory_service.py"
Task: "建立 backend/tests/unit/test_storage_service.py"
Task: "建立 backend/tests/integration/test_chat_flow.py"
Task: "建立 backend/tests/api/test_chat_endpoints.py"

# 同時啟動使用者故事 1 的所有 models：
Task: "建立 backend/src/models/conversation.py"
Task: "建立 backend/src/api/schemas/chat.py"
```

---

## Implementation Strategy

### MVP First (僅使用者故事 1)

1. 完成 Phase 1: Setup
2. 完成 Phase 2: Foundational（關鍵 - 阻塞所有故事）
3. 完成 Phase 3: User Story 1
4. **停止並驗證**: 獨立測試使用者故事 1
5. 如果就緒則部署/展示

### Incremental Delivery

1. 完成 Setup + Foundational → 基礎就緒
2. 新增使用者故事 1 → 獨立測試 → 部署/展示（MVP！）
3. 新增使用者故事 2 → 獨立測試 → 部署/展示
4. 新增使用者故事 3 → 獨立測試 → 部署/展示
5. 每個故事都在不破壞先前故事的情況下增加價值

### Parallel Team Strategy

多位開發者：

1. 團隊一起完成 Setup + Foundational
2. Foundational 完成後：
   - 開發者 A: 使用者故事 1
   - 開發者 B: 使用者故事 2
   - 開發者 C: 使用者故事 3
3. 故事獨立完成並整合

---

## Task Summary

- **Total Tasks**: 83
- **Setup Phase**: 6 tasks
- **Foundational Phase**: 11 tasks (BLOCKS all stories)
- **User Story 1 (P1 - MVP)**: 17 tasks (4 tests + 13 implementation)
- **User Story 2 (P2)**: 9 tasks (3 tests + 6 implementation)
- **User Story 3 (P3)**: 19 tasks (3 tests + 16 implementation)
- **Health Check Phase**: 5 tasks
- **Polish Phase**: 16 tasks

**Parallel Opportunities Identified**: 47 tasks marked [P] can run in parallel within their respective phases

**Suggested MVP Scope**: Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (User Story 1) = 34 tasks

**Independent Test Criteria**:
- **US1**: 發送投資偏好訊息 → 檢查 Mem0 儲存成功
- **US2**: 詢問投資建議 → 檢查回應包含先前偏好
- **US3**: 查看記憶列表 → 更新記憶 → 驗證變更成功

---

## Notes

- [P] tasks = 不同檔案，無依賴
- [Story] 標籤將任務映射到特定使用者故事以便追蹤
- 每個使用者故事應可獨立完成和測試
- 在實作前驗證測試會 FAIL
- 每個任務或邏輯群組後提交
- 在任何檢查點停止以獨立驗證故事
- 避免：模糊任務、相同檔案衝突、破壞獨立性的跨故事依賴
