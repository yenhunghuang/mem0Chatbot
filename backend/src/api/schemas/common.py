"""
API 公共結構定義

定義 API 通用的回應格式。
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """錯誤回應結構"""

    code: str = Field(..., description="錯誤代碼")
    message: str = Field(..., description="錯誤訊息")
    details: Optional[dict] = Field(None, description="錯誤詳細資訊")
    request_id: Optional[str] = Field(None, description="請求 ID")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "輸入驗證失敗",
                "details": {"field": "email", "reason": "無效的電郵格式"},
                "request_id": "req_12345",
            }
        }


class SuccessResponse(BaseModel):
    """成功回應結構"""

    code: str = Field(default="SUCCESS", description="結果代碼")
    data: Any = Field(..., description="回應資料")
    message: Optional[str] = Field(None, description="訊息")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "SUCCESS",
                "data": {},
                "message": "操作成功",
            }
        }


class PaginationMeta(BaseModel):
    """分頁元資料"""

    page: int = Field(..., ge=1, description="頁碼")
    page_size: int = Field(..., ge=1, le=100, description="每頁項數")
    total: int = Field(..., ge=0, description="總項數")
    total_pages: int = Field(..., ge=0, description="總頁數")

    class Config:
        json_schema_extra = {
            "example": {
                "page": 1,
                "page_size": 20,
                "total": 100,
                "total_pages": 5,
            }
        }


class PaginatedResponse(BaseModel):
    """分頁回應結構"""

    code: str = Field(default="SUCCESS", description="結果代碼")
    data: list = Field(..., description="資料列表")
    meta: PaginationMeta = Field(..., description="分頁中繼資料")
    message: Optional[str] = Field(None, description="訊息")

    class Config:
        json_schema_extra = {
            "example": {
                "code": "SUCCESS",
                "data": [],
                "meta": {
                    "page": 1,
                    "page_size": 20,
                    "total": 100,
                    "total_pages": 5,
                },
                "message": "查詢成功",
            }
        }
