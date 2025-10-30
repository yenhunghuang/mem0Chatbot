"""
聊天 API 路由

實作聊天端點。
"""

from typing import Optional

from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse

from ...config import settings
from ...utils.logger import get_logger
from ...utils.exceptions import (
    ValidationError,
    MemoryError,
    LLMError,
    DatabaseError,
    NotFoundError,
)
from ...services.conversation_service import ConversationService
from ..schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationResponse,
    CreateConversationRequest,
    CreateConversationResponse,
    MessageListResponse,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["Chat"],
)


@router.post(
    "/conversations",
    response_model=CreateConversationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    request: Request,
    payload: CreateConversationRequest,
):
    """
    建立新對話

    Args:
        request: FastAPI 請求物件
        payload: 建立對話請求

    Returns:
        CreateConversationResponse: 新建立的對話
    """
    try:
        logger.info(f"[{request.state.request_id}] 建立對話: user_id={payload.user_id}")

        conversation = ConversationService.get_or_create_conversation(
            payload.user_id,
            conversation_id=None,
        )

        return CreateConversationResponse(
            code="SUCCESS",
            data=ConversationResponse(
                id=conversation.id,
                user_id=conversation.user_id,
                created_at=conversation.created_at,
                last_activity=conversation.last_activity,
                status=conversation.status,
                message_count=conversation.message_count,
            ),
        )

    except ValidationError as e:
        logger.warning(f"[{request.state.request_id}] 驗證錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": e.details,
                "request_id": request.state.request_id,
            },
        )
    except Exception as e:
        logger.error(f"[{request.state.request_id}] 建立對話失敗: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "建立對話失敗",
                "request_id": request.state.request_id,
            },
        )


@router.post(
    "/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat(
    request: Request,
    payload: ChatRequest,
):
    """
    發送聊天訊息

    處理使用者訊息，自動儲存、記憶擷取、LLM 回應、儲存流程。

    Args:
        request: FastAPI 請求物件
        payload: 聊天請求

    Returns:
        ChatResponse: 聊天回應
    """
    try:
        logger.info(
            f"[{request.state.request_id}] 聊天請求: user_id={payload.user_id}, "
            f"conversation_id={payload.conversation_id}"
        )

        result = ConversationService.process_message(
            user_id=payload.user_id,
            conversation_id=payload.conversation_id,
            message=payload.message,
        )

        return ChatResponse(
            code="SUCCESS",
            message="聊天回應已生成",
            data=result,
        )

    except ValidationError as e:
        logger.warning(f"[{request.state.request_id}] 驗證錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "code": "VALIDATION_ERROR",
                "message": str(e),
                "details": e.details,
                "request_id": request.state.request_id,
            },
        )

    except LLMError as e:
        logger.error(f"[{request.state.request_id}] LLM 錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "code": "LLM_ERROR",
                "message": "LLM 服務暫時不可用",
                "request_id": request.state.request_id,
            },
        )

    except MemoryError as e:
        logger.error(f"[{request.state.request_id}] 記憶錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "MEMORY_ERROR",
                "message": "無法處理記憶操作",
                "request_id": request.state.request_id,
            },
        )

    except DatabaseError as e:
        logger.error(f"[{request.state.request_id}] 資料庫錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "DATABASE_ERROR",
                "message": "資料庫操作失敗",
                "request_id": request.state.request_id,
            },
        )

    except Exception as e:
        logger.error(
            f"[{request.state.request_id}] 未預期的錯誤: {str(e)}",
            exc_info=e,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "伺服器內部錯誤",
                "request_id": request.state.request_id,
            },
        )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=MessageListResponse,
    status_code=status.HTTP_200_OK,
)
async def get_conversation_messages(
    request: Request,
    conversation_id: int,
    limit: int = 50,
):
    """
    取得對話訊息

    Args:
        request: FastAPI 請求物件
        conversation_id: 對話 ID
        limit: 最大返回數量

    Returns:
        MessageListResponse: 訊息列表
    """
    try:
        logger.info(
            f"[{request.state.request_id}] 取得對話訊息: conversation_id={conversation_id}"
        )

        messages_data = ConversationService.get_conversation_history(
            conversation_id,
            limit=limit,
        )

        return MessageListResponse(
            code="SUCCESS",
            data=[
                {
                    "id": msg["id"],
                    "conversation_id": msg["conversation_id"],
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"],
                    "token_count": msg["token_count"],
                }
                for msg in messages_data
            ],
            meta={
                "total": len(messages_data),
                "count": len(messages_data),
            },
        )

    except NotFoundError as e:
        logger.warning(f"[{request.state.request_id}] 對話未找到: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "code": "NOT_FOUND",
                "message": "對話未找到",
                "request_id": request.state.request_id,
            },
        )

    except DatabaseError as e:
        logger.error(f"[{request.state.request_id}] 資料庫錯誤: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "DATABASE_ERROR",
                "message": "資料庫操作失敗",
                "request_id": request.state.request_id,
            },
        )

    except Exception as e:
        logger.error(
            f"[{request.state.request_id}] 未預期的錯誤: {str(e)}",
            exc_info=e,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": "INTERNAL_ERROR",
                "message": "伺服器內部錯誤",
                "request_id": request.state.request_id,
            },
        )
