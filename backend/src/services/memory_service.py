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

            # 調試：記錄原始結果
            logger.debug(f"搜索原始結果數: {len(results)}, 第一個結果類型: {type(results[0]) if results else 'None'}")
            if results and isinstance(results[0], dict):
                logger.debug(f"第一個結果 keys: {results[0].keys()}")

            for idx, result in enumerate(results):
                if isinstance(result, dict):
                    # 從 Mem0 結果提取信息
                    # 優先順序：document > content > text > data > metadata.data
                    content = None
                    
                    # 第 1 層：直接欄位
                    if result.get("document"):
                        content = result.get("document")
                        logger.debug(f"[{idx}] 從 document 提取: {str(content)[:50]}")
                    elif result.get("content"):
                        content = result.get("content")
                        logger.debug(f"[{idx}] 從 content 提取: {str(content)[:50]}")
                    elif result.get("text"):
                        content = result.get("text")
                        logger.debug(f"[{idx}] 從 text 提取: {str(content)[:50]}")
                    elif result.get("data"):
                        content = result.get("data")
                        logger.debug(f"[{idx}] 從 data 提取: {str(content)[:50]}")
                    
                    # 第 2 層：metadata 中的 data（關鍵備用方案）
                    if not content and isinstance(result.get("metadata"), dict):
                        metadata = result.get("metadata", {})
                        if metadata.get("data"):
                            content = metadata.get("data")
                            logger.debug(f"[{idx}] 從 metadata.data 提取: {str(content)[:50]}")
                    
                    # 最後備用：嘗試使用整個結果作為字符串
                    if not content:
                        logger.warning(f"[{idx}] 警告：未找到任何有效內容，結果 keys: {result.keys()}")
                    
                    memory = {
                        "id": result.get("id") or result.get("memory_id") or f"mem_{idx}",
                        "content": str(content).strip() if content else "",
                        "metadata": {
                            "relevance": result.get("relevance", 1.0 - (idx * 0.15)),
                            "created_at": result.get("created_at", ""),
                            "category": result.get("category", "general"),
                            **(result.get("metadata", {}) if isinstance(result.get("metadata"), dict) else {}),
                        },
                    }
                else:
                    # 如果是字符串，直接使用
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
                    logger.debug(f"✓ 記憶已添加: {memory['id'][:20]}... content={memory['content'][:40]}")
                else:
                    logger.warning(f"✗ 記憶內容為空，跳過: {memory['id']}")

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
                logger.info(f"⏭️ 訊息過短，跳過記憶擷取: length={len(message_content)}")
                return None

            logger.info(f"🔎 [Mem0] 開始提取偏好: message={message_content[:50]!r}...")

            # 準備中繼資料
            meta = metadata or {}
            meta["source"] = "user_message"
            meta["user_id"] = user_id

            logger.debug(f"📋 [Mem0] 呼叫 add() API: user_id={user_id[:8]}..., metadata={meta}")

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

            logger.debug(f"📤 [Mem0] add() 返回結果: type={type(result)}, value={result!r}")

            # 提取 memory_id，處理多種結果格式
            memory_id = None
            if isinstance(result, dict):
                memory_id = result.get("memory_id") or result.get("id")
                logger.debug(f"   從字典提取: keys={list(result.keys())}, memory_id={memory_id}")
            elif isinstance(result, str):
                memory_id = result
                logger.debug(f"   直接字符串: memory_id={memory_id}")
            elif isinstance(result, list) and len(result) > 0:
                # 某些版本可能返回列表
                memory_id = result[0] if isinstance(result[0], str) else result[0].get("memory_id")
                logger.debug(f"   從列表提取: memory_id={memory_id}")
            
            if memory_id:
                logger.info(
                    f"✅ [Mem0] 記憶已提取並儲存: user_id={user_id[:8]}..., "
                    f"memory_id={memory_id}, content={message_content[:50]}..."
                )
                return memory_id
            else:
                logger.info(
                    f"ℹ️ [Mem0] 訊息未包含可儲存的記憶: user_id={user_id[:8]}..., "
                    f"message={message_content[:50]}..."
                )
                return None

        except Exception as e:
            logger.warning(
                f"❌ [Mem0] 記憶提取失敗: user_id={user_id[:8]}..., "
                f"error={str(e)[:100]}"
            )
            import traceback
            logger.debug(f"   詳細錯誤堆棧:\n{traceback.format_exc()}")
            # 不拋出異常，允許聊天繼續進行
            return None
