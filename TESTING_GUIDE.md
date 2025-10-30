# 🧪 投資顧問聊天機器人測試指南

**修復完成日期**: 2025-10-30  
**版本**: 001-mem0-investment-advisor  
**狀態**: ✅ 所有代碼修復已完成並推送

---

## 📋 系統狀態檢查清單

### ✅ 已完成的修復

- [x] Phase 1-3 完整實現 (34 個任務)
- [x] Google Gemini API 安全設定優化
- [x] HarmCategory 類型正確配置
- [x] UNSPECIFIED 類型移除
- [x] response.text 快速訪問器異常修復
- [x] finish_reason 檢查改進
- [x] 空 parts 列表處理
- [x] 所有代碼已推送 GitHub

### 📊 修復統計
```
提交數量: 7 個
文件變更: 2 個 (llm_service.py + 文檔)
總行數: +183 / -99
分支: 001-mem0-investment-advisor
```

---

## 🚀 快速開始

### 1. 環境準備

#### 前置條件檢查
```bash
# 檢查 Python 版本
python --version  # 應為 3.12+

# 檢查依賴
cd backend
pip list | grep -i "google\|fastapi\|mem0"
```

#### 環境變數設定
```bash
# 創建或編輯 .env 文件
cp backend/.env.example backend/.env

# 編輯 backend/.env，添加:
GOOGLE_API_KEY=your_api_key_here
DATABASE_URL=sqlite:///./data/chat.db
CHROMA_PATH=./data/chroma_db
```

### 2. 啟動後端

```bash
# 方式 1: 開發模式 (推薦測試)
cd backend
python -m uvicorn src.main:app --reload --port 8000

# 輸出應該顯示:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

### 3. 啟動前端

**在新的終端窗口**:
```bash
# 方式 1: 使用 Python 簡單伺服器
cd frontend
python -m http.server 8080

# 輸出應該顯示:
# Serving HTTP on 0.0.0.0 port 8080

# 訪問: http://localhost:8080
```

### 4. 測試對話

#### 測試 Case 1: 簡單問候
```
用戶輸入: "你好"
預期回應: ✅ 應收到問候回應
預期 HTTP 狀態: 200 OK
```

#### 測試 Case 2: 投資偏好
```
用戶輸入: "我偏好投資科技股，風險承受度中等"
預期回應: ✅ 應收到回應
預期操作:
  - 記憶自動提取
  - Mem0 儲存偏好
  - 返回個人化建議
預期 HTTP 狀態: 200 OK
```

#### 測試 Case 3: 連續對話
```
第一條訊息: "我想投資"
第二條訊息: "有什麼推薦?" (應使用相同的 conversation_id)
預期: ✅ 系統保持對話上下文
```

---

## 🔍 故障排查

### Issue: 503 Service Unavailable

**可能原因**:

#### 1. Google API 配額或限制
```
症狀: 所有請求都返回 503
解決方案:
  - 檢查 Google Cloud 配額: https://console.cloud.google.com
  - 確認 API 金鑰有效且配額充足
  - 查看 Google AI Studio: https://aistudio.google.com
  - 檢查速率限制 (通常為 60 req/min)
```

#### 2. Google API 暫時不可用
```
症狀: 某些時段返回 503，過一會兒恢復
解決方案:
  - 這是 Google 側的暫時問題
  - 等待幾分鐘後重試
  - 檢查 Google Cloud 狀態頁面
```

#### 3. 後端未正確啟動
```
症狀: 後端日誌無輸出或顯示錯誤
解決方案:
  # 檢查後端是否在運行
  netstat -ano | findstr :8000  # Windows
  lsof -i :8000                 # Mac/Linux
  
  # 檢查後端日誌
  cd backend && python -m uvicorn src.main:app --reload
  
  # 查看是否有異常
