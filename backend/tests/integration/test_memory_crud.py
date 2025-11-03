"""
記憶 CRUD 整合測試

測試完整的記憶建立、讀取、更新、刪除流程。
"""

import pytest
from unittest.mock import patch, MagicMock
from src.services.memory_service import MemoryService
from src.utils.exceptions import MemoryError


class TestMemoryCRUDFlow:
    """完整的記憶 CRUD 流程測試"""

    @pytest.fixture
    def mock_mem0(self):
        """模擬 Mem0 客戶端"""
        with patch("src.services.memory_service.Memory") as mock:
            yield mock

    def test_create_read_flow(self, mock_mem0):
        """測試建立後讀取記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        
        # 建立時的回應
        mock_client.add.return_value = {"memory_id": "mem_123"}
        
        # 讀取時的回應
        mock_client.search.return_value = {
            'results': [
                {"id": "mem_123", "content": "科技股投資", "metadata": {"category": "investment_type"}}
            ]
        }

        MemoryService.initialize()
        
        # 行動：建立記憶
        memory_id = MemoryService.add_memory("user_001", "科技股投資")
        assert memory_id == "mem_123"
        
        # 行動：讀取記憶
        memories = MemoryService.get_memories("user_001")
        
        # 斷言
        assert len(memories) > 0
        mock_client.add.assert_called_once()
        mock_client.search.assert_called()

    def test_create_update_delete_flow(self, mock_mem0):
        """測試完整的建立、更新、刪除流程"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        
        mock_client.add.return_value = {"memory_id": "mem_456"}
        mock_client.update.return_value = {
            "id": "mem_456",
            "content": "更新後的科技股投資"
        }
        mock_client.delete.return_value = True

        MemoryService.initialize()
        user_id = "user_002"
        
        # 行動：建立
        memory_id = MemoryService.add_memory(user_id, "科技股投資")
        assert memory_id == "mem_456"
        
        # 行動：更新
        updated = MemoryService.update_memory(memory_id, "更新後的科技股投資", "investment_type")
        assert updated["content"] == "更新後的科技股投資"
        
        # 行動：刪除
        deleted = MemoryService.delete_memory(user_id, memory_id)
        assert deleted is True
        
        # 斷言
        mock_client.add.assert_called_once()
        mock_client.update.assert_called_once()
        mock_client.delete.assert_called_once()

    def test_batch_delete_flow(self, mock_mem0):
        """測試批量刪除流程"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        
        # 先取得所有記憶
        mock_client.search.return_value = {
            'results': [
                {"id": "mem_1", "content": "科技股", "metadata": {"category": "investment_type"}},
                {"id": "mem_2", "content": "中等風險", "metadata": {"category": "investment_type"}},
                {"id": "mem_3", "content": "台灣市場", "metadata": {"category": "location"}},
            ]
        }
        mock_client.delete.return_value = True

        MemoryService.initialize()
        user_id = "user_003"
        
        # 行動：批量刪除特定類別
        deleted_count = MemoryService.batch_delete_memories(
            user_id,
            category="investment_type"
        )
        
        # 斷言
        assert deleted_count >= 0
        mock_client.search.assert_called()
        mock_client.delete.assert_called()

    def test_search_and_update_flow(self, mock_mem0):
        """測試搜索後更新記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        
        # 搜索回應
        mock_client.search.return_value = {
            'results': [
                {"id": "mem_search_1", "content": "股票投資", "metadata": {"relevance": 0.9}}
            ]
        }
        
        # 更新回應
        mock_client.update.return_value = {
            "id": "mem_search_1",
            "content": "更新的股票投資"
        }

        MemoryService.initialize()
        
        # 行動：搜索
        results = MemoryService.search_memories("user_004", "股票投資", top_k=5)
        
        # 斷言搜索結果
        assert len(results) > 0
        
        # 行動：更新找到的記憶
        if results:
            updated = MemoryService.update_memory(
                results[0].get("id"),
                "更新的股票投資"
            )
            assert updated["content"] == "更新的股票投資"


class TestMemoryCRUDEdgeCases:
    """記憶 CRUD 邊界情況測試"""

    @pytest.fixture
    def mock_mem0(self):
        """模擬 Mem0 客戶端"""
        with patch("src.services.memory_service.Memory") as mock:
            yield mock

    def test_update_nonexistent_memory(self, mock_mem0):
        """測試更新不存在的記憶"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.update.side_effect = Exception("記憶不存在")

        MemoryService.initialize()
        
        # 行動 & 斷言
        with pytest.raises(MemoryError):
            MemoryService.update_memory("nonexistent_id", "content")

    def test_delete_with_empty_user_id(self, mock_mem0):
        """測試使用空 user_id 刪除"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        # 當 user_id 為空時，Mem0 API 會失敗並返回 False
        mock_client.delete.side_effect = Exception("Invalid user_id")

        MemoryService.initialize()
        
        # 行動
        result = MemoryService.delete_memory("", "mem_123")
        
        # 斷言 - 應該返回 False 因為刪除失敗
        assert result is False

    def test_batch_delete_empty_category(self, mock_mem0):
        """測試批量刪除時不指定類別"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        
        mock_client.search.return_value = {
            'results': [
                {"id": "mem_1", "content": "記憶1"},
                {"id": "mem_2", "content": "記憶2"},
            ]
        }
        mock_client.delete.return_value = True

        MemoryService.initialize()
        
        # 行動
        deleted_count = MemoryService.batch_delete_memories("user_005")
        
        # 斷言
        assert deleted_count >= 0

    def test_get_memories_returns_empty_list_on_error(self, mock_mem0):
        """測試錯誤時 get_memories 返回空列表"""
        # 安排
        mock_client = MagicMock()
        mock_mem0.from_config.return_value = mock_client
        mock_client.search.side_effect = Exception("搜索失敗")

        MemoryService.initialize()
        
        # 行動
        memories = MemoryService.get_memories("user_006")
        
        # 斷言
        assert memories == []
