"""
記憶服務單元測試

測試 MemoryService 的記憶管理功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List

from backend.src.services.memory_service import MemoryService
from backend.src.utils.exceptions import MemoryError


class TestMemoryServiceAddMemory:
    """測試 add_memory() 方法"""

    @pytest.fixture
    def mock_mem0(self):
        """模擬 Mem0 客戶端"""
        with patch("backend.src.services.memory_service.Memory") as mock:
            yield mock

    def test_add_memory_success(self, mock_mem0):
        """測試成功新增記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.add.return_value = {"memory_id": "mem_123"}

        MemoryService.initialize()
        user_id = "user_001"
        content = "我偏好投資科技股"

        # 行動
        memory_id = MemoryService.add_memory(user_id, content)

        # 斷言
        assert memory_id == "mem_123"
        mock_client.add.assert_called_once()
        call_args = mock_client.add.call_args
        assert call_args[1]["user_id"] == user_id

    def test_add_memory_with_metadata(self, mock_mem0):
        """測試新增記憶並指定中繼資料"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.add.return_value = {"memory_id": "mem_456"}

        MemoryService.initialize()
        user_id = "user_002"
        content = "我的風險承受度是中等"
        metadata = {"category": "risk_profile"}

        # 行動
        memory_id = MemoryService.add_memory(user_id, content, metadata)

        # 斷言
        assert memory_id == "mem_456"
        call_args = mock_client.add.call_args
        assert call_args[1]["metadata"]["category"] == "risk_profile"

    def test_add_memory_failure(self, mock_mem0):
        """測試新增記憶失敗時拋出例外"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.add.side_effect = Exception("Mem0 API 錯誤")

        MemoryService.initialize()

        # 行動 & 斷言
        with pytest.raises(MemoryError):
            MemoryService.add_memory("user_003", "記憶內容")

    def test_add_memory_no_memory_id_returned(self, mock_mem0):
        """測試 Mem0 未返回 memory_id 時生成 UUID"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.add.return_value = {}  # 未返回 memory_id

        MemoryService.initialize()

        # 行動
        memory_id = MemoryService.add_memory("user_004", "測試記憶")

        # 斷言
        assert memory_id is not None
        assert isinstance(memory_id, str)
        assert len(memory_id) > 0


class TestMemoryServiceSearchMemories:
    """測試 search_memories() 方法"""

    @pytest.fixture
    def mock_mem0(self):
        """模擬 Mem0 客戶端"""
        with patch("backend.src.services.memory_service.Memory") as mock:
            yield mock

    def test_search_memories_success(self, mock_mem0):
        """測試成功搜索記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.search.return_value = [
            {"text": "科技股投資偏好"},
            {"text": "中等風險承受度"},
        ]

        MemoryService.initialize()
        user_id = "user_005"
        query = "投資偏好"

        # 行動
        results = MemoryService.search_memories(user_id, query, top_k=2)

        # 斷言
        assert len(results) == 2
        assert "科技股" in results[0]
        mock_client.search.assert_called_once_with(
            query=query,
            user_id=user_id,
            limit=2,
        )

    def test_search_memories_no_results(self, mock_mem0):
        """測試搜索無結果"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.search.return_value = []

        MemoryService.initialize()

        # 行動
        results = MemoryService.search_memories("user_006", "不存在的查詢")

        # 斷言
        assert len(results) == 0

    def test_search_memories_failure_returns_empty_list(self, mock_mem0):
        """測試搜索失敗時返回空列表（降級）"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.search.side_effect = Exception("搜索失敗")

        MemoryService.initialize()

        # 行動
        results = MemoryService.search_memories("user_007", "查詢")

        # 斷言
        assert results == []

    def test_search_memories_custom_top_k(self, mock_mem0):
        """測試自訂 top_k 參數"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.search.return_value = [{"text": f"記憶{i}"} for i in range(10)]

        MemoryService.initialize()

        # 行動
        results = MemoryService.search_memories("user_008", "查詢", top_k=10)

        # 斷言
        assert len(results) == 10
        call_args = mock_client.search.call_args
        assert call_args[1]["limit"] == 10


class TestMemoryServiceDeleteMemory:
    """測試 delete_memory() 方法"""

    @pytest.fixture
    def mock_mem0(self):
        """模擬 Mem0 客戶端"""
        with patch("backend.src.services.memory_service.Memory") as mock:
            yield mock

    def test_delete_memory_success(self, mock_mem0):
        """測試成功刪除記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client

        MemoryService.initialize()

        # 行動
        result = MemoryService.delete_memory("user_009", "mem_789")

        # 斷言
        assert result is True
        mock_client.delete.assert_called_once_with(
            memory_id="mem_789",
            user_id="user_009",
        )

    def test_delete_memory_failure(self, mock_mem0):
        """測試刪除記憶失敗"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.delete.side_effect = Exception("刪除失敗")

        MemoryService.initialize()

        # 行動
        result = MemoryService.delete_memory("user_010", "mem_999")

        # 斷言
        assert result is False


class TestMemoryServiceInitialization:
    """測試 MemoryService 初始化"""

    def test_initialize_success(self):
        """測試成功初始化"""
        with patch("backend.src.services.memory_service.Memory") as mock:
            mock.from_config.return_value = MagicMock()

            # 應不拋出異常
            MemoryService.initialize()
            assert MemoryService._mem0_client is not None

    def test_initialize_failure(self):
        """測試初始化失敗"""
        with patch("backend.src.services.memory_service.Memory") as mock:
            mock.from_config.side_effect = Exception("初始化失敗")

            with pytest.raises(MemoryError):
                MemoryService.initialize()

    def test_initialize_mem0_not_installed(self):
        """測試 Mem0 未安裝時"""
        with patch("backend.src.services.memory_service.Memory", None):
            with pytest.raises(MemoryError, match="Mem0 庫未安裝"):
                MemoryService.initialize()
