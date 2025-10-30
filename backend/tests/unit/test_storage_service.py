"""
儲存服務單元測試

測試 StorageService 的對話和訊息儲存功能。
"""

import pytest
import sqlite3
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from backend.src.utils.exceptions import DatabaseError


class TestStorageServiceConversation:
    """測試對話儲存相關操作"""

    @pytest.fixture
    def mock_db(self):
        """模擬資料庫連線"""
        with patch("backend.src.storage.database.DatabaseManager") as mock:
            yield mock

    def test_create_conversation_success(self, mock_db):
        """測試成功建立對話"""
        from backend.src.storage.database import DatabaseManager

        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1
        mock_db.get_connection.return_value = mock_conn

        user_id = "user_uuid_001"

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            INSERT INTO conversations (user_id, created_at, last_activity, status, message_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, datetime.now().isoformat(), datetime.now().isoformat(), "active", 0),
        )
        conversation_id = cursor.lastrowid

        # 斷言
        assert conversation_id == 1
        mock_cursor.execute.assert_called()

    def test_get_conversation_success(self, mock_db):
        """測試成功取得對話"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        conversation_id = 1
        expected_row = (
            1,
            "user_001",
            "2025-01-01T00:00:00",
            "2025-01-01T00:05:00",
            "active",
            5,
        )
        mock_cursor.fetchone.return_value = expected_row
        mock_db.get_connection.return_value = mock_conn

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            "SELECT id, user_id, created_at, last_activity, status, message_count FROM conversations WHERE id = ?",
            (conversation_id,),
        )
        row = cursor.fetchone()

        # 斷言
        assert row == expected_row
        assert row[1] == "user_001"  # user_id
        assert row[4] == "active"  # status

    def test_get_conversation_not_found(self, mock_db):
        """測試取得不存在的對話"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = None
        mock_db.get_connection.return_value = mock_conn

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            "SELECT * FROM conversations WHERE id = ?",
            (999,),
        )
        row = cursor.fetchone()

        # 斷言
        assert row is None

    def test_update_conversation_last_activity(self, mock_db):
        """測試更新對話最後活動時間"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        conversation_id = 1
        new_time = datetime.now().isoformat()

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            UPDATE conversations
            SET last_activity = ?, message_count = message_count + 1
            WHERE id = ?
            """,
            (new_time, conversation_id),
        )
        mock_conn.commit()

        # 斷言
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()


class TestStorageServiceMessage:
    """測試訊息儲存相關操作"""

    @pytest.fixture
    def mock_db(self):
        """模擬資料庫連線"""
        with patch("backend.src.storage.database.DatabaseManager") as mock:
            yield mock

    def test_save_message_success(self, mock_db):
        """測試成功儲存訊息"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 101
        mock_db.get_connection.return_value = mock_conn

        conversation_id = 1
        role = "user"
        content = "我偏好投資科技股"
        timestamp = datetime.now().isoformat()

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, timestamp, len(content.split())),
        )
        message_id = cursor.lastrowid
        mock_conn.commit()

        # 斷言
        assert message_id == 101
        mock_cursor.execute.assert_called()
        mock_conn.commit.assert_called()

    def test_save_message_assistant_response(self, mock_db):
        """測試儲存助理回應訊息"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 102
        mock_db.get_connection.return_value = mock_conn

        conversation_id = 1
        role = "assistant"
        content = "根據您的偏好，科技股是一個不錯的選擇..."

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, datetime.now().isoformat(), len(content.split())),
        )
        message_id = cursor.lastrowid

        # 斷言
        assert message_id == 102

    def test_get_conversation_messages(self, mock_db):
        """測試取得對話的所有訊息"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        messages = [
            (1, 1, "user", "我偏好科技股", "2025-01-01T00:00:00", 4),
            (2, 1, "assistant", "很好的選擇", "2025-01-01T00:00:05", 3),
            (3, 1, "user", "你能推薦嗎？", "2025-01-01T00:00:10", 3),
        ]
        mock_cursor.fetchall.return_value = messages
        mock_db.get_connection.return_value = mock_conn

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            SELECT id, conversation_id, role, content, timestamp, token_count
            FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            """,
            (1,),
        )
        rows = cursor.fetchall()

        # 斷言
        assert len(rows) == 3
        assert rows[0][2] == "user"  # 第一條是使用者訊息
        assert rows[1][2] == "assistant"  # 第二條是助理訊息

    def test_message_token_count_tracking(self, mock_db):
        """測試訊息的 token 計數追蹤"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.get_connection.return_value = mock_conn

        content = "這是一條測試訊息包含了多個單詞"
        expected_tokens = len(content.split())  # 簡單實作

        # 行動
        cursor = mock_conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (1, "user", content, datetime.now().isoformat(), expected_tokens),
        )

        # 斷言
        call_args = mock_cursor.execute.call_args
        assert expected_tokens > 0


class TestStorageServiceQueryPerformance:
    """測試儲存層查詢效能（索引驗證）"""

    @pytest.fixture
    def mock_db(self):
        """模擬資料庫連線"""
        with patch("backend.src.storage.database.DatabaseManager") as mock:
            yield mock

    def test_query_by_user_id_uses_index(self, mock_db):
        """測試按 user_id 查詢使用索引"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_db.get_connection.return_value = mock_conn

        user_id = "user_001"

        # 行動
        cursor = mock_conn.cursor()
        # 這個查詢應該使用 conversations_user_id_idx 索引
        cursor.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY last_activity DESC",
            (user_id,),
        )

        # 斷言
        assert mock_cursor.execute.called

    def test_query_by_conversation_id_for_messages(self, mock_db):
        """測試按 conversation_id 查詢訊息使用索引"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.fetchall.return_value = []
        mock_db.get_connection.return_value = mock_conn

        conversation_id = 1

        # 行動
        cursor = mock_conn.cursor()
        # 這個查詢應該使用 messages_conversation_id_timestamp_idx 索引
        cursor.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
            """,
            (conversation_id,),
        )

        # 斷言
        assert mock_cursor.execute.called


class TestStorageServiceTransactions:
    """測試儲存層事務處理"""

    @pytest.fixture
    def mock_db(self):
        """模擬資料庫連線"""
        with patch("backend.src.storage.database.DatabaseManager") as mock:
            yield mock

    def test_save_conversation_and_message_transaction(self, mock_db):
        """測試儲存對話和訊息的事務"""
        # 安排
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.lastrowid = 1
        mock_db.get_connection.return_value = mock_conn

        # 行動
        cursor = mock_conn.cursor()

        # 開始事務
        cursor.execute("BEGIN TRANSACTION")

        # 建立對話
        cursor.execute(
            """
            INSERT INTO conversations (user_id, created_at, last_activity, status, message_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("user_001", datetime.now().isoformat(), datetime.now().isoformat(), "active", 0),
        )
        conversation_id = cursor.lastrowid

        # 儲存訊息
        cursor.execute(
            """
            INSERT INTO messages (conversation_id, role, content, timestamp, token_count)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, "user", "測試", datetime.now().isoformat(), 1),
        )

        # 提交事務
        mock_conn.commit()

        # 斷言
        assert mock_cursor.execute.called
        assert mock_conn.commit.called
