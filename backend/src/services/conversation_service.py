"""
對話服務

協調對話流程：儲存訊息 → 擷取記憶 → 呼叫 LLM → 儲存回應。
"""

from typing import List, Optional, Dict
import uuid

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import (
    ValidationError,
    MemoryError,
    LLMError,
    DatabaseError,
    NotFoundError,
)
from ..storage.storage_service import StorageService
from ..services.memory_service import MemoryService
from ..services.llm_service import LLMService
from ..models.conversation import Conversation, Message

logger = get_logger(__name__)


class ConversationService:
    """對話服務"""

    @staticmethod
    def validate_user_id(user_id: str) -> None:
        """
        驗證 user_id

        Args:
            user_id: 使用者 ID

        Raises:
            ValidationError: 如果驗證失敗
        """
        try:
            uuid.UUID(user_id)
        except (ValueError, TypeError):
            raise ValidationError(
                "無效的 user_id 格式",
                details={"field": "user_id", "reason": "must be valid UUID"},
            )

    @staticmethod
    def validate_message(message: str) -> None:
        """
        驗證訊息內容

        驗證項目：
        - 不能為空
        - 必須是字串型態
        - 長度 1-10000 字元
        - 不能只包含空白字元

        Args:
            message: 訊息內容

        Raises:
            ValidationError: 如果驗證失敗
        """
        # T028: 輸入驗證
        if not message or not isinstance(message, str):
            raise ValidationError(
                "訊息不能為空",
                details={
                    "field": "message",
                    "reason": "message is required and must be string",
                },
            )

        # 驗證最小長度
        if len(message.strip()) == 0:
            raise ValidationError(
                "訊息不能只包含空白",
                details={
                    "field": "message",
                    "reason": "message cannot be blank",
                },
            )

        # 驗證最大長度（T028）
        if len(message) > 10000:
            raise ValidationError(
                "訊息超過最大長度 (10000 字元)",
                details={
                    "field": "message",
                    "reason": f"max length is 10000 characters, got {len(message)}",
                },
            )

    @staticmethod
    def get_or_create_conversation(
        user_id: str,
        conversation_id: Optional[int] = None,
    ) -> Conversation:
        """
        取得或建立對話

        Args:
            user_id: 使用者 ID
            conversation_id: 對話 ID（可選）

        Returns:
            Conversation: 對話物件

        Raises:
            ValidationError: 如果 user_id 無效
            DatabaseError: 如果操作失敗
        """
        ConversationService.validate_user_id(user_id)

        try:
            if conversation_id:
                try:
                    # 嘗試取得現有對話
                    conversation = StorageService.get_conversation(conversation_id)
                    # 驗證對話屬於該使用者
                    if conversation.user_id != user_id:
                        raise ValidationError(
                            "對話不屬於該使用者",
                            details={
                                "conversation_id": conversation_id,
                                "reason": "unauthorized access",
                            },
                        )
                    logger.info(f"取得對話: conversation_id={conversation_id}")
                    return conversation
                except NotFoundError:
                    # 對話不存在，建立新對話 (降級處理)
                    logger.warning(
                        f"對話不存在 (conversation_id={conversation_id})，建立新對話"
                    )
                    conversation = StorageService.create_conversation(user_id)
                    logger.info(f"建立新對話: conversation_id={conversation.id}")
                    return conversation
            else:
                # 建立新對話
                conversation = StorageService.create_conversation(user_id)
                logger.info(f"建立新對話: conversation_id={conversation.id}")
                return conversation

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"取得或建立對話失敗: {str(e)}")
            raise DatabaseError(f"無法處理對話: {str(e)}")

    @staticmethod
    def process_message(
        user_id: str,
        conversation_id: Optional[int] = None,
        message: str = "",
    ) -> Dict:
        """
        處理使用者訊息完整流程

        步驟：
        1. 驗證輸入
        2. 取得或建立對話
        3. 儲存使用者訊息
        4. 從訊息擷取記憶
        5. 搜索相關記憶
        6. 呼叫 LLM 生成回應
        7. 儲存助理回應

        Args:
            user_id: 使用者 ID
            conversation_id: 對話 ID（可選）
            message: 使用者訊息

        Returns:
            Dict: 包含回應的字典

        Raises:
            ValidationError: 如果輸入無效
            LLMError: 如果 LLM 呼叫失敗
            DatabaseError: 如果資料庫操作失敗
        """
        # 步驟 1: 驗證輸入
        ConversationService.validate_user_id(user_id)
        ConversationService.validate_message(message)

        try:
            # 步驟 2: 取得或建立對話
            conversation = ConversationService.get_or_create_conversation(
                user_id,
                conversation_id,
            )

            logger.info(
                f"[對話 {conversation.id}] 開始處理訊息",
            )

            # 步驟 3: 儲存使用者訊息
            user_msg = StorageService.save_message(
                conversation.id,
                "user",
                message,
            )

            logger.info(
                f"[對話 {conversation.id}] 使用者訊息已儲存: message_id={user_msg.id}"
            )

            # 步驟 4: 從訊息擷取記憶（非阻塞）
            logger.info(f"[Step 4] 開始提取記憶... user_id={user_id[:8]}..., message={message[:30]!r}...")
            memory_id = None
            try:
                memory_id = MemoryService.add_memory_from_message(
                    user_id,
                    message,
                    {"conversation_id": conversation.id},
                )
                if memory_id:
                    logger.info(
                        f"[Step 4] 記憶已提取並儲存: memory_id={memory_id}"
                    )
                else:
                    logger.info(
                        f"[Step 4] Mem0 未提取到可儲存的偏好"
                    )
            except Exception as e:
                logger.warning(
                    f"[Step 4] 記憶提取失敗 (非阻塞): {str(e)[:100]}"
                )
                import traceback
                logger.debug(f"   記憶提取錯誤堆棧: {traceback.format_exc()}")

            # 步驟 5: 搜索相關記憶
            memories_used = []
            try:
                logger.info(f"[Step 5] 開始搜索記憶: user_id={user_id[:8]}..., query={message!r}")
                
                memories = MemoryService.search_memories(
                    user_id,
                    message,
                    top_k=settings.memory_retrieval_top_k,
                )
                memories_used = memories
                
                logger.info(
                    f"[Step 5] 搜索記憶完成: found={len(memories_used)}"
                )
                if memories_used:
                    for idx, mem in enumerate(memories_used, 1):
                        content = mem.get("content", "")[:50] if isinstance(mem, dict) else str(mem)[:50]
                        logger.info(f"   [{idx}] 記憶: {content}...")
                else:
                    logger.info(f"   [Step 5] 未找到任何記憶")
            except Exception as e:
                logger.warning(
                    f"[Step 5] 搜索記憶失敗 (降級): {str(e)[:100]}"
                )
                import traceback
                logger.debug(f"   詳細錯誤: {traceback.format_exc()}")

            # 步驟 6: 取得對話歷史（用於上下文）
            conversation_history = StorageService.get_conversation_messages(
                conversation.id,
                limit=settings.conversation_context_window,
            )

            # 轉換為 LLM 格式
            history = [
                {
                    "role": msg.role,
                    "content": msg.content,
                }
                for msg in conversation_history
            ]

            # 步驟 7: 呼叫 LLM 生成回應
            assistant_response = LLMService.generate_response(
                user_input=message,
                memories=memories_used,
                conversation_history=history,
            )

            logger.info(
                f"[對話 {conversation.id}] LLM 回應已生成"
            )

            # 步驟 8: 儲存助理回應
            assistant_msg = StorageService.save_message(
                conversation.id,
                "assistant",
                assistant_response,
            )

            logger.info(
                f"[對話 {conversation.id}] 助理回應已儲存: message_id={assistant_msg.id}"
            )

            # 返回完整回應
            return {
                "conversation_id": conversation.id,
                "user_message": user_msg.to_dict(),
                "assistant_message": assistant_msg.to_dict(),
                "memories_used": memories_used,
            }

        except ValidationError:
            logger.warning(f"驗證錯誤: {str(e)}")
            raise
        except LLMError as e:
            logger.error(f"LLM 錯誤: {str(e)}")
            raise
        except DatabaseError as e:
            logger.error(f"資料庫錯誤: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"未預期的錯誤: {str(e)}", exc_info=e)
            raise DatabaseError(f"無法處理訊息: {str(e)}")

    @staticmethod
    def get_conversation_history(
        conversation_id: int,
        limit: int = 50,
    ) -> List[Dict]:
        """
        取得對話歷史

        Args:
            conversation_id: 對話 ID
            limit: 最大返回數量

        Returns:
            List[Dict]: 訊息歷史

        Raises:
            DatabaseError: 如果查詢失敗
        """
        try:
            messages = StorageService.get_conversation_messages(
                conversation_id,
                limit=limit,
            )

            return [msg.to_dict() for msg in messages]

        except Exception as e:
            logger.error(f"取得對話歷史失敗: {str(e)}")
            raise DatabaseError(f"無法取得對話歷史: {str(e)}")
