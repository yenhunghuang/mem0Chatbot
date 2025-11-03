"""
Pytest 配置和共享夾具

定義所有測試使用的共享夾具和配置。
"""
import sys
import os
# HACK: 將 'backend' 目錄加入 sys.path
# 這能解決 `ModuleNotFoundError: No module named 'src'` 的問題
# 讓測試在執行時能正確找到 src 模組
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
import sqlite3
import tempfile
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

# 在導入 settings 前設置測試環境變數
if not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = "test-key"

import pytest
from fastapi.testclient import TestClient

from src.config import settings
from src.main import app
from src.storage.database import DatabaseManager
from src.services.embedding_service import EmbeddingService
from src.services.llm_service import LLMService
from src.services.memory_service import MemoryService


# ============================================================================
# 設置和清理
# ============================================================================


@pytest.fixture(scope="session")
def test_db_path() -> Generator[str, None, None]:
    """
    取得測試資料庫路徑

    Yields:
        str: 測試資料庫的臨時路徑
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield os.path.join(tmpdir, "test.db")


@pytest.fixture(autouse=True)
def reset_services():
    """
    重置所有服務單例

    在每個測試前重置服務單例，確保測試隔離。
    """
    # 重置前
    yield
    # 重置後
    DatabaseManager._db = None
    EmbeddingService._client = None
    LLMService._model = None
    MemoryService._mem0_client = None


# ============================================================================
# 資料庫夾具
# ============================================================================


@pytest.fixture
def test_db(test_db_path: str) -> Generator[str, None, None]:
    """
    初始化測試資料庫

    Args:
        test_db_path: 測試資料庫路徑

    Yields:
        str: 初始化的測試資料庫路徑
    """
    # 初始化資料庫
    db_url = f"sqlite:///{test_db_path}"
    DatabaseManager.initialize(db_url)

    yield db_url

    # 清理
    DatabaseManager.close()
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def db_connection(test_db: str) -> Generator[sqlite3.Connection, None, None]:
    """
    取得測試資料庫連線

    Args:
        test_db: 測試資料庫 URL

    Yields:
        sqlite3.Connection: 資料庫連線
    """
    # 提取資料庫路徑
    db_path = test_db.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    yield conn

    conn.close()


# ============================================================================
# 服務模擬夾具
# ============================================================================


@pytest.fixture
def mock_embedding_service() -> MagicMock:
    """
    模擬嵌入服務

    Returns:
        MagicMock: 模擬的嵌入服務
    """
    mock = MagicMock()
    mock.embed_text.return_value = [0.1] * 768  # 模擬嵌入向量
    mock.embed_batch.return_value = [[0.1] * 768] * 5
    return mock


@pytest.fixture
def mock_llm_service() -> MagicMock:
    """
    模擬 LLM 服務

    Returns:
        MagicMock: 模擬的 LLM 服務
    """
    mock = MagicMock()
    mock.generate_response.return_value = "根據您的風險承受度，我建議投資穩定收益的基金。"
    mock.extract_preferences.return_value = "低風險承受度"
    return mock


@pytest.fixture
def mock_memory_service() -> MagicMock:
    """
    模擬記憶服務

    Returns:
        MagicMock: 模擬的記憶服務
    """
    mock = MagicMock()
    mock.add_memory.return_value = "mem_123"
    mock.search_memories.return_value = ["使用者偏好低風險投資", "月收入 50000 元"]
    mock.get_latest_memories.return_value = ["最近查詢科技股", "對房產投資感興趣"]
    mock.delete_memory.return_value = True
    return mock


# ============================================================================
# 客戶端夾具
# ============================================================================


@pytest.fixture
def client() -> TestClient:
    """
    建立 FastAPI 測試客戶端

    Returns:
        TestClient: FastAPI 測試客戶端
    """
    return TestClient(app)


@pytest.fixture
def authenticated_client(client: TestClient) -> TestClient:
    """
    建立已認證的 FastAPI 測試客戶端

    Args:
        client: 基礎測試客戶端

    Returns:
        TestClient: 已認證的測試客戶端
    """
    # 設置預設標頭（模擬認證）
    client.headers = {
        "Authorization": "Bearer test_token",
        "User-ID": "test_user_123",
    }
    return client


# ============================================================================
# 資料夾具
# ============================================================================


@pytest.fixture
def sample_user_id() -> str:
    """
    取得示例使用者 ID

    Returns:
        str: 示例使用者 ID
    """
    return "user_test_12345"


@pytest.fixture
def sample_conversation_id() -> str:
    """
    取得示例對話 ID

    Returns:
        str: 示例對話 ID
    """
    return "conv_test_12345"


@pytest.fixture
def sample_message() -> dict:
    """
    取得示例訊息

    Returns:
        dict: 示例訊息資料
    """
    return {
        "role": "user",
        "content": "我想投資科技股，但擔心風險太高。您有什麼建議嗎？",
    }


@pytest.fixture
def sample_memories() -> list:
    """
    取得示例記憶列表

    Returns:
        list: 示例記憶列表
    """
    return [
        "使用者的風險承受度為低至中",
        "對科技股有興趣",
        "月可用投資金額為 10000 元",
    ]


@pytest.fixture
def sample_conversation_history() -> list:
    """
    取得示例對話歷史

    Returns:
        list: 示例對話歷史
    """
    return [
        {
            "role": "user",
            "content": "你好，我是新使用者",
        },
        {
            "role": "assistant",
            "content": "歡迎！我是您的投資顧問助理，很高興認識您。",
        },
    ]


# ============================================================================
# 配置夾具
# ============================================================================


@pytest.fixture
def test_settings():
    """
    取得測試配置

    Returns:
        settings: 測試配置物件
    """
    # 設置測試環境變數
    os.environ["APP_ENV"] = "test"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["DATABASE_URL"] = "sqlite:///./test.db"
    return settings


# ============================================================================
# 模擬補丁夾具
# ============================================================================


@pytest.fixture
def patch_google_api():
    """
    模擬 Google API 呼叫

    Yields:
        None
    """
    with patch("src.services.embedding_service.genai") as mock_genai:
        mock_genai.embed_content.return_value = {
            "embedding": [0.1] * 768,
        }
        yield mock_genai


@pytest.fixture
def patch_mem0():
    """
    模擬 Mem0 客戶端

    Yields:
        None
    """
    with patch("src.services.memory_service.Memory") as mock_memory:
        mock_instance = MagicMock()
        mock_memory.from_config.return_value = mock_instance
        mock_instance.add.return_value = {"memory_id": "mem_123"}
        mock_instance.search.return_value = [
            {"text": "使用者偏好低風險投資"},
        ]
        yield mock_memory


# ============================================================================
# 標記定義
# ============================================================================


def pytest_configure(config):
    """
    Pytest 配置鉤子

    定義自訂標記。
    """
    config.addinivalue_line("markers", "unit: 單元測試")
    config.addinivalue_line("markers", "integration: 整合測試")
    config.addinivalue_line("markers", "api: API 測試")
    config.addinivalue_line("markers", "slow: 慢速測試")
