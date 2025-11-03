"""
聊天 API 結構定義

定義聊天相關的 Pydantic 模型。
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict
import uuid


class MemoryUsedResponse(BaseModel):
    """使用的記憶（US2 T041）"""

    id: str = Field(..., description="記憶 ID")
    content: str = Field(..., description="記憶內容")
    relevance_score: Optional[float] = Field(None, description="相關度分數 (0-1)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="記憶元資料")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "mem_001",
                "content": "使用者偏好投資科技股",
                "relevance_score": 0.85,
                "metadata": {
                    "category": "preference",
                    "created_at": "2025-11-03T12:00:00Z",
                },
            }
        }
    )


class ChatRequest(BaseModel):
    """聊天請求"""

    user_id: str = Field(..., description="使用者 UUID")
    conversation_id: Optional[str] = Field(
        None, description="對話 ID UUID（無則建立新對話）"
    )
    message: str = Field(
        ..., min_length=1, max_length=10000, description="使用者訊息"
    )

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """驗證 user_id 為有效 UUID"""
        try:
            uuid.UUID(v)
            return v
        except (ValueError, TypeError):
            raise ValueError("user_id 必須為有效的 UUID 格式")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        """驗證訊息內容"""
        if not v or not v.strip():
            raise ValueError("訊息不能為空")
        return v.strip()

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "conversation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "message": "我偏好投資科技股",
            }
        }
    )


class MessageResponse(BaseModel):
    """訊息回應"""

    id: int = Field(..., description="訊息 ID")
    conversation_id: str = Field(..., description="對話 ID UUID")
    role: str = Field(..., description="角色 (user/assistant)")
    content: str = Field(..., description="訊息內容")
    timestamp: str = Field(..., description="時間戳記 (ISO 8601)")
    token_count: int = Field(..., description="Token 數量")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": 1,
                "conversation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "role": "user",
                "content": "我偏好投資科技股",
                "timestamp": "2025-01-01T00:00:00",
                "token_count": 6,
            }
        }
    )


class ChatDataResponse(BaseModel):
    """聊天回應資料"""

    conversation_id: str = Field(..., description="對話 ID")
    user_message: MessageResponse = Field(..., description="使用者訊息")
    assistant_message: MessageResponse = Field(..., description="助理訊息")
    memories_used: List[MemoryUsedResponse] = Field(
        default_factory=list, description="使用的記憶"
    )


class ChatResponse(BaseModel):
    """聊天回應（US2 T041 - 包含 memories_used）"""

    code: str = Field(default="SUCCESS", description="結果代碼")
    message: Optional[str] = Field(None, description="訊息")
    data: Optional[ChatDataResponse] = Field(None, description="回應資料")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "SUCCESS",
                "message": "聊天回應已生成",
                "data": {
                    "conversation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                    "user_message": {
                        "id": 1,
                        "role": "user",
                        "content": "我偏好投資科技股",
                        "timestamp": "2025-01-01T00:00:00",
                    },
                    "assistant_message": {
                        "id": 2,
                        "role": "assistant",
                        "content": "根據您的偏好，科技股是一個不錯的選擇...",
                        "timestamp": "2025-01-01T00:00:05",
                    },
                    "memories_used": [
                        {
                            "id": "mem_001",
                            "content": "使用者偏好投資科技股",
                            "metadata": {
                                "relevance": 0.95,
                                "category": "preference",
                            },
                        }
                    ],
                },
            }
        }
    )


class ConversationResponse(BaseModel):
    """對話回應"""

    id: str = Field(..., description="對話 ID UUID")
    user_id: str = Field(..., description="使用者 ID")
    created_at: str = Field(..., description="建立時間")
    last_activity: str = Field(..., description="最後活動時間")
    status: str = Field(..., description="對話狀態")
    message_count: int = Field(..., description="訊息數量")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-01-01T00:00:00",
                "last_activity": "2025-01-01T00:05:00",
                "status": "active",
                "message_count": 5,
            }
        }
    )


class CreateConversationRequest(BaseModel):
    """建立對話請求"""

    user_id: str = Field(..., description="使用者 UUID")

    @field_validator("user_id")
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """驗證 user_id 為有效 UUID"""
        try:
            uuid.UUID(v)
            return v
        except (ValueError, TypeError):
            raise ValueError("user_id 必須為有效的 UUID 格式")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
            }
        }
    )


class CreateConversationResponse(BaseModel):
    """建立對話回應"""

    code: str = Field(default="SUCCESS", description="結果代碼")
    data: ConversationResponse = Field(..., description="新建立的對話")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "SUCCESS",
                "data": {
                    "id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                    "user_id": "550e8400-e29b-41d4-a716-446655440000",
                    "created_at": "2025-01-01T00:00:00",
                    "last_activity": "2025-01-01T00:00:00",
                    "status": "active",
                    "message_count": 0,
                },
            }
        }
    )


class MessageListResponse(BaseModel):
    """訊息列表回應"""

    code: str = Field(default="SUCCESS", description="結果代碼")
    data: List[MessageResponse] = Field(..., description="訊息列表")
    meta: dict = Field(..., description="中繼資料")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "code": "SUCCESS",
                "data": [
                    {
                        "id": 1,
                        "conversation_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
                        "role": "user",
                        "content": "訊息",
                        "timestamp": "2025-01-01T00:00:00",
                        "token_count": 1,
                    },
                ],
                "meta": {
                    "total": 1,
                    "count": 1,
                },
            }
        }
    )