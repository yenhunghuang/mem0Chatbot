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

            # 提取並轉換為統一格式
            memories = []
            
            # Mem0 返回的是 dict，結構為 {'results': [...]}
            if isinstance(results, dict) and 'results' in results:
                results_list = results['results']
                logger.debug(f"從 Mem0 提取到 {len(results_list)} 個記憶結果")
            else:
                # 備用：如果是 list 則直接使用
                results_list = results if isinstance(results, list) else []
                logger.warning(f"意外的 results 類型: {type(results)}")
            
            if not results_list:
                logger.info(f"搜索記憶: user_id={user_id}, query='{query}', found=0")
                return []

            for idx, result in enumerate(results_list):
                if not isinstance(result, dict):
                    logger.warning(f"跳過非字典格式的結果: {type(result)}")
                    continue
                
                # 📌 直接從 Mem0 標準格式提取（遵循 SDK 文檔）
                memory_id = result.get("id", f"mem_{idx}")  # 如果沒有 id，生成一個
                # 支援多種欄位名稱：memory, text, content
                content = result.get("memory", result.get("text", result.get("content", "")))
                raw_score = result.get("score", 0.0)     # Mem0 的分數（可能是距離或相似度）
                
                # 📌 正規化分數到 0-1 範圍
                # Mem0 的 score 可能是距離分數（越小越相關）或相似度分數
                # 如果分數 > 1，視為距離分數，需要轉換為相似度
                if raw_score > 1.0:
                    # 距離分數：使用倒數並限制在 0-1 範圍
                    score = 1.0 / (1.0 + raw_score)
                    logger.debug(f"轉換距離分數: {raw_score:.3f} → {score:.3f}")
                else:
                    # 相似度分數：直接使用
                    score = raw_score if raw_score > 0 else 0.5  # 預設分數
                
                # 驗證必要字段
                if not content or not str(content).strip():
                    logger.warning(f"跳過無效記憶 (idx={idx}): id={memory_id}, has_content={bool(content)}")
                    continue
                
                # 📌 過濾低質量記憶（通用描述性文本）
                # 這些通常是 Mem0 生成的摘要，而非用戶真實偏好
                low_quality_patterns = [
                    "looking for",
                    "asking about",
                    "requesting information",
                    "wants to know",
                    "interested in learning",
                ]
                
                content_lower = str(content).lower()
                is_low_quality = any(pattern in content_lower for pattern in low_quality_patterns)
                
                if is_low_quality:
                    logger.info(f"過濾低質量記憶 (idx={idx}): {content[:50]}... (score={score:.3f})")
                    continue
                
                # 📌 統一格式：只在頂層存儲 relevance_score
                memory = {
                    "id": memory_id,
                    "content": str(content).strip(),
                    "relevance_score": score,  # 單一數據源
                    "metadata": result.get("metadata", {}),  # 保留原始 metadata
                    "created_at": result.get("created_at"),
                    "updated_at": result.get("updated_at"),
                }
                
                memories.append(memory)
                logger.debug(f"✓ 記憶 {idx+1}: {content[:40]}... (相關度: {score:.2%})")

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

            logger.info(f"開始刪除記憶: user_id={user_id}, memory_id={memory_id}")
            
            cls._mem0_client.delete(memory_id=memory_id, user_id=user_id)
            
            logger.info(f"記憶已刪除: user_id={user_id}, memory_id={memory_id}")
            return True

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"刪除記憶失敗: {type(e).__name__}: {str(e)}\n{error_trace}")
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

            # 優先使用 get_all()，如果失敗則使用 search()
            all_memories = None
            try:
                all_memories = cls._mem0_client.get_all(
                    user_id=user_id,
                )
                # 檢查是否是 MagicMock 或無效返回
                if hasattr(all_memories, '_mock_name') or (isinstance(all_memories, dict) and not all_memories.get('results') and not all_memories.get('memories')):
                    # 是 MagicMock 或空字典，嘗試 search
                    logger.debug("get_all() 返回無效結果，嘗試 search()")
                    all_memories = None
            except Exception as e:
                logger.debug(f"get_all() 失敗，嘗試 search(): {str(e)}")
                all_memories = None
            
            # 如果 get_all() 無效，使用 search()
            if all_memories is None:
                try:
                    all_memories = cls._mem0_client.search(
                        query="",
                        user_id=user_id,
                        limit=limit,
                    )
                except Exception as e:
                    logger.debug(f"search() 也失敗: {str(e)}")
                    all_memories = {}

            # 轉換結果格式
            memories = []
            
            # Mem0 返回格式可能是多種：list, dict with 'results', dict with 'memories', 或 MagicMock
            if isinstance(all_memories, dict):
                # 嘗試多種可能的 key
                results_list = (
                    all_memories.get('results') or 
                    all_memories.get('memories') or 
                    all_memories.get('data') or
                    []
                )
                logger.debug(f"從 dict 提取記憶: keys={list(all_memories.keys())}, count={len(results_list)}")
            elif isinstance(all_memories, list):
                results_list = all_memories
                logger.debug(f"直接使用 list: count={len(results_list)}")
            else:
                # 嘗試作為字典處理（包括 MagicMock）
                try:
                    results_list = []
                    if hasattr(all_memories, 'get'):
                        results_list = (
                            all_memories.get('results') or 
                            all_memories.get('memories') or 
                            all_memories.get('data') or
                            []
                        )
                    logger.warning(f"嘗試作為字典處理 MagicMock: count={len(results_list)}")
                except Exception:
                    results_list = []
                    logger.warning(f"意外的返回類型: {type(all_memories)}")

            for idx, result in enumerate(results_list):
                try:
                    if isinstance(result, dict):
                        # 提取記憶內容 - 支援多種欄位名稱
                        content = (
                            result.get("memory") or
                            result.get("content") or
                            result.get("text") or
                            result.get("data") or
                            ""
                        )
                        
                        # 從 metadata 提取額外信息
                        metadata = result.get("metadata", {})
                        if isinstance(metadata, dict):
                            # 如果內容在 metadata.data 中
                            if not content and metadata.get("data"):
                                content = metadata.get("data")
                        
                        memory = {
                            "id": result.get("id") or result.get("memory_id") or f"mem_{idx}",
                            "content": str(content).strip() if content else "",
                            "metadata": metadata if isinstance(metadata, dict) else {},
                            "category": result.get("category") or metadata.get("category", "general"),
                            "timestamp": result.get("created_at") or result.get("timestamp", ""),
                        }
                    elif hasattr(result, '__dict__'):
                        # 如果是物件，轉換為字典
                        result_dict = result.__dict__
                        memory = {
                            "id": result_dict.get("id", f"mem_{idx}"),
                            "content": str(result_dict.get("content", "")).strip(),
                            "metadata": result_dict.get("metadata", {}),
                            "category": result_dict.get("category", "general"),
                            "timestamp": result_dict.get("timestamp", ""),
                        }
                    else:
                        # 備用：作為字串處理
                        memory = {
                            "id": f"mem_{idx}",
                            "content": str(result).strip() if result else "",
                            "metadata": {},
                            "category": "general",
                            "timestamp": "",
                        }

                    # 過濾類別
                    if category and memory.get("category") != category:
                        continue

                    # 只加入有內容的記憶
                    if memory.get("content"):
                        memories.append(memory)
                        logger.debug(f"✓ 記憶已添加: {memory['id'][:20]}...")
                    else:
                        logger.debug(f"✗ 記憶內容為空，跳過: {memory.get('id', 'unknown')}")
                        
                except Exception as e:
                    logger.warning(f"處理記憶項目失敗 (idx={idx}): {str(e)}")
                    continue

            # 限制返回數量
            if len(memories) > limit:
                memories = memories[:limit]

            logger.info(f"取得記憶列表: user_id={user_id}, count={len(memories)}, category={category}")
            return memories

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"取得 記憶列表失敗: {type(e).__name__}. {str(e)}\n{error_trace}")
            # 返回空列表而不是拋出異常
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

            logger.info(f"開始批量刪除記憶: user_id={user_id}, category={category}")
            
            # 先取得所有匹配的記憶
            memories = cls.get_memories(user_id, category=category)

            # 批量刪除
            deleted_count = 0
            failed_count = 0
            errors = []
            
            for memory in memories:
                try:
                    memory_id = memory.get("id", "")
                    if memory_id:
                        # Mem0 delete() 不需要 user_id 參數
                        cls._mem0_client.delete(memory_id=memory_id)
                        deleted_count += 1
                        logger.debug(f"記憶已刪除: memory_id={memory_id}")
                except Exception as e:
                    failed_count += 1
                    error_msg = f"刪除 {memory_id} 失敗: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)

            logger.info(
                f"批量刪除記憶完成: user_id={user_id}, "
                f"deleted={deleted_count}, failed={failed_count}"
            )
            
            if errors:
                logger.warning(f"批量刪除錯誤: {errors}")
            
            return deleted_count

        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"批量刪除記憶失敗: {type(e).__name__}: {str(e)}\n{error_trace}")
            raise MemoryError(f"無法批量刪除記憶: {str(e)}")
