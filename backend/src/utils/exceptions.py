"""
自訂例外模組：定義應用程式特定的例外類別

此模組提供與應用程式域相關的例外類別，用於更精確的錯誤處理。
"""


class ApplicationError(Exception):
    """應用程式基礎例外"""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        """
        初始化例外

        Args:
            message: 錯誤訊息
            code: 錯誤代碼（用於 API 回應）
        """
        self.message = message
        self.code = code
        super().__init__(self.message)


class ValidationError(ApplicationError):
    """驗證錯誤"""

    def __init__(self, message: str, details: dict = None):
        """
        初始化驗證錯誤

        Args:
            message: 錯誤訊息
            details: 詳細信息字典
        """
        self.details = details or {}
        super().__init__(message, code="VALIDATION_ERROR")


class MemoryError(ApplicationError):
    """記憶操作錯誤"""

    def __init__(self, message: str):
        """初始化記憶錯誤"""
        super().__init__(message, code="MEMORY_ERROR")


class LLMError(ApplicationError):
    """LLM 服務錯誤"""

    def __init__(self, message: str):
        """初始化 LLM 錯誤"""
        super().__init__(message, code="LLM_SERVICE_UNAVAILABLE")


class DatabaseError(ApplicationError):
    """資料庫操作錯誤"""

    def __init__(self, message: str):
        """初始化資料庫錯誤"""
        super().__init__(message, code="DATABASE_ERROR")


class NotFoundError(ApplicationError):
    """資源不存在錯誤"""

    def __init__(self, resource_type: str, resource_id: str):
        """
        初始化未找到錯誤

        Args:
            resource_type: 資源類型（例如 'conversation'）
            resource_id: 資源識別碼
        """
        message = f"找不到指定的{resource_type}"
        super().__init__(message, code=f"{resource_type.upper()}_NOT_FOUND")


class ConversationNotFoundError(NotFoundError):
    """對話不存在"""

    def __init__(self, conversation_id: str):
        super().__init__("對話", conversation_id)


class MemoryNotFoundError(NotFoundError):
    """記憶不存在"""

    def __init__(self, memory_id: str):
        super().__init__("記憶", memory_id)


class RateLimitError(ApplicationError):
    """速率限制錯誤"""

    def __init__(self, retry_after_seconds: int = 60):
        """
        初始化速率限制錯誤

        Args:
            retry_after_seconds: 建議重試等待秒數
        """
        self.retry_after = retry_after_seconds
        message = f"已超過速率限制，請稍後再試"
        super().__init__(message, code="RATE_LIMIT_EXCEEDED")
