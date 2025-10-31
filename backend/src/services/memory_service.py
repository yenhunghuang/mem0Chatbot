"""
記憶服務模組：Mem0 記憶系統整合

此模組提供長期記憶的管理功能。
"""

from typing import List, Optional, Dict
import uuid

try:
    from mem0 import Memory
except ImportError:
    Memory = None

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import MemoryError, DatabaseError
from .embedding_service import EmbeddingService

logger = get_logger(__name__)


class MemoryService:
    """記憶服務"""

    _mem0_client = None

    @classmethod
    def initialize(cls) -> None:
        """初始化記憶服務"""
        try:
            if Memory is None:
                raise MemoryError("Mem0 庫未安裝")

            # 初始化 Mem0 with Google Gemini
            cls._mem0_client = Memory.from_config(
                {
                    "llm": {
                        "provider": "gemini",  # 正確的 provider 名稱
                        "config": {
                            "model": settings.mem0_llm_model,
                            "temperature": 0.7,
                            "max_tokens": 2000,
                            "api_key": settings.google_api_key,
                        },
                    },
                    "embedder": {
                        "provider": "gemini",  # 正確的 provider 名稱
                        "config": {
                            "model": f"models/{settings.mem0_embedder_model}",
                            "api_key": settings.google_api_key,
                        },
                    },
                    "vector_store": {
                        "provider": "chroma",
                        "config": {
                            "collection_name": "investment_memories",
                            "path": settings.chroma_path,
                        },
                    },
                }
            )
            logger.info("Mem0 客戶端已初始化（使用 Google Gemini）")

        except Exception as e:
            logger.error(f"Mem0 初始化失敗: {str(e)}")
            raise MemoryError(f"無法初始化記憶服務: {str(e)}")

    @classmethod
    def add_memory(cls, user_id: str, content: str, metadata: Optional[Dict] = None) -> str:
        """
        新增記憶

        Args:
            user_id: 使用者 ID
            content: 記憶內容
            metadata: 中繼資料（選用）

        Returns:
            str: 記憶 ID

        Raises:
            MemoryError: 如果新增失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # Mem0 會自動處理嵌入和儲存
            meta = metadata or {}
            meta["user_id"] = user_id

            # 使用 Mem0 API 新增記憶
            result = cls._mem0_client.add(
                messages=[{"role": "user", "content": content}],
                user_id=user_id,
                metadata=meta,
            )

            logger.info(f"記憶已新增: user_id={user_id}")
            return result.get("memory_id", str(uuid.uuid4()))

        except Exception as e:
            logger.error(f"新增記憶失敗: {str(e)}")
            raise MemoryError(f"無法新增記憶: {str(e)}")

    @classmethod
    def search_memories(
        cls,
        user_id: str,
        query: str,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        搜索記憶（US2 T038）

        Args:
            user_id: 使用者 ID
            query: 搜索查詢
            top_k: 返回結果數量

        Returns:
            List[Dict]: 記憶字典列表，包含 id, content, metadata

        Raises:
            MemoryError: 如果搜索失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # 搜索記憶
            results = cls._mem0_client.search(
                query=query,
                user_id=user_id,
                limit=top_k,
            )

            # 提取並轉換為字典格式
            memories = []
            
            if not results:
                logger.info(f"搜索記憶: user_id={user_id}, query='{query}', found=0")
                return memories

            for idx, result in enumerate(results):
                if isinstance(result, dict):
                    # 從 Mem0 結果提取信息
                    # 嘗試多種可能的欄位名稱來取得內容
                    content = (
                        result.get("data") or 
                        result.get("content") or 
                        result.get("text") or 
                        result.get("document", "")
                    )
                    
                    # 如果內容為空，嘗試從 metadata 中的 data 欄位
                    if not content and isinstance(result.get("metadata"), dict):
                        content = result.get("metadata", {}).get("data", "")
                    
                    memory = {
                        "id": result.get("id") or result.get("memory_id") or f"mem_{idx}",
                        "content": str(content).strip() if content else "",
                        "metadata": {
                            "relevance": result.get("relevance", 1.0 - (idx * 0.15)),
                            "created_at": result.get("created_at", ""),
                            "category": result.get("category", "general"),
                            **result.get("metadata", {}),  # 合併原有的 metadata
                        },
                    }
                else:
                    # 如果是字串，轉換為字典
                    memory = {
                        "id": f"mem_{idx}",
                        "content": str(result).strip() if result else "",
                        "metadata": {
                            "relevance": 1.0 - (idx * 0.15),
                            "category": "general",
                        },
                    }
                
                # 只新增有內容的記憶
                if memory["content"]:
                    memories.append(memory)

            logger.info(f"搜索記憶: user_id={user_id}, query='{query}', found={len(memories)}")
            return memories

        except Exception as e:
            logger.error(f"搜索記憶失敗: {str(e)}")
            logger.debug(f"詳細錯誤: {type(e).__name__}")
            # 返回空列表而不是拋出異常，以實現降級
            return []

    @classmethod
    def get_latest_memories(
        cls,
        user_id: str,
        limit: int = 5,
    ) -> List[str]:
        """
        取得最新的記憶

        Args:
            user_id: 使用者 ID
            limit: 返回數量

        Returns:
            List[str]: 最新記憶列表
        """
        try:
            # 使用簡單查詢獲取最新記憶
            return cls.search_memories(user_id, "latest", top_k=limit)
        except Exception:
            return []

    @classmethod
    def delete_memory(cls, user_id: str, memory_id: str) -> bool:
        """
        刪除記憶

        Args:
            user_id: 使用者 ID
            memory_id: 記憶 ID

        Returns:
            bool: 是否刪除成功
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # Mem0 刪除 API
            cls._mem0_client.delete(memory_id=memory_id, user_id=user_id)
            logger.info(f"記憶已刪除: memory_id={memory_id}")
            return True

        except Exception as e:
            logger.error(f"刪除記憶失敗: {str(e)}")
            return False

    @classmethod
    def add_memory_from_message(
        cls,
        user_id: str,
        message_content: str,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        從訊息中自動擷取並儲存記憶

        此方法分析訊息內容，自動識別投資偏好和相關信息，
        並將其儲存為長期記憶。

        Args:
            user_id: 使用者 ID
            message_content: 訊息內容
            metadata: 附加中繼資料

        Returns:
            Optional[str]: 記憶 ID，如果擷取失敗則返回 None

        Raises:
            MemoryError: 如果新增失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # 如果訊息過短，跳過記憶擷取
            if not message_content or len(message_content.strip()) < 3:
                logger.debug(f"訊息過短，跳過記憶擷取: length={len(message_content)}")
                return None

            # 準備中繼資料
            meta = metadata or {}
            meta["source"] = "user_message"
            meta["user_id"] = user_id

            # 呼叫 Mem0 以自動擷取記憶
            # Mem0 會根據內容分析是否有值得儲存的信息
            result = cls._mem0_client.add(
                messages=[
                    {
                        "role": "user",
                        "content": message_content,
                    }
                ],
                user_id=user_id,
                metadata=meta,
            )

            # 提取 memory_id，處理多種結果格式
            memory_id = None
            if isinstance(result, dict):
                memory_id = result.get("memory_id") or result.get("id")
            elif isinstance(result, str):
                memory_id = result
            
            if memory_id:
                logger.info(
                    f"✅ 記憶已從訊息擷取: user_id={user_id[:8]}..., "
                    f"memory_id={memory_id}, content={message_content[:50]}..."
                )
                return memory_id
            else:
                logger.debug(
                    f"⚠️ 訊息未包含可儲存的記憶或 Mem0 無返回: user_id={user_id[:8]}..."
                )
                return None

        except Exception as e:
            logger.warning(
                f"⚠️ 從訊息擷取記憶失敗: user_id={user_id[:8]}..., "
                f"error={str(e)[:100]}"
            )
            # 不拋出異常，允許聊天繼續進行
            return None
