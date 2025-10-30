# API 合約總覽

**版本**: v1.0  
**基礎路徑**: `/api/v1`  
**日期**: 2025-10-30

## 目的

定義投顧助理前後端 API 合約，確保介面一致性與可測試性。

## 合約文件清單

| 檔案名稱              | 說明                                    |
|-----------------------|-----------------------------------------|
| `chat.yaml`           | 對話相關端點（核心功能）                |
| `memories.yaml`       | 記憶管理端點（查詢/更新/刪除）          |
| `health.yaml`         | 健康檢查與系統狀態                      |

## OpenAPI 規範

所有合約遵循 OpenAPI 3.0.3 規範，包含：
- 完整的請求/回應模型定義
- 錯誤碼標準化
- 範例資料
- 驗證規則

## 通用設計原則

### 1. 錯誤處理
所有 API 使用統一錯誤格式：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "使用者訊息不可為空",
    "details": {
      "field": "message",
      "constraint": "min_length"
    }
  }
}
```

### 2. HTTP 狀態碼
- `200 OK`: 成功（查詢、更新）
- `201 Created`: 建立新資源
- `400 Bad Request`: 驗證錯誤
- `404 Not Found`: 資源不存在
- `429 Too Many Requests`: 超過速率限制
- `500 Internal Server Error`: 伺服器錯誤
- `503 Service Unavailable`: LLM API 不可用

### 3. 速率限制
- **一般端點**: 50 req/min per user_id
- **LLM 端點**: 10 req/min per user_id
- Header 回應：
  ```
  X-RateLimit-Limit: 10
  X-RateLimit-Remaining: 7
  X-RateLimit-Reset: 1672531200
  ```

### 4. 請求追蹤
每個回應包含 `X-Request-Id` header，用於除錯和日誌追蹤。

## 安全考量

- **無認證**: 規格要求無登入流程，使用 user_id 識別
- **輸入驗證**: 所有輸入必須經過 Pydantic 驗證
- **輸出過濾**: 避免洩漏內部錯誤細節

## 測試策略

每個端點提供：
1. **正常流程測試**: 使用 VS Code REST Client (.http 檔案)
2. **錯誤處理測試**: 驗證各種錯誤情境
3. **邊界測試**: 測試極限值（空字串、超長文字等）

## 版本控制

API 版本透過路徑控制 (`/api/v1/`)，重大變更時遞增版本號。

---

**相關文件**:
- [資料模型](../data-model.md)
- [快速開始](../quickstart.md)
