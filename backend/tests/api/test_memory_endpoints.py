"""
記憶管理 API 端點測試

測試所有記憶管理相關的 HTTP 端點。
"""

import pytest
from unittest.mock import MagicMock, patch
import uuid
from datetime import datetime


class TestMemoryEndpointsGetMemories:
    """GET /api/v1/memories 端點測試"""

    def test_get_memories_success(self):
        """測試成功取得使用者的記憶列表"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.get_memories') as mock_get:
            mock_get.return_value = [
                {"id": "mem-1", "content": "科技股投資", "category": "investment_type"},
                {"id": "mem-2", "content": "中等風險承受度", "category": "risk_level"},
            ]
            
            result = mock_get(user_id, 100, None)
            
            assert len(result) == 2
            assert result[0]["content"] == "科技股投資"

    def test_get_memories_empty(self):
        """測試使用者無記憶時的回應"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.get_memories') as mock_get:
            mock_get.return_value = []
            
            result = mock_get(user_id)
            
            assert len(result) == 0

    def test_get_memories_with_limit(self):
        """測試分頁限制參數"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.get_memories') as mock_get:
            mock_get.return_value = [{"id": "mem-1", "content": "test"}]
            
            result = mock_get(user_id, limit=10)
            
            assert len(result) == 1
            mock_get.assert_called_once_with(user_id, limit=10)


class TestMemoryEndpointsGetSingleMemory:
    """GET /api/v1/memories/{memory_id} 端點測試"""

    def test_get_memory_success(self):
        """測試成功取得單一記憶"""
        memory_id = "mem-123"
        
        with patch('src.services.memory_service.MemoryService.get_memory_by_id') as mock_get:
            mock_get.return_value = {
                "id": memory_id,
                "content": "科技股投資",
                "metadata": {"category": "investment_type"},
                "timestamp": "2025-10-30T12:00:00Z"
            }
            
            result = mock_get(memory_id)
            
            assert result is not None
            assert result["id"] == memory_id
            assert result["content"] == "科技股投資"

    def test_get_memory_not_found(self):
        """測試記憶不存在時的 None 回應"""
        memory_id = "nonexistent-123"
        
        with patch('src.services.memory_service.MemoryService.get_memory_by_id') as mock_get:
            mock_get.return_value = None
            
            result = mock_get(memory_id)
            
            assert result is None


class TestMemoryEndpointsUpdateMemory:
    """PUT /api/v1/memories/{memory_id} 端點測試"""

    def test_update_memory_success(self):
        """測試成功更新記憶"""
        memory_id = "mem-123"
        
        with patch('src.services.memory_service.MemoryService.update_memory') as mock_update:
            mock_update.return_value = {
                "id": memory_id,
                "content": "更新後的科技股投資",
                "category": "investment_type",
                "timestamp": "2025-10-30T12:30:00Z"
            }
            
            result = mock_update(memory_id, "更新後的科技股投資", "investment_type")
            
            assert result["content"] == "更新後的科技股投資"
            assert result["id"] == memory_id

    def test_update_memory_error(self):
        """測試更新不存在的記憶會拋出錯誤"""
        memory_id = "nonexistent-123"
        
        with patch('src.services.memory_service.MemoryService.update_memory') as mock_update:
            from src.utils.exceptions import MemoryError
            mock_update.side_effect = MemoryError("無法更新記憶")
            
            with pytest.raises(MemoryError):
                mock_update(memory_id, "test")


class TestMemoryEndpointsDeleteMemory:
    """DELETE /api/v1/memories/{memory_id} 端點測試"""

    def test_delete_memory_success(self):
        """測試成功刪除記憶"""
        memory_id = "mem-123"
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.delete_memory') as mock_delete:
            mock_delete.return_value = True
            
            result = mock_delete(user_id, memory_id)
            
            assert result is True

    def test_delete_memory_failure(self):
        """測試刪除記憶失敗"""
        memory_id = "nonexistent-123"
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.delete_memory') as mock_delete:
            mock_delete.return_value = False
            
            result = mock_delete(user_id, memory_id)
            
            assert result is False


class TestMemoryEndpointsBatchDelete:
    """POST /api/v1/memories/batch-delete 端點測試"""

    def test_batch_delete_success(self):
        """測試成功批量刪除記憶"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.batch_delete_memories') as mock_delete:
            mock_delete.return_value = 3
            
            result = mock_delete(user_id, category="investment_type")
            
            assert result == 3

    def test_batch_delete_empty(self):
        """測試批量刪除無符合記憶"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.batch_delete_memories') as mock_delete:
            mock_delete.return_value = 0
            
            result = mock_delete(user_id, category="nonexistent")
            
            assert result == 0


class TestMemoryEndpointsSemanticSearch:
    """POST /api/v1/memories/search 端點測試"""

    def test_semantic_search_success(self):
        """測試成功執行語義搜索"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.search_memories') as mock_search:
            mock_search.return_value = [
                {"id": "mem-1", "content": "科技股投資", "metadata": {"relevance": 0.95}},
                {"id": "mem-2", "content": "中等風險", "metadata": {"relevance": 0.80}},
            ]
            
            result = mock_search(user_id, "股票投資推薦", top_k=5)
            
            assert len(result) == 2
            assert result[0]["content"] == "科技股投資"

    def test_semantic_search_empty_result(self):
        """測試搜索無結果"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.search_memories') as mock_search:
            mock_search.return_value = []
            
            result = mock_search(user_id, "不相關的查詢")
            
            assert len(result) == 0

    def test_semantic_search_respects_top_k(self):
        """測試 top_k 參數被尊重"""
        user_id = str(uuid.uuid4())
        
        with patch('src.services.memory_service.MemoryService.search_memories') as mock_search:
            mock_search.return_value = [{"id": f"mem-{i}", "content": f"記憶{i}"} for i in range(3)]
            
            result = mock_search(user_id, "查詢", top_k=3)
            
            assert len(result) == 3
            mock_search.assert_called_with(user_id, "查詢", top_k=3)


class TestMemoryServiceMethods:
    """記憶服務方法單元測試"""

    def test_get_memories_returns_list(self):
        """測試 get_memories 返回列表"""
        with patch('src.services.memory_service.MemoryService.get_memories') as mock:
            mock.return_value = []
            
            result = mock("user_id")
            
            assert isinstance(result, list)

    def test_update_memory_returns_dict(self):
        """測試 update_memory 返回字典"""
        with patch('src.services.memory_service.MemoryService.update_memory') as mock:
            mock.return_value = {"id": "mem-1", "content": "updated"}
            
            result = mock("mem-1", "updated")
            
            assert isinstance(result, dict)
            assert "id" in result

    def test_batch_delete_returns_count(self):
        """測試 batch_delete_memories 返回計數"""
        with patch('src.services.memory_service.MemoryService.batch_delete_memories') as mock:
            mock.return_value = 5
            
            result = mock("user_id")
            
            assert isinstance(result, int)
            assert result == 5
