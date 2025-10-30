"""
儲存服務

實作對話和訊息的 CRUD 操作。
"""

from typing import List, Optional
from datetime import datetime

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import DatabaseError, NotFoundError
from ..storage.database import DatabaseManager
from ..models.conversation import ConversationDB, MessageDB, Conversation, Message

logger = get_logger(__name__)


class StorageService:
    """儲存服務"""

    @staticmethod
    def create_conversation(user_id: str) -> Conversation:
        """
        建立新對話

        Args:
            user_id: 使用者 ID

        Returns:
            Conversation: 新建立的對話

        Raises:
            DatabaseError: 如果建立失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            now = datetime.now().isoformat()

            cursor.execute(
                """
                INSERT INTO conversations (user_id, created_at, last_activity, status, message_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, now, now, "active", 0),
            )
            conn.commit()

            conversation_id = cursor.lastrowid

            logger.info(f"對話已建立: conversation_id={conversation_id}, user_id={user_id}")

            return Conversation(
                user_id=user_id,
                conversation_id=conversation_id,
                created_at=now,
                last_activity=now,
                status="active",
                message_count=0,
            )

        except Exception as e:
            logger.error(f"建立對話失敗: {str(e)}")
            raise DatabaseError(f"無法建立對話: {str(e)}")

    @staticmethod
    def get_conversation(conversation_id: int) -> Conversation:
        """
        取得對話

        Args:
            conversation_id: 對話 ID

        Returns:
            Conversation: 對話物件

        Raises:
            NotFoundError: 如果對話不存在
            DatabaseError: 如果查詢失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, created_at, last_activity, status, message_count
                FROM conversations
                WHERE id = ?
                """,
                (conversation_id,),
            )

            row = cursor.fetchone()

            if not row:
                raise NotFoundError(f"對話未找到: {conversation_id}")

            return Conversation(
                user_id=row[1],
                conversation_id=row[0],
                created_at=row[2],
                last_activity=row[3],
                status=row[4],
                message_count=row[5],
            )

        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"取得對話失敗: {str(e)}")
            raise DatabaseError(f"無法取得對話: {str(e)}")

    @staticmethod
    def get_user_conversations(user_id: str, limit: int = 20) -> List[Conversation]:
        """
        取得使用者的所有對話

        Args:
            user_id: 使用者 ID
            limit: 最大返回數量

        Returns:
            List[Conversation]: 對話列表

        Raises:
            DatabaseError: 如果查詢失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, user_id, created_at, last_activity, status, message_count
                FROM conversations
                WHERE user_id = ?
                ORDER BY last_activity DESC
                LIMIT ?
                """,
                (user_id, limit),
            )

            rows = cursor.fetchall()
            conversations = []

            for row in rows:
                conv = Conversation(
                    user_id=row[1],
                    conversation_id=row[0],
                    created_at=row[2],
                    last_activity=row[3],
                    status=row[4],
                    message_count=row[5],
                )
                conversations.append(conv)

            logger.info(f"取得使用者對話: user_id={user_id}, count={len(conversations)}")
            return conversations

        except Exception as e:
            logger.error(f"取得使用者對話失敗: {str(e)}")
            raise DatabaseError(f"無法取得使用者對話: {str(e)}")

    @staticmethod
    def save_message(
        conversation_id: int,
        role: str,
        content: str,
    ) -> Message:
        """
        儲存訊息

        Args:
            conversation_id: 對話 ID
            role: 角色 (user/assistant)
            content: 訊息內容

        Returns:
            Message: 儲存的訊息

        Raises:
            DatabaseError: 如果儲存失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            now = datetime.now().isoformat()
            token_count = len(content.split())

            # 開始事務
            cursor.execute("BEGIN TRANSACTION")

            # 儲存訊息
            cursor.execute(
                """
                INSERT INTO messages (conversation_id, role, content, timestamp, token_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, now, token_count),
            )

            message_id = cursor.lastrowid

            # 更新對話最後活動時間和訊息計數
            cursor.execute(
                """
                UPDATE conversations
                SET last_activity = ?, message_count = message_count + 1
                WHERE id = ?
                """,
                (now, conversation_id),
            )

            conn.commit()

            logger.info(
                f"訊息已儲存: message_id={message_id}, conversation_id={conversation_id}, role={role}"
            )

            return Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                message_id=message_id,
                timestamp=now,
                token_count=token_count,
            )

        except Exception as e:
            conn.rollback()
            logger.error(f"儲存訊息失敗: {str(e)}")
            raise DatabaseError(f"無法儲存訊息: {str(e)}")

    @staticmethod
    def get_conversation_messages(
        conversation_id: int,
        limit: int = 50,
    ) -> List[Message]:
        """
        取得對話的所有訊息

        Args:
            conversation_id: 對話 ID
            limit: 最大返回數量

        Returns:
            List[Message]: 訊息列表

        Raises:
            DatabaseError: 如果查詢失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, conversation_id, role, content, timestamp, token_count
                FROM messages
                WHERE conversation_id = ?
                ORDER BY timestamp ASC
                LIMIT ?
                """,
                (conversation_id, limit),
            )

            rows = cursor.fetchall()
            messages = []

            for row in rows:
                msg = Message(
                    conversation_id=row[1],
                    role=row[2],
                    content=row[3],
                    message_id=row[0],
                    timestamp=row[4],
                    token_count=row[5],
                )
                messages.append(msg)

            logger.info(
                f"取得對話訊息: conversation_id={conversation_id}, count={len(messages)}"
            )
            return messages

        except Exception as e:
            logger.error(f"取得對話訊息失敗: {str(e)}")
            raise DatabaseError(f"無法取得對話訊息: {str(e)}")

    @staticmethod
    def archive_conversation(conversation_id: int) -> bool:
        """
        封存對話

        Args:
            conversation_id: 對話 ID

        Returns:
            bool: 是否成功

        Raises:
            DatabaseError: 如果操作失敗
        """
        try:
            conn = DatabaseManager.get_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE conversations
                SET status = 'archived'
                WHERE id = ?
                """,
                (conversation_id,),
            )

            conn.commit()

            logger.info(f"對話已封存: conversation_id={conversation_id}")
            return True

        except Exception as e:
            logger.error(f"封存對話失敗: {str(e)}")
            raise DatabaseError(f"無法封存對話: {str(e)}")
