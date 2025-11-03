# Phase 5 記憶管理前端使用指南

## 📚 檔案結構

```
frontend/
├── index.html              # 新增記憶管理標籤
├── js/
│   ├── memory.js          # T060: 記憶 API 客戶端
│   ├── app.js            # T062: 記憶功能整合
│   ├── api.js            # 聊天 API 客戶端
│   └── storage.js        # 本地儲存管理
└── css/
    └── style.css         # T061: 新增記憶管理樣式
```

## 🚀 快速開始

### 1. 啟動應用

```bash
# 啟動後端 API (若未啟動)
cd backend
python -m uvicorn src.main:app --reload

# 在瀏覽器中開啟前端
# 檔案:// 協議或使用本地伺服器
http://localhost:8000/frontend/index.html
```

### 2. 訪問記憶管理

```
點擊頂部的「📝 我的記憶」標籤
↓
檢視所有已保存的投資偏好記憶
```

## ✨ 功能描述

### T060: memory.js API 客戶端

提供記憶 CRUD 操作的函數：

```javascript
// 取得記憶列表
const memories = await listMemories(userId, { limit: 100, category: 'investment_type' });

// 刪除記憶
await deleteMemory(memoryId);

// 更新記憶
const updated = await updateMemory(memoryId, { content: '新內容', category: '類別' });

// 批量刪除
const result = await batchDeleteMemories(userId, { category: 'investment_type' });

// 搜索記憶
const results = await searchMemories(userId, '查詢詞', { top_k: 10 });
```

### T061: index.html 使用者介面

**標籤頁導航**
- 💬 聊天：主要聊天介面
- 📝 我的記憶：記憶管理介面

**記憶管理功能**
- 🔍 搜索：實時搜索記憶內容
- 🔄 重新載入：重新從伺服器獲取記憶
- 🗑️ 清除所有：批量刪除所有記憶（需確認）

**記憶卡片操作**
- ✏️ 編輯：使用 Prompt 對話框編輯記憶
- 🗑️ 刪除：刪除單一記憶（需確認）

**顯示信息**
- 記憶 ID（縮寫）
- 時間戳（建立日期）
- 類別標籤
- 相關度評分（百分比）

### T062: app.js 功能整合

**核心函數**

```javascript
// 綁定記憶事件
bindMemoryEvents()

// 切換標籤頁
switchTab(tabName)

// 載入記憶列表
loadMemories()

// 顯示記憶列表
displayMemories(memories)

// 刪除記憶
deleteMemoryItem(memoryId)

// 編輯記憶
editMemory(memoryId, content)

// 批量刪除
handleDeleteAllMemories()

// 搜索記憶
handleMemorySearch(event)
```

**事件綁定**
- 標籤按鈕點擊
- 搜索框輸入（含防抖）
- 刷新按鈕點擊
- 清除全部按鈕點擊
- 編輯/刪除按鈕點擊

## 🎯 工作流程

### 使用者保存記憶

```
1. 使用者在聊天中分享投資偏好
   "我想投資科技股，風險承受度中等"

2. 系統 (LLM + Mem0) 自動提取記憶
   並保存到 Mem0 記憶庫

3. 使用者可在「我的記憶」標籤中查看
```

### 使用者管理記憶

```
1. 點擊「我的記憶」標籤
   ↓ 載入記憶列表

2. 搜索特定記憶
   ↓ 實時過濾結果

3. 編輯或刪除記憶
   ↓ 儲存更改到伺服器

4. 查看相關度和時間戳
   ↓ 了解記憶的重要性
```

## 🔧 技術詳情

### 搜索功能（防抖）

搜索框採用 300ms 防抖，避免過多 API 呼叫：

```javascript
memorySearchInput.addEventListener('input', debounce(handleMemorySearch, 300));
```

### 確認對話框

刪除操作使用瀏覽器原生 `confirm()` 對話框確認：

```javascript
if (!confirm('確定要刪除此記憶嗎？')) {
  return;
}
```

### 通知系統

成功操作顯示綠色通知（3 秒後自動消失）：

```javascript
showNotification('記憶已刪除');
```

### 錯誤處理

失敗操作顯示紅色錯誤提示：

```javascript
showError('無法載入記憶: ' + getErrorMessage(error));
```

## 🎨 樣式系統

### 顏色編碼

- 🔵 **主色** (藍色): 按鈕、標籤、邊框
- 🟢 **成功** (綠色): 通知訊息
- 🔴 **危險** (紅色): 刪除按鈕、錯誤提示
- ⚫ **文字**: 深灰色 (#111827)
- ⚪ **背景**: 白色

### 響應式設計

介面在以下裝置上自動調整：
- 🖥️ 桌面 (> 768px): 完整佈局
- 📱 平板/手機 (≤ 768px): 單欄佈局

## 🔌 API 端點對應

| 前端函數 | API 端點 | 方法 |
|---------|---------|------|
| `listMemories()` | `/memories` | GET |
| `deleteMemory()` | `/memories/{id}` | DELETE |
| `updateMemory()` | `/memories/{id}` | PUT |
| `batchDeleteMemories()` | `/memories/batch-delete` | POST |
| `searchMemories()` | `/memories/search` | POST |

## 📝 狀態管理

應用狀態保存在全局 `appState` 物件中：

```javascript
appState = {
  userId: "user-123",        // 使用者 ID
  conversationId: "conv-456", // 對話 ID
  isLoading: false,           // 是否正在載入
}
```

## ⚠️ 限制與已知問題

1. **編輯對話框**: 使用原生 `prompt()` (可改進為模態框)
2. **搜索**: 客戶端搜索，在大量記憶時可能較慢
3. **分頁**: 目前載入所有記憶，未實現分頁

## 🚧 未來改進

- [ ] 使用模態框代替 Prompt 對話框
- [ ] 實現記憶分頁
- [ ] 本地搜索緩存
- [ ] 記憶類別篩選
- [ ] 匯出記憶為 CSV
- [ ] 批量匯入記憶

## 🤝 與後端整合

前端完全依賴於後端 API：

**必需的 API 端點** (Phase 5 已實作):
- ✅ GET `/api/v1/memories`
- ✅ DELETE `/api/v1/memories/{id}`
- ✅ PUT `/api/v1/memories/{id}`
- ✅ POST `/api/v1/memories/batch-delete`
- ✅ POST `/api/v1/memories/search`

## 📞 故障排除

### 記憶不顯示

```
1. 檢查後端是否執行: http://localhost:8000/health
2. 檢查瀏覽器控制台是否有錯誤
3. 檢查使用者 ID 是否正確設置
```

### 編輯/刪除失敗

```
1. 檢查記憶 ID 是否正確
2. 檢查 API 回應狀態碼
3. 查看錯誤訊息詳情
```

### 搜索不工作

```
1. 檢查搜索查詢是否為空
2. 確認防抖延遲 (300ms)
3. 檢查記憶是否存在
```

---

**文檔版本**: 1.0  
**最後更新**: 2025-11-03  
**對應階段**: Phase 5 - US3 記憶回顧與更新
