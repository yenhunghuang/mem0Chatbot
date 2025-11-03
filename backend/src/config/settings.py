"""
設定管理模組：使用 pydantic-settings 載入環境變數

此模組負責管理應用程式的所有設定，包括 API 密鑰、資料庫連線、
以及各種應用程式行為參數。
"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings
from typing import List, Optional


class Settings(BaseSettings):
    """應用程式設定類別"""

    # Google API Configuration
    google_api_key: str
    mem0_llm_model: str = "gemini-2.0-flash"
    mem0_embedder_model: str = "text-embedding-004"

    # Database Configuration
    database_url: str = "sqlite:///./data/app.db"
    chroma_path: str = "./data/chroma"

    # Application Settings
    app_env: str = "development"
    debug: bool = True
    log_level: str = "INFO"

    # CORS Configuration
    cors_origins: List[str] = [
        "http://localhost:8000",
        "http://12-7.0.0.1:8000",
        "http://localhost:3000",
    ]

    # Rate Limiting
    rate_limit_chat_per_minute: int = 10
    rate_limit_general_per_minute: int = 50

    # Performance
    response_timeout_seconds: int = 30
    memory_search_top_k: int = 5
    memory_retrieval_top_k: int = 5  # Number of memories to retrieve
    conversation_context_window: int = 10  # Number of recent messages to include in context

    # Memory Management
    memory_ttl_days: int = 30
    memory_max_per_user: int = 1000

    model_config = ConfigDict(env_file=".env", case_sensitive=False)


# 全域設定實例
settings = Settings()  # type: ignore
