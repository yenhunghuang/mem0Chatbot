# 實作計劃：個人化投顧助理（Mem0 練習版）

**分支**: `001-mem0-investment-advisor` | **日期**: 2025-10-30 | **規格**: [spec.md](./spec.md)
**輸入**: 功能規格來自 `/specs/001-mem0-investment-advisor/spec.md`

**備註**: 此模板由 `/speckit.plan` 命令填寫。詳見 `.specify/templates/commands/plan.md` 執行流程。

## 摘要

本專案開發一個基於 Mem0 長期記憶系統的個人化投資助理聊天機器人（練習版）。核心目標是讓使用者透過自然語言對話建立個人化的投資偏好檔案，系統自動擷取並儲存至 Mem0 記憶層，在後續對話中檢索相關記憶並提供個人化建議。

技術方案採用 FastAPI + Python 3.12 作為後端框架，整合 Google Gemini 2.5 Flash 作為主要 LLM，使用 Google Embeddings 進行記憶向量化，Chroma 作為向量資料庫，SQLite 儲存短期記憶。整個系統無需登入流程，使用瀏覽器 localStorage 管理臨時使用者識別碼，專注於展示 LLM + 記憶系統的整合實踐。

## Technical Context

**Language/Version**: Python 3.12  
**Primary Dependencies**: FastAPI, Mem0, Google Generative AI SDK (Gemini 2.5 Flash), Google AI Python SDK (Embeddings), ChromaDB, SQLite3, Pydantic  
**Storage**: Chroma (向量資料庫, 本地), SQLite (短期記憶與中繼資料), localStorage (前端使用者識別)  
**Testing**: pytest, VS Code REST Client  
**Target Platform**: Linux/Windows 伺服器 (FastAPI 後端), 現代瀏覽器 (前端)  
**Project Type**: Web (後端 API + 前端 SPA)  
**Performance Goals**: 記憶檢索 < 2 秒, 記憶操作 < 500ms, 支援 50 並發對話  
**Constraints**: 無登入系統, 本地記憶儲存, 同步執行無背景任務, 無實時交易資料  
**Scale/Scope**: 單機部署, 練習用途, 重點在 LLM + 記憶系統整合實踐

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Code Quality Excellence Gates:**
- [x] Architecture follows documented patterns and design principles (FastAPI 標準架構, 分層設計)
- [x] Component structure supports maintainability and clear interfaces (models/services/api 分層)
- [x] Documentation strategy defined for all modules (docstrings + 型別註解)

**Testing Standards Gates:**
- [x] Test strategy includes unit, integration, and performance tests (pytest 框架)
- [x] 90%+ code coverage target established (核心記憶與 LLM 整合邏輯)
- [x] TDD approach planned for all critical functionality (記憶操作先寫測試)

**User Experience Consistency Gates:**
- [x] Conversation patterns and response formats standardized (繁體中文回應格式)
- [x] Error handling and messaging guidelines defined (友善錯誤訊息)
- [x] Response time requirements specified (2 秒標準, 5 秒複雜查詢)

**Performance Requirements Gates:**
- [x] Response time targets defined (2s standard, 5s complex queries)
- [x] Memory operation performance specified (500ms)
- [x] Concurrent user capacity planned (50 users minimum)

**Localization Standards Gates:**
- [x] All specifications and plans written in Traditional Chinese (zh-TW)
- [x] User-facing documentation in Traditional Chinese
- [x] Chatbot responses and UI text in Traditional Chinese
- [x] Code comments language strategy defined (English for technical, zh-TW for user-facing)

**憲法檢查結果**: ✅ **全部通過** - 無違規項目需要說明

## Project Structure

### Documentation (this feature)

```text
specs/001-mem0-investment-advisor/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # ✅ Phase 0 完成：技術研究與決策 (7 個研究領域)
├── data-model.md        # ✅ Phase 1 完成：資料模型設計 (5 個實體 + Pydantic 模型)
├── quickstart.md        # ✅ Phase 1 完成：整合測試場景 (6 個測試案例)
├── contracts/           # ✅ Phase 1 完成：API 合約 (3 個 OpenAPI 規格)
│   ├── README.md        #    合約總覽與設計原則
│   ├── chat.yaml        #    對話 API (3 個端點)
│   ├── memories.yaml    #    記憶管理 API (5 個端點)
│   └── health.yaml      #    健康檢查 API (3 個端點)
└── tasks.md             # ⏳ Phase 2 待執行：使用 /speckit.tasks 命令生成
```

### Source Code (repository root)

```text
backend/
├── src/
│   ├── main.py                    # FastAPI 應用入口
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # 環境變數與設定
│   ├── models/
│   │   ├── __init__.py
│   │   ├── conversation.py        # 對話會話模型
│   │   ├── memory.py              # 記憶片段模型
│   │   └── user_preference.py    # 使用者偏好模型
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm_service.py         # Gemini LLM 整合
│   │   ├── memory_service.py      # Mem0 記憶管理
│   │   ├── embedding_service.py   # Google Embeddings
│   │   ├── storage_service.py     # SQLite + Chroma 儲存
│   │   └── conversation_service.py # 對話邏輯協調
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py            # 對話端點
│   │   │   ├── memory.py          # 記憶管理端點
│   │   │   └── health.py          # 健康檢查
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── chat.py            # 對話請求/回應 schema
│   │       └── memory.py          # 記憶 schema
│   └── utils/
│       ├── __init__.py
│       ├── logger.py              # 日誌工具
│       └── exceptions.py          # 自訂例外
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # pytest 設定與 fixtures
│   ├── unit/
│   │   ├── test_llm_service.py
│   │   ├── test_memory_service.py
│   │   └── test_embedding_service.py
│   ├── integration/
│   │   ├── test_chat_flow.py     # 完整對話流程測試
│   │   └── test_memory_retrieval.py
│   └── api/
│       ├── test_chat_endpoints.py
│       └── test_memory_endpoints.py
├── requirements.txt               # Python 依賴
├── .env.example                   # 環境變數範例
└── README.md

frontend/
├── index.html                     # 單頁應用
├── css/
│   └── style.css
├── js/
│   ├── app.js                     # 主要應用邏輯
│   ├── api.js                     # API 客戶端
│   └── storage.js                 # localStorage UUID 管理
└── http/
    └── api-test.http              # VS Code REST Client 測試

data/                               # 本地資料目錄 (gitignored)
├── chroma/                         # Chroma 向量資料庫
└── chat.db                         # SQLite 資料庫
```

**Structure Decision**: 採用 Web 應用架構（選項 2），因為本專案包含 FastAPI 後端 API 與簡單的前端聊天介面。後端使用標準 FastAPI 三層架構（models/services/api），前端為簡單 SPA，測試涵蓋單元、整合與 API 層。

## Complexity Tracking

**無違規項目** - 所有憲法檢查項目均已通過，無需複雜度說明。
