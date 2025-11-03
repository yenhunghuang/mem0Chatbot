"""
記憶管理 API 路由

實作所有記憶管理相關的 HTTP 端點。
"""

from fastapi import APIRouter, HTTPException, Query, Path, Body
from datetime import datetime
from typing import Optional

from ..schemas.memory import (
    MemoryResponse,
    MemoryListResponse,
    MemoryUpdateRequest,
    MemorySingleResponse,
    BatchDeleteRequest,
    BatchDeleteResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from ...services.memory_service import MemoryService
from ...utils.logger import get_logger
from ...utils.exceptions import MemoryError

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/memories", tags=["memories"])


@router.get("", response_model=MemoryListResponse)
async def get_memories(
    user_id: str = Query(..., description="使用者 ID"),
    limit: int = Query(100, ge=1, le=1000, description="返回結果數量"),
    category: Optional[str] = Query(None, description="記憶類別過濾"),
) -> MemoryListResponse:
    """
    取得使用者的記憶列表

    **功能**: 取得特定使用者的所有記憶，支援分頁和類別過濾
    
    **驗收標準**: 成功回傳記憶列表，包含記憶總數

    Args:
        user_id: 使用者 ID
        limit: 返回的記憶數量（1-1000）
        category: 可選的記憶類別過濾

    Returns:
        MemoryListResponse: 包含記憶列表和總數的回應

    Raises:
        HTTPException: 400 驗證錯誤, 500 伺服器錯誤
    """
    try:
        if not user_id or not user_id.strip():
            raise HTTPException(status_code=422, detail="使用者 ID 不能為空")

        logger.info(f"取得記憶列表: user_id={user_id}, limit={limit}, category={category}")
        
        memories = MemoryService.get_memories(user_id, limit, category)
        
        # 轉換為 response 格式
        memory_responses = []
        for mem in memories:
            memory_responses.append(MemoryResponse(
                id=mem.get("id", ""),
                content=mem.get("content", ""),
                category=mem.get("metadata", {}).get("category"),
                timestamp=mem.get("timestamp"),
                relevance_score=mem.get("metadata", {}).get("relevance"),
            ))
        
        return MemoryListResponse(
            data=memory_responses,
            total=len(memory_responses),
            count=len(memory_responses),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得記憶列表失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法取得記憶列表: {str(e)}")


@router.get("/{memory_id}", response_model=MemorySingleResponse)
async def get_memory(
    memory_id: str = Path(..., description="記憶 ID"),
) -> MemorySingleResponse:
    """
    取得單一記憶

    **功能**: 根據記憶 ID 取得特定記憶

    Args:
        memory_id: 記憶 ID

    Returns:
        MemorySingleResponse: 包含記憶資料的回應

    Raises:
        HTTPException: 404 記憶不存在, 500 伺服器錯誤
    """
    try:
        logger.info(f"取得記憶: memory_id={memory_id}")
        
        memory = MemoryService.get_memory_by_id(memory_id)
        
        if not memory:
            raise HTTPException(status_code=404, detail=f"記憶不存在: {memory_id}")
        
        return MemorySingleResponse(
            data=MemoryResponse(
                id=memory.get("id", ""),
                content=memory.get("content", ""),
                category=memory.get("metadata", {}).get("category"),
                timestamp=memory.get("timestamp"),
            ),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取得記憶失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法取得記憶: {str(e)}")


@router.put("/{memory_id}", response_model=MemorySingleResponse)
async def update_memory(
    memory_id: str = Path(..., description="記憶 ID"),
    request: MemoryUpdateRequest = Body(...),
) -> MemorySingleResponse:
    """
    更新記憶

    **功能**: 更新特定記憶的內容和類別

    Args:
        memory_id: 記憶 ID
        request: 更新請求（包含 content 和 category）

    Returns:
        MemorySingleResponse: 更新後的記憶

    Raises:
        HTTPException: 404 記憶不存在, 400 驗證錯誤, 500 伺服器錯誤
    """
    try:
        if not request.content or not request.content.strip():
            raise HTTPException(status_code=422, detail="記憶內容不能為空")

        logger.info(f"更新記憶: memory_id={memory_id}")
        
        updated_memory = MemoryService.update_memory(
            memory_id=memory_id,
            content=request.content,
            category=request.category,
        )
        
        return MemorySingleResponse(
            data=MemoryResponse(
                id=updated_memory.get("id", ""),
                content=updated_memory.get("content", ""),
                category=updated_memory.get("category"),
                timestamp=updated_memory.get("timestamp"),
            ),
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"記憶不存在: {str(e)}")
        raise HTTPException(status_code=404, detail=f"記憶不存在")
    except MemoryError as e:
        logger.error(f"記憶服務錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法更新記憶: {str(e)}")
    except Exception as e:
        logger.error(f"更新記憶失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法更新記憶: {str(e)}")


@router.delete("/{memory_id}", status_code=204)
async def delete_memory(
    memory_id: str = Path(..., description="記憶 ID"),
) -> None:
    """
    刪除記憶

    **功能**: 刪除特定的記憶

    Args:
        memory_id: 記憶 ID

    Raises:
        HTTPException: 404 記憶不存在, 500 伺服器錯誤
    """
    try:
        logger.info(f"刪除記憶: memory_id={memory_id}")
        
        # 呼叫 MemoryService.delete_memory() - 只需要 memory_id
        success = MemoryService.delete_memory(memory_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"無法刪除記憶")

    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"記憶服務錯誤: {str(e)}")
        raise HTTPException(status_code=404, detail=f"記憶不存在或無法刪除")
    except Exception as e:
        logger.error(f"刪除記憶失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法刪除記憶: {str(e)}")


@router.post("/batch-delete", response_model=BatchDeleteResponse)
async def batch_delete_memories(
    request: BatchDeleteRequest = Body(...),
) -> BatchDeleteResponse:
    """
    批量刪除記憶

    **功能**: 根據使用者和類別批量刪除記憶

    Args:
        request: 批量刪除請求（包含 user_id 和可選的 category）

    Returns:
        BatchDeleteResponse: 包含刪除數量的回應

    Raises:
        HTTPException: 400 驗證錯誤, 500 伺服器錯誤
    """
    try:
        if not request.user_id or not request.user_id.strip():
            raise HTTPException(status_code=422, detail="使用者 ID 不能為空")

        logger.info(
            f"批量刪除記憶: user_id={request.user_id}, category={request.category}"
        )
        
        deleted_count = MemoryService.batch_delete_memories(
            user_id=request.user_id,
            category=request.category,
        )
        
        return BatchDeleteResponse(
            deleted_count=deleted_count,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"記憶服務錯誤: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法批量刪除記憶: {str(e)}")
    except Exception as e:
        logger.error(f"批量刪除記憶失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法批量刪除記憶: {str(e)}")


@router.post("/search", response_model=SemanticSearchResponse)
async def search_memories(
    request: SemanticSearchRequest = Body(...),
) -> SemanticSearchResponse:
    """
    語義搜索記憶

    **功能**: 使用自然語言查詢搜索相關記憶

    Args:
        request: 搜索請求（包含 user_id, query, top_k）

    Returns:
        SemanticSearchResponse: 搜索結果

    Raises:
        HTTPException: 400 驗證錯誤, 500 伺服器錯誤
    """
    try:
        if not request.user_id or not request.user_id.strip():
            raise HTTPException(status_code=422, detail="使用者 ID 不能為空")

        if not request.query or not request.query.strip():
            raise HTTPException(status_code=422, detail="搜索查詢不能為空")

        logger.info(
            f"搜索記憶: user_id={request.user_id}, query={request.query}, top_k={request.top_k}"
        )
        
        results = MemoryService.search_memories(
            user_id=request.user_id,
            query=request.query,
            top_k=request.top_k,
        )
        
        # 轉換為 response 格式
        memory_responses = []
        for result in results:
            memory_responses.append(MemoryResponse(
                id=result.get("id", ""),
                content=result.get("content", ""),
                category=result.get("metadata", {}).get("category"),
                relevance_score=result.get("metadata", {}).get("relevance"),
            ))
        
        return SemanticSearchResponse(
            results=memory_responses,
            query=request.query,
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索記憶失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"無法搜索記憶: {str(e)}")
