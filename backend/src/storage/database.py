"""
資料庫模組：SQLite 連線管理與初始化

此模組負責 SQLite 資料庫連線、建立和管理。
使用 WAL 模式提升並發效能。
"""

import sqlite3
from pathlib import Path
from typing import Optional

from ..config import settings
from ..utils.logger import get_logger
from ..utils.exceptions import DatabaseError

logger = get_logger(__name__)


class DatabaseManager:
    """資料庫管理器"""

    _connection: Optional[sqlite3.Connection] = None
    _db_path: Optional[Path] = None

    @classmethod
    def initialize(cls, db_path: Optional[str] = None) -> None:
        """
        初始化資料庫連線

        Args:
            db_path: 資料庫路徑（預設使用設定中的路徑）
        """
        try:
            # 解析資料庫路徑
            path_str = db_path or settings.database_url
            if path_str.startswith("sqlite:///"):
                path_str = path_str.replace("sqlite:///", "")

            cls._db_path = Path(path_str)
            cls._db_path.parent.mkdir(parents=True, exist_ok=True)

            # 建立連線
            cls._connection = sqlite3.connect(
                str(cls._db_path),
                check_same_thread=False,
                timeout=30.0,
            )

            # 啟用 WAL 模式以提升並發效能
            cls._connection.execute("PRAGMA journal_mode=WAL")
            cls._connection.execute("PRAGMA synchronous=NORMAL")

            # 建立初始 schema
            cls._init_schema()

            logger.info(f"資料庫已初始化: {cls._db_path}")

        except Exception as e:
            logger.error(f"資料庫初始化失敗: {str(e)}")
            raise DatabaseError(f"無法初始化資料庫: {str(e)}")

    @classmethod
    def _init_schema(cls) -> None:
        """建立資料表"""
        if cls._connection is None:
            raise DatabaseError("資料庫未初始化")

        # 讀取 schema.sql
        schema_file = Path(__file__).parent / "schema.sql"
        if schema_file.exists():
            with open(schema_file, "r", encoding="utf-8") as f:
                sql = f.read()
                cls._connection.executescript(sql)
                cls._connection.commit()
                logger.info("資料表已建立")
        else:
            logger.warning(f"找不到 schema 檔案: {schema_file}")

    @classmethod
    def get_connection(cls) -> sqlite3.Connection:
        """
        取得資料庫連線

        Returns:
            sqlite3.Connection: 資料庫連線

        Raises:
            DatabaseError: 如果資料庫未初始化
        """
        if cls._connection is None:
            cls.initialize()

        if cls._connection is None:
            raise DatabaseError("無法取得資料庫連線")

        return cls._connection

    @classmethod
    def close(cls) -> None:
        """關閉資料庫連線"""
        if cls._connection is not None:
            cls._connection.close()
            cls._connection = None
            logger.info("資料庫連線已關閉")

    @classmethod
    def cleanup_expired(cls, ttl_days: int = 30) -> int:
        """
        清理過期的對話

        Args:
            ttl_days: 保留天數

        Returns:
            int: 刪除的記錄數
        """
        try:
            conn = cls.get_connection()
            cursor = conn.cursor()

            # 計算刪除前的對話數
            cursor.execute(
                """
                SELECT COUNT(*) FROM conversations
                WHERE datetime('now', '-' || ? || ' days') > last_activity
                AND status = 'active'
                """,
                (ttl_days,),
            )
            count = cursor.fetchone()[0]

            if count > 0:
                # 標記為過期
                cursor.execute(
                    """
                    UPDATE conversations SET status = 'expired'
                    WHERE datetime('now', '-' || ? || ' days') > last_activity
                    AND status = 'active'
                    """,
                    (ttl_days,),
                )
                conn.commit()
                logger.info(f"已清理 {count} 個過期對話")

            return count

        except Exception as e:
            logger.error(f"清理過期對話失敗: {str(e)}")
            raise DatabaseError(f"清理失敗: {str(e)}")
