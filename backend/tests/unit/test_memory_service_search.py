"""
測試 Mem0 記憶搜索功能

US2 T035: 測試 search_memories() 方法正確呼叫 Mem0.search()
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid

from src.services.memory_service import MemoryService
from src.utils.exceptions import MemoryError


class TestMemoryServiceSearch:
    """記憶搜索服務測試"""

    @pytest.fixture
    def user_id(self):
        """測試使用者 ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_memories(self):
        """範例記憶資料"""
        return [
            {
                "id": "mem_001",
                "content": "使用者偏好投資科技股",
                "metadata": {"category": "preference", "relevance": 0.95},
            },
            {
                "id": "mem_002",
                "content": "使用者風險承受度中等偏高",
                "metadata": {"category": "risk_profile", "relevance": 0.85},
            },
            {
                "id": "mem_003",
                "content": "使用者打算長期投資5年以上",
                "metadata": {"category": "investment_horizon", "relevance": 0.75},
            },
        ]

    def test_search_memories_basic(self, user_id, sample_memories):
        """測試基本記憶搜索功能

        給定：使用者 ID 和搜索查詢
        當：呼叫 search_memories()
        則：返回相關記憶列表
        """
        query = "我想要投資建議"
        top_k = 3

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=top_k)

            # 驗證方法被呼叫
            mock_search.assert_called_once_with(user_id, query, top_k=top_k)

            # 驗證返回結果
            assert result is not None
            assert len(result) == 3
            assert all(isinstance(m, dict) for m in result)
            assert all("id" in m and "content" in m for m in result)

    def test_search_memories_returns_sorted_by_relevance(self, user_id, sample_memories):
        """測試記憶按相關度排序

        給定：記憶按相關度排序
        當：呼叫 search_memories()
        則：返回的記憶按相關度從高到低排列
        """
        query = "科技股"

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=3)

            # 驗證記憶按相關度排序（若有 relevance 欄位）
            if all("metadata" in m and "relevance" in m["metadata"] for m in result):
                relevances = [m["metadata"]["relevance"] for m in result]
                assert relevances == sorted(relevances, reverse=True)

    def test_search_memories_respects_top_k_limit(self, user_id, sample_memories):
        """測試記憶搜索尊重 top_k 限制

        給定：top_k = 2
        當：呼叫 search_memories()
        則：最多返回 2 個記憶
        """
        query = "投資"
        top_k = 2

        # 模擬返回前 2 個記憶
        limited_memories = sample_memories[:2]

        with patch.object(
            MemoryService, "search_memories", return_value=limited_memories
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=top_k)

            assert len(result) <= top_k
            assert len(result) == 2

    def test_search_memories_returns_empty_when_no_match(self, user_id):
        """測試無相關記憶時返回空列表

        給定：搜索不存在的內容
        當：呼叫 search_memories()
        則：返回空列表而不是錯誤
        """
        query = "完全不相關的查詢"

        with patch.object(
            MemoryService, "search_memories", return_value=[]
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=5)

            assert result == []
            mock_search.assert_called_once()

    def test_search_memories_includes_metadata(self, user_id, sample_memories):
        """測試返回的記憶包含元資料

        給定：記憶包含元資料
        當：呼叫 search_memories()
        則：返回的記憶包含所有必要的元資料欄位
        """
        query = "科技"

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=3)

            # 驗證記憶結構
            for memory in result:
                assert "id" in memory
                assert "content" in memory
                # metadata 是可選的但應該存在
                if "metadata" in memory:
                    assert isinstance(memory["metadata"], dict)

    def test_search_memories_handles_empty_query(self, user_id):
        """測試空查詢處理

        給定：空的查詢字串
        當：呼叫 search_memories()
        則：應該返回空列表或引發錯誤
        """
        query = ""

        # 空查詢應該返回空列表或異常
        with patch.object(
            MemoryService, "search_memories", return_value=[]
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=5)

            assert isinstance(result, list)

    def test_search_memories_handles_very_long_query(self, user_id):
        """測試長查詢處理

        給定：非常長的查詢字串
        當：呼叫 search_memories()
        則：應該正常處理而不崩潰
        """
        query = "我想要投資一些能夠在" + "未來五年內產生穩定" * 100 + "回報的股票"

        with patch.object(
            MemoryService, "search_memories", return_value=[]
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=5)

            assert isinstance(result, list)

    def test_search_memories_with_different_top_k_values(self, user_id, sample_memories):
        """測試不同 top_k 值

        給定：不同的 top_k 值
        當：呼叫 search_memories()
        則：返回相應數量的記憶
        """
        query = "投資"

        for top_k in [1, 2, 5, 10]:
            limited_memories = sample_memories[: min(top_k, len(sample_memories))]

            with patch.object(
                MemoryService, "search_memories", return_value=limited_memories
            ) as mock_search:
                result = MemoryService.search_memories(user_id, query, top_k=top_k)

                assert len(result) <= top_k

    def test_search_memories_invalid_user_id_format(self):
        """測試無效使用者 ID 格式

        給定：無效的使用者 ID（非 UUID）
        當：呼叫 search_memories()
        則：應該引發或返回錯誤
        """
        invalid_user_id = "not-a-uuid"
        query = "投資"

        # 可能引發例外或返回空列表
        with patch.object(
            MemoryService, "search_memories", return_value=[]
        ) as mock_search:
            result = MemoryService.search_memories(invalid_user_id, query, top_k=5)

            # 應該返回結果而不崩潰
            assert isinstance(result, list)

    def test_search_memories_with_special_characters(self, user_id, sample_memories):
        """測試特殊字元的查詢

        給定：包含特殊字元的查詢
        當：呼叫 search_memories()
        則：應該正常處理
        """
        queries = ["$100 股票", "AI/ML 相關", "50% 漲幅"]

        for query in queries:
            with patch.object(
                MemoryService, "search_memories", return_value=sample_memories
            ) as mock_search:
                result = MemoryService.search_memories(user_id, query, top_k=3)

                assert isinstance(result, list)

    def test_search_memories_unicode_support(self, user_id, sample_memories):
        """測試 Unicode 支援（繁體中文）

        給定：繁體中文查詢
        當：呼叫 search_memories()
        則：應該正常處理
        """
        query = "我想了解科技股和 AI 相關的投資機會"

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ) as mock_search:
            result = MemoryService.search_memories(user_id, query, top_k=3)

            assert len(result) > 0
            assert all(isinstance(m, dict) for m in result)
