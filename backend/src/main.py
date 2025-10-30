"""
FastAPI 主應用程式

啟動 FastAPI 應用程式，設置中介軟體、異常處理器、以及路由。
"""

from contextlib import asynccontextmanager
from typing import Callable
import uuid

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from .config import settings
from .utils.logger import get_logger
from .utils.exceptions import (
    ApplicationError,
    ValidationError,
    MemoryError,
    LLMError,
    DatabaseError,
    NotFoundError,
    RateLimitError,
)
from .storage.database import DatabaseManager
from .services.embedding_service import EmbeddingService
from .services.llm_service import LLMService
from .services.memory_service import MemoryService

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    應用程式生命週期管理

    處理應用程式啟動和關閉事件。
    """
    # 啟動事件
    logger.info("應用程式啟動中...")
    try:
        # 初始化資料庫
        DatabaseManager.initialize(settings.database_url)
        logger.info("資料庫已初始化")

        # 初始化服務
        EmbeddingService.initialize()
        logger.info("嵌入服務已初始化")

        LLMService.initialize()
        logger.info("LLM 服務已初始化")

        MemoryService.initialize()
        logger.info("記憶服務已初始化")

    except Exception as e:
        logger.error(f"應用程式啟動失敗: {str(e)}")
        raise

    yield

    # 關閉事件
    logger.info("應用程式關閉中...")
    try:
        DatabaseManager.close()
        logger.info("資料庫連線已關閉")
    except Exception as e:
        logger.error(f"關閉資料庫失敗: {str(e)}")


# 建立 FastAPI 應用程式
app = FastAPI(
    title="投資顧問助理 API",
    description="基於 Mem0 的個人化投資顧問聊天機器人",
    version="1.0.0",
    lifespan=lifespan,
)


# 設置 CORS 中介軟體
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 請求 ID 中介軟體
@app.middleware("http")
async def add_request_id_middleware(request: Request, call_next: Callable):
    """
    新增請求 ID

    為每個請求分配唯一 ID，便於追蹤。
    """
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# 日誌中介軟體
@app.middleware("http")
async def log_requests_middleware(request: Request, call_next: Callable):
    """
    記錄 HTTP 請求和回應

    記錄所有 API 請求和響應時間。
    """
    logger.info(
        f"[{request.state.request_id}] {request.method} {request.url.path}",
    )
    response = await call_next(request)
    logger.info(
        f"[{request.state.request_id}] {request.method} {request.url.path} -> {response.status_code}",
    )
    return response


# 例外處理器


@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    """處理驗證錯誤"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": "VALIDATION_ERROR",
            "message": str(exc),
            "details": exc.details,
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(NotFoundError)
async def not_found_error_handler(request: Request, exc: NotFoundError):
    """處理未找到錯誤"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "code": "NOT_FOUND",
            "message": str(exc),
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(MemoryError)
async def memory_error_handler(request: Request, exc: MemoryError):
    """處理記憶相關錯誤"""
    logger.error(f"記憶錯誤: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "MEMORY_ERROR",
            "message": "無法處理記憶操作",
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(LLMError)
async def llm_error_handler(request: Request, exc: LLMError):
    """處理 LLM 相關錯誤"""
    logger.error(f"LLM 錯誤: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "code": "LLM_ERROR",
            "message": "LLM 服務暫時不可用",
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(DatabaseError)
async def database_error_handler(request: Request, exc: DatabaseError):
    """處理資料庫錯誤"""
    logger.error(f"資料庫錯誤: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "DATABASE_ERROR",
            "message": "資料庫操作失敗",
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(RateLimitError)
async def rate_limit_error_handler(request: Request, exc: RateLimitError):
    """處理速率限制錯誤"""
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "code": "RATE_LIMITED",
            "message": "請求過於頻繁，請稍後再試",
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(ApplicationError)
async def application_error_handler(request: Request, exc: ApplicationError):
    """處理應用程式錯誤"""
    logger.error(f"應用程式錯誤: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "APPLICATION_ERROR",
            "message": "應用程式發生錯誤",
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
):
    """處理 FastAPI 驗證錯誤"""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": ".".join(str(x) for x in error["loc"][1:]),
                "message": error["msg"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "code": "VALIDATION_ERROR",
            "message": "請求驗證失敗",
            "details": {"errors": errors},
            "request_id": request.state.request_id,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """處理一般異常"""
    logger.error(f"未預期的錯誤: {str(exc)}", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": "INTERNAL_ERROR",
            "message": "伺服器內部錯誤",
            "request_id": request.state.request_id,
        },
    )


# 健康檢查路由
@app.get("/health", tags=["Health"])
async def health_check():
    """健康檢查端點"""
    return {
        "status": "healthy",
        "version": "1.0.0",
    }


# 註冊路由
from .api.routes import chat as chat_routes

app.include_router(chat_routes.router)


# 根路由
@app.get("/", tags=["Root"])
async def root():
    """根端點"""
    return {
        "name": "投資顧問助理 API",
        "version": "1.0.0",
        "docs": "/docs",
    }
