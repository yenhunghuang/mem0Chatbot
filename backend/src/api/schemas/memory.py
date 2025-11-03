"""
記憶管理 API 的 Pydantic 模型

定義記憶相關的請求和回應格式。
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime


class MemoryResponse(BaseModel):
    """單一記憶回應"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "id": "mem-123",
            "content": "我偏好科技股投資",
            "category": "investment_type",
            "timestamp": "2025-10-30T12:00:00Z",
            "relevance_score": 0.95,
        }
    })

    id: str = Field(..., description="記憶 ID")
    content: str = Field(..., description="記憶內容")
    category: Optional[str] = Field(None, description="記憶類別（如 investment_type, risk_level）")
    timestamp: Optional[str] = Field(None, description="記憶建立時間 (ISO 8601 格式)")
    relevance_score: Optional[float] = Field(None, description="相關度評分 (0-1)")
    metadata: Optional[dict] = Field(None, description="額外中繼資料")


class MemoryListResponse(BaseModel):
    """記憶列表回應"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": [
                {
                    "id": "mem-1",
                    "content": "科技股投資",
                    "category": "investment_type",
                    "timestamp": "2025-10-30T12:00:00Z",
                },
                {
                    "id": "mem-2",
                    "content": "中等風險承受度",
                    "category": "risk_level",
                    "timestamp": "2025-10-30T13:00:00Z",
                },
            ],
            "total": 2,
            "count": 2,
        }
    })

    data: List[MemoryResponse] = Field(..., description="記憶列表")
    total: int = Field(..., description="記憶總數")
    count: int = Field(..., description="本次返回的記憶數量")


class MemoryCreateRequest(BaseModel):
    """記憶新增請求"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "content": "我偏好科技股投資",
            "metadata": {
                "category": "preference",
                "source": "seed"
            }
        }
    })

    user_id: str = Field(..., description="使用者 ID")
    content: str = Field(..., description="記憶內容", min_length=1, max_length=10000)
    metadata: Optional[dict] = Field(None, description="記憶中繼資料（可包含 category）")


class MemoryUpdateRequest(BaseModel):
    """記憶更新請求"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "content": "更新後的科技股投資偏好",
            "category": "investment_type",
        }
    })

    user_id: str = Field(..., description="使用者 ID")
    content: str = Field(..., description="記憶內容", min_length=1, max_length=10000)
    category: Optional[str] = Field(None, description="記憶類別")


class MemorySingleResponse(BaseModel):
    """單一記憶的 API 回應包裝"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "data": {
                "id": "mem-123",
                "content": "我偏好科技股投資",
                "category": "investment_type",
                "timestamp": "2025-10-30T12:00:00Z",
            },
            "timestamp": "2025-10-30T12:05:00Z",
        }
    })

    data: MemoryResponse = Field(..., description="記憶資料")
    timestamp: str = Field(..., description="回應時間戳")


class BatchDeleteRequest(BaseModel):
    """批量刪除記憶請求"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "category": "investment_type",
        }
    })

    user_id: str = Field(..., description="使用者 ID")
    category: Optional[str] = Field(None, description="要刪除的記憶類別")


class BatchDeleteResponse(BaseModel):
    """批量刪除記憶回應"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "deleted_count": 3,
            "timestamp": "2025-10-30T12:05:00Z",
        }
    })

    deleted_count: int = Field(..., description="刪除的記憶數量")
    timestamp: str = Field(..., description="操作時間戳")


class SemanticSearchRequest(BaseModel):
    """語義搜索記憶請求"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "user_id": "user-123",
            "query": "股票投資推薦",
            "top_k": 5,
        }
    })

    user_id: str = Field(..., description="使用者 ID")
    query: str = Field(..., description="搜索查詢", min_length=1, max_length=1000)
    top_k: int = Field(5, description="返回結果數量", ge=1, le=50)


class SemanticSearchResponse(BaseModel):
    """語義搜索結果回應"""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "results": [
                {
                    "id": "mem-1",
                    "content": "科技股投資",
                    "category": "investment_type",
                    "relevance_score": 0.95,
                },
            ],
            "query": "股票投資推薦",
            "timestamp": "2025-10-30T12:05:00Z",
        }
    })

    results: List[MemoryResponse] = Field(..., description="搜索結果")
    query: str = Field(..., description="搜索查詢詞")
    timestamp: str = Field(..., description="搜索時間戳")