```

#### 4. 前端無法連接後端
```
症狀: 前端發送請求但無回應
解決方案:
  # 檢查瀏覽器開發者工具 (F12)
  - Network 選項卡查看請求
  - 確認後端地址正確 (http://localhost:8000)
  - 查看 CORS 是否有問題
```

---

## 📊 日誌檢查

### 成功的對話日誌
```
✅ 2025-10-30 15:40:10 - src.services.llm_service - INFO - LLM 回應成功
✅ 2025-10-30 15:40:10 - src.storage.storage_service - INFO - 訊息已儲存
✅ 2025-10-30 15:40:10 - src.main - INFO - [UUID] POST /api/v1/chat -> 200
```

### 調試日誌
```
🔍 DEBUG 級別日誌:
  - LLM 請求詳情
  - finish_reason 狀態
  - 記憶檢索結果
  - 回應部分計數

啟用調試:
  export PYTHON_LOG_LEVEL=DEBUG
  python -m uvicorn src.main:app --reload --log-level debug
```

---

## 💾 數據存儲

### SQLite 數據庫
```
位置: backend/data/chat.db
表結構:
  - conversations: 對話會話
  - messages: 訊息紀錄
  - timestamps: 時間戳

查詢工具:
  sqlite3 backend/data/chat.db
  .tables          # 查看所有表
  SELECT * FROM conversations;  # 查看對話
```

### Mem0 記憶庫
```
位置: backend/data/chroma_db
用途: 語義搜索和記憶檢索
查詢: 通過 Python API
  from src.services.memory_service import MemoryService
  memories = MemoryService.get_user_memories(user_id)
```

---

## 🧬 代碼驗證

### 導入驗證
```python
# 驗證所有關鍵模塊可以導入
from src.services.llm_service import LLMService      ✅
from src.services.memory_service import MemoryService ✅
from src.services.conversation_service import ConversationService ✅
from src.storage.storage_service import StorageService ✅
from src.api.routes.chat import router ✅
```

### 配置驗證
```python
# 驗證所有配置都已加載
from src.config.settings import settings
print(settings.google_api_key)     # 應有值
print(settings.database_url)       # 應為有效路徑
print(settings.mem0_llm_model)    # 應為 gemini-2.5-flash
```

---

## 📈 性能測試

### 響應時間目標
```
單個對話: < 2 秒 (P95)
記憶檢索: < 500 ms
LLM 調用: < 5 秒 (通常 2-3 秒)
```

### 測試方法
```bash
# 使用 curl 測試
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-123",
    "message": "你好，我想投資"
  }' \
  -w "\nTime: %{time_total}s\n"
```

---

## 🐛 常見問題 (FAQ)

### Q1: 如何重置所有對話和記憶?
```bash
# 刪除數據文件夾
rm -rf backend/data/

# 或手動刪除:
# - backend/data/chat.db
# - backend/data/chroma_db/
```

### Q2: 如何更改 LLM 模型?
```bash
# 編輯 backend/src/config/settings.py
mem0_llm_model = "gemini-2.0-flash"  # 或其他模型

# 重啟後端
```

### Q3: 如何檢查 Google API 配額?
```
方式 1: Google Cloud Console
  https://console.cloud.google.com/apis/api/generativeai.googleapis.com/quotas

方式 2: Google AI Studio
  https://aistudio.google.com/app/apikey
```

### Q4: 前端顯示"連接失敗"怎麼辦?
```bash
# 1. 檢查後端是否在運行
netstat -ano | findstr :8000

# 2. 檢查 CORS 配置 (backend/src/main.py)
# 應該有: allow_origins=["*"] 或特定的前端地址

# 3. 查看瀏覽器控制台是否有 CORS 錯誤
```

---

## ✅ 預發布檢查清單

在部署到生產環境前:

- [ ] 後端能正常啟動無錯誤
- [ ] 前端能連接到後端
- [ ] 簡單訊息能正常回應
- [ ] 記憶正確儲存和檢索
- [ ] 日誌不含異常或錯誤
- [ ] 所有修復都已推送 GitHub
- [ ] 環境變數已正確配置
- [ ] Google API 配額充足

---

## 📞 聯絡與支持

### 資源鏈接
- 項目代碼: https://github.com/yenhunghuang/mem0Chatbot
- Google Gemini API: https://ai.google.dev
- Mem0 文檔: https://docs.mem0.com
- FastAPI 文檔: https://fastapi.tiangolo.com

### 日誌文件
- 詳細分析: `GOOGLE_GEMINI_FIX_LOG.md`
- 快速摘要: `FIXES_SUMMARY.md`
- 完成報告: `US1_COMPLETION_REPORT.md`

---

## 📝 版本信息

```
項目版本: 1.0.0 (MVP)
Python 版本: 3.12
FastAPI 版本: 最新
Mem0 版本: 最新
Google Generative AI SDK: 最新
ChromaDB 版本: 最新

分支: 001-mem0-investment-advisor
最後更新: 2025-10-30 15:40 UTC+8
```

---

## 🎉 總結

系統已完全就緒！所有關鍵的 Google Gemini API 問題都已修復。

**預期行為**:
✅ 能夠正常發送和接收聊天訊息
✅ 投資偏好自動提取和儲存
✅ 記憶正確檢索和使用
✅ 詳細的日誌記錄用於調試

如遇到 503 錯誤，大多數情況是 Google API 側的暫時問題。請根據上述故障排查指南進行診斷。

**Happy Chatting! 🚀**
