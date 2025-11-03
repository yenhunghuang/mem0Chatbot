"""
健康檢查 API 路由

提供系統健康狀態檢查和詳細依賴檢查端點
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime
import time
import sqlite3
import logging

from src.config import settings
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService
from src.services.memory_service import MemoryService
from src.storage.database import DatabaseManager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthStatus:
    """健康狀態定義"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@router.get("/")
async def basic_health_check():
    """基本健康檢查端點
    
    Returns:
        dict: 基本狀態資訊
    """
    return {
        "status": HealthStatus.HEALTHY,
        "timestamp": datetime.utcnow().isoformat(),
        "service": "mem0-investment-advisor"
    }


@router.get("/detailed")
async def detailed_health_check():
    """詳細依賴檢查端點
    
    檢查所有關鍵依賴的可用性：
    - SQLite 數據庫
    - Chroma 向量數據庫
    - Google Gemini API
    - Google Embeddings API
    
    Returns:
        dict: 詳細依賴狀態
    """
    dependencies = {}
    overall_status = HealthStatus.HEALTHY
    
    # 檢查 SQLite
    sqlite_status = _check_sqlite()
    dependencies["sqlite"] = sqlite_status
    if sqlite_status["status"] != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED
    
    # 檢查 Chroma (記憶服務中初始化)
    chroma_status = _check_chroma()
    dependencies["chroma"] = chroma_status
    if chroma_status["status"] != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED
    
    # 檢查 Google Gemini API
    gemini_status = await _check_gemini_api()
    dependencies["gemini_api"] = gemini_status
    if gemini_status["status"] != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED
    
    # 檢查 Google Embeddings API
    embeddings_status = await _check_embeddings_api()
    dependencies["embeddings_api"] = embeddings_status
    if embeddings_status["status"] != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED
    
    # 檢查 Mem0 客戶端
    mem0_status = _check_mem0()
    dependencies["mem0"] = mem0_status
    if mem0_status["status"] != HealthStatus.HEALTHY:
        overall_status = HealthStatus.DEGRADED
    
    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "dependencies": dependencies
    }


@router.get("/metrics")
async def system_metrics():
    """系統效能指標端點
    
    Returns:
        dict: 系統指標包括響應時間、記憶統計等
    """
    metrics = {
        "timestamp": datetime.utcnow().isoformat(),
        "memory_stats": {},
        "database_stats": {}
    }
    
    # 獲取記憶統計
    try:
        memory_stats = _get_memory_stats()
        metrics["memory_stats"] = memory_stats
    except Exception as e:
        logger.warning(f"無法獲取記憶統計: {e}")
        metrics["memory_stats"]["error"] = str(e)
    
    # 獲取數據庫統計
    try:
        db_stats = _get_database_stats()
        metrics["database_stats"] = db_stats
    except Exception as e:
        logger.warning(f"無法獲取數據庫統計: {e}")
        metrics["database_stats"]["error"] = str(e)
    
    return metrics


def _check_sqlite() -> dict:
    """檢查 SQLite 連接
    
    Returns:
        dict: SQLite 狀態
    """
    try:
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        
        # 執行簡單查詢測試
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        
        return {
            "status": HealthStatus.HEALTHY,
            "message": "SQLite 連接正常",
            "database_path": settings.DATABASE_URL
        }
    except Exception as e:
        logger.error(f"SQLite 檢查失敗: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"SQLite 連接失敗: {str(e)}",
            "error": str(e)
        }


def _check_chroma() -> dict:
    """檢查 Chroma 向量數據庫
    
    Returns:
        dict: Chroma 狀態
    """
    try:
        # Chroma 通過 MemoryService 初始化
        # 嘗試訪問客戶端以驗證連接
        if hasattr(MemoryService, '_client'):
            client = MemoryService._client
            if client is not None:
                # 嘗試獲取集合計數
                collections = client.list_collections()
                return {
                    "status": HealthStatus.HEALTHY,
                    "message": "Chroma 連接正常",
                    "collections": len(collections)
                }
        
        return {
            "status": HealthStatus.HEALTHY,
            "message": "Chroma 未初始化但可用"
        }
    except Exception as e:
        logger.error(f"Chroma 檢查失敗: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Chroma 檢查失敗: {str(e)}",
            "error": str(e)
        }


async def _check_gemini_api() -> dict:
    """檢查 Google Gemini API
    
    Returns:
        dict: Gemini API 狀態
    """
    try:
        # 嘗試執行簡單的生成請求
        response = LLMService.generate_response(
            "您好",
            memories=[]
        )
        
        if response and len(response) > 0:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Gemini API 連接正常",
                "model": "gemini-2.5-flash"
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Gemini API 回應為空"
            }
    except Exception as e:
        logger.error(f"Gemini API 檢查失敗: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Gemini API 檢查失敗: {str(e)}",
            "error": str(e)
        }


async def _check_embeddings_api() -> dict:
    """檢查 Google Embeddings API
    
    Returns:
        dict: Embeddings API 狀態
    """
    try:
        # 嘗試生成簡單文本的嵌入
        embeddings = EmbeddingService.embed_text("測試")
        
        if embeddings and len(embeddings) > 0:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Embeddings API 連接正常",
                "model": "gemini-embedding-001",
                "embedding_dim": len(embeddings)
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Embeddings API 回應為空"
            }
    except Exception as e:
        logger.error(f"Embeddings API 檢查失敗: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Embeddings API 檢查失敗: {str(e)}",
            "error": str(e)
        }


def _check_mem0() -> dict:
    """檢查 Mem0 客戶端
    
    Returns:
        dict: Mem0 狀態
    """
    try:
        # Mem0 應已通過主模組初始化
        if MemoryService._client is not None:
            return {
                "status": HealthStatus.HEALTHY,
                "message": "Mem0 客戶端已初始化",
                "backend": "chroma"
            }
        else:
            return {
                "status": HealthStatus.UNHEALTHY,
                "message": "Mem0 客戶端未初始化"
            }
    except Exception as e:
        logger.error(f"Mem0 檢查失敗: {e}")
        return {
            "status": HealthStatus.UNHEALTHY,
            "message": f"Mem0 檢查失敗: {str(e)}",
            "error": str(e)
        }


def _get_memory_stats() -> dict:
    """獲取記憶統計資訊
    
    Returns:
        dict: 記憶統計
    """
    try:
        # 通過 Mem0 獲取統計
        stats = {
            "total_collections": 0,
            "message": "記憶統計獲取成功"
        }
        
        if hasattr(MemoryService, '_client') and MemoryService._client is not None:
            collections = MemoryService._client.list_collections()
            stats["total_collections"] = len(collections)
        
        return stats
    except Exception as e:
        logger.warning(f"獲取記憶統計失敗: {e}")
        return {"error": str(e)}


def _get_database_stats() -> dict:
    """獲取數據庫統計資訊
    
    Returns:
        dict: 數據庫統計
    """
    try:
        db_manager = DatabaseManager()
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        
        # 查詢對話和訊息計數
        cursor.execute("SELECT COUNT(*) FROM conversations")
        conv_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM messages")
        msg_count = cursor.fetchone()[0]
        
        cursor.close()
        
        return {
            "total_conversations": conv_count,
            "total_messages": msg_count,
            "message": "數據庫統計獲取成功"
        }
    except Exception as e:
        logger.warning(f"獲取數據庫統計失敗: {e}")
        return {"error": str(e)}
