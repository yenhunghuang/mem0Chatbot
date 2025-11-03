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
            
            # Mem0 返回的是 dict，結構為 {'results': [...]}
            if isinstance(results, dict) and 'results' in results:
                results_list = results['results']
                logger.debug(f"從 dict 中提取到 {len(results_list)} 個記憶")
            else:
                # 備用：如果是 list 則直接使用
                results_list = results if isinstance(results, list) else []
                logger.warning(f"意外的 results 類型: {type(results)}, 轉換為 list")
            
            if not results_list:
                logger.info(f"搜索記憶: user_id={user_id}, query='{query}', found=0")
                return memories

            for idx, result in enumerate(results_list):
                if isinstance(result, dict):
                    # 從 Mem0 結果提取信息
                    # Mem0 結構: {'id': '...', 'memory': '實際內容', 'score': ..., 'metadata': {...}}
                    # 優先順序：memory > document > content > text > data > metadata.data
                    content = None
                    
                    # 第 1 層：直接欄位（Mem0 使用 'memory' 欄位）
                    if result.get("memory"):
                        content = result.get("memory")
                        logger.debug(f"[{idx}] 從 memory 提取: {str(content)[:50]}")
                    elif result.get("document"):
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
                            "relevance": result.get("score", result.get("relevance", 1.0 - (idx * 0.15))),
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
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"搜索記憶失敗: {type(e).__name__}: {str(e)[:100]}\n完整堆棧:\n{error_trace}")
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
                logger.info(f"[Mem0] 訊息過短，跳過記憶擷取: length={len(message_content)}")
                return None

            logger.info(f"[Mem0] 開始提取偏好: message={message_content[:50]!r}...")

            # 準備中繼資料
            meta = metadata or {}
            meta["source"] = "user_message"
            meta["user_id"] = user_id

            logger.debug(f"[Mem0] 呼叫 add() API: user_id={user_id[:8]}..., metadata={meta}")

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

            logger.debug(f"[Mem0] add() 返回結果: type={type(result)}, value={result!r}")

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
                    f"[Mem0] 記憶已提取並儲存: user_id={user_id[:8]}..., "
                    f"memory_id={memory_id}, content={message_content[:50]}..."
                )
                return memory_id
            else:
                logger.info(
                    f"[Mem0] 訊息未包含可儲存的記憶: user_id={user_id[:8]}..., "
                    f"message={message_content[:50]}..."
                )
                return None

        except Exception as e:
            logger.warning(
                f"[Mem0] 記憶提取失敗: user_id={user_id[:8]}..., "
                f"error={str(e)[:100]}"
            )
            import traceback
            logger.debug(f"   詳細錯誤堆棧:\n{traceback.format_exc()}")
            # 不拋出異常，允許聊天繼續進行
            return None

    @classmethod
    def get_memories(
        cls,
        user_id: str,
        limit: int = 100,
        category: Optional[str] = None,
    ) -> List[Dict]:
        """
        取得使用者的記憶列表（US3 T048）

        Args:
            user_id: 使用者 ID
            limit: 返回數量限制
            category: 記憶類別過濾（選用）

        Returns:
            List[Dict]: 記憶字典列表

        Raises:
            MemoryError: 如果取得失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # 使用簡單搜索取得所有記憶
            all_memories = cls._mem0_client.search(
                query="",
                user_id=user_id,
                limit=limit,
            )

            # 轉換結果格式
            memories = []
            if isinstance(all_memories, dict) and 'results' in all_memories:
                results_list = all_memories['results']
            else:
                results_list = all_memories if isinstance(all_memories, list) else []

            for idx, result in enumerate(results_list):
                if isinstance(result, dict):
                    memory = result
                elif hasattr(result, '__dict__'):
                    memory = result.__dict__
                else:
                    memory = {
                        "id": f"mem_{idx}",
                        "content": str(result).strip() if result else "",
                    }

                # 過濾類別
                if category and memory.get("metadata", {}).get("category") != category:
                    continue

                memories.append(memory)

            logger.info(f"取得記憶列表: user_id={user_id}, count={len(memories)}")
            return memories

        except Exception as e:
            logger.error(f"取得記憶列表失敗: {str(e)}")
            return []

    @classmethod
    def get_memory_by_id(cls, memory_id: str) -> Optional[Dict]:
        """
        根據 ID 取得單一記憶（US3 T049）

        Args:
            memory_id: 記憶 ID

        Returns:
            Optional[Dict]: 記憶字典，或 None 若不存在

        Raises:
            MemoryError: 如果取得失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # Mem0 沒有直接的 get_by_id，所以需要透過搜索或內部存儲
            # 對於此實作，我們假設記憶 ID 在搜索結果中可用
            # 這是一個簡化版本，實際可能需要存儲層支持
            logger.info(f"根據 ID 取得記憶: memory_id={memory_id}")
            
            # 返回 None 表示不存在（需要與存儲層整合）
            return None

        except Exception as e:
            logger.error(f"取得記憶失敗: {str(e)}")
            return None

    @classmethod
    def update_memory(
        cls,
        memory_id: str,
        content: str,
        category: Optional[str] = None,
    ) -> Dict:
        """
        更新記憶內容（US3 T050）

        Args:
            memory_id: 記憶 ID
            content: 新的記憶內容
            category: 記憶類別（選用）

        Returns:
            Dict: 更新後的記憶字典

        Raises:
            MemoryError: 如果更新失敗
            ValueError: 如果記憶不存在
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # Mem0 的更新操作
            # 先刪除舊記憶，再新增新記憶
            meta = {}
            if category:
                meta["category"] = category
            meta["updated"] = True

            # 使用 Mem0 的更新方法
            result = cls._mem0_client.update(
                memory_id=memory_id,
                data=content,
                metadata=meta,
            )

            logger.info(f"記憶已更新: memory_id={memory_id}")
            return result if isinstance(result, dict) else {
                "id": memory_id,
                "content": content,
                "category": category,
            }

        except Exception as e:
            logger.error(f"更新記憶失敗: {str(e)}")
            raise MemoryError(f"無法更新記憶: {str(e)}")

    @classmethod
    def batch_delete_memories(
        cls,
        user_id: str,
        category: Optional[str] = None,
    ) -> int:
        """
        批量刪除記憶（US3 T051）

        Args:
            user_id: 使用者 ID
            category: 要刪除的記憶類別（選用，若不指定則刪除所有）

        Returns:
            int: 刪除的記憶數量

        Raises:
            MemoryError: 如果刪除失敗
        """
        try:
            if cls._mem0_client is None:
                cls.initialize()

            # 先取得所有匹配的記憶
            memories = cls.get_memories(user_id, category=category)

            # 批量刪除
            deleted_count = 0
            for memory in memories:
                try:
                    memory_id = memory.get("id", "")
                    if memory_id:
                        cls._mem0_client.delete(memory_id=memory_id, user_id=user_id)
                        deleted_count += 1
                except Exception as e:
                    logger.warning(f"刪除單一記憶失敗: memory_id={memory_id}, {str(e)}")

            logger.info(f"批量刪除記憶完成: user_id={user_id}, deleted={deleted_count}")
            return deleted_count

        except Exception as e:
            logger.error(f"批量刪除記憶失敗: {str(e)}")
            raise MemoryError(f"無法批量刪除記憶: {str(e)}")
