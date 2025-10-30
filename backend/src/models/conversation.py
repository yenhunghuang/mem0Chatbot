"""
對話和訊息模型

定義資料庫模型和轉換邏輯。
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class ConversationDB:
    """對話資料庫模型"""

    id: Optional[int] = None
    user_id: str = ""
    created_at: str = ""
    last_activity: str = ""
    status: str = "active"  # active, archived, expired
    message_count: int = 0

    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationDB":
        """從字典建立"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MessageDB:
    """訊息資料庫模型"""

    id: Optional[int] = None
    conversation_id: int = 0
    role: str = "user"  # user, assistant
    content: str = ""
    timestamp: str = ""
    token_count: int = 0

    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MessageDB":
        """從字典建立"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class PreferenceDB:
    """投資偏好資料庫模型"""

    memory_id: str = ""
    user_id: str = ""
    content: str = ""
    category: str = "preference"  # preference, fact, behavior
    created_at: str = ""
    updated_at: str = ""
    relevance: float = 1.0

    def to_dict(self) -> dict:
        """轉換為字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "PreferenceDB":
        """從字典建立"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Conversation:
    """對話業務模型"""

    def __init__(
        self,
        user_id: str,
        conversation_id: Optional[int] = None,
        created_at: Optional[str] = None,
        last_activity: Optional[str] = None,
        status: str = "active",
        message_count: int = 0,
    ):
        """初始化對話"""
        self.id = conversation_id
        self.user_id = user_id
        self.created_at = created_at or datetime.now().isoformat()
        self.last_activity = last_activity or datetime.now().isoformat()
        self.status = status
        self.message_count = message_count

    def to_db_model(self) -> ConversationDB:
        """轉換為資料庫模型"""
        return ConversationDB(
            id=self.id,
            user_id=self.user_id,
            created_at=self.created_at,
            last_activity=self.last_activity,
            status=self.status,
            message_count=self.message_count,
        )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_activity": self.last_activity,
            "status": self.status,
            "message_count": self.message_count,
        }

    @classmethod
    def from_db_model(cls, db_model: ConversationDB) -> "Conversation":
        """從資料庫模型建立"""
        return cls(
            user_id=db_model.user_id,
            conversation_id=db_model.id,
            created_at=db_model.created_at,
            last_activity=db_model.last_activity,
            status=db_model.status,
            message_count=db_model.message_count,
        )


class Message:
    """訊息業務模型"""

    def __init__(
        self,
        conversation_id: int,
        role: str,
        content: str,
        message_id: Optional[int] = None,
        timestamp: Optional[str] = None,
        token_count: Optional[int] = None,
    ):
        """初始化訊息"""
        self.id = message_id
        self.conversation_id = conversation_id
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now().isoformat()
        self.token_count = token_count or len(content.split())

    def to_db_model(self) -> MessageDB:
        """轉換為資料庫模型"""
        return MessageDB(
            id=self.id,
            conversation_id=self.conversation_id,
            role=self.role,
            content=self.content,
            timestamp=self.timestamp,
            token_count=self.token_count,
        )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "token_count": self.token_count,
        }

    @classmethod
    def from_db_model(cls, db_model: MessageDB) -> "Message":
        """從資料庫模型建立"""
        return cls(
            conversation_id=db_model.conversation_id,
            role=db_model.role,
            content=db_model.content,
            message_id=db_model.id,
            timestamp=db_model.timestamp,
            token_count=db_model.token_count,
        )


class Preference:
    """投資偏好業務模型"""

    def __init__(
        self,
        user_id: str,
        content: str,
        memory_id: Optional[str] = None,
        category: str = "preference",
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        relevance: float = 1.0,
    ):
        """初始化偏好"""
        self.memory_id = memory_id
        self.user_id = user_id
        self.content = content
        self.category = category
        self.created_at = created_at or datetime.now().isoformat()
        self.updated_at = updated_at or datetime.now().isoformat()
        self.relevance = relevance

    def to_db_model(self) -> PreferenceDB:
        """轉換為資料庫模型"""
        return PreferenceDB(
            memory_id=self.memory_id,
            user_id=self.user_id,
            content=self.content,
            category=self.category,
            created_at=self.created_at,
            updated_at=self.updated_at,
            relevance=self.relevance,
        )

    def to_dict(self) -> dict:
        """轉換為字典"""
        return {
            "memory_id": self.memory_id,
            "user_id": self.user_id,
            "content": self.content,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "relevance": self.relevance,
        }

    @classmethod
    def from_db_model(cls, db_model: PreferenceDB) -> "Preference":
        """從資料庫模型建立"""
        return cls(
            user_id=db_model.user_id,
            content=db_model.content,
            memory_id=db_model.memory_id,
            category=db_model.category,
            created_at=db_model.created_at,
            updated_at=db_model.updated_at,
            relevance=db_model.relevance,
        )
