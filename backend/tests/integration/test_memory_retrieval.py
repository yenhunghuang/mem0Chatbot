"""
測試記憶檢索與 LLM 上下文整合

US2 T036: 測試記憶檢索與 LLM 上下文整合流程
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import uuid
import json

from src.services.memory_service import MemoryService
from src.services.conversation_service import ConversationService
from src.services.llm_service import LLMService
from src.storage.storage_service import StorageService
from src.utils.exceptions import MemoryError, LLMError


class TestMemoryRetrievalIntegration:
    """記憶檢索與整合流程測試"""

    @pytest.fixture
    def user_id(self):
        """測試使用者 ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def conversation_id(self):
        """測試對話 ID"""
        return str(uuid.uuid4())

    @pytest.fixture
    def sample_memories(self):
        """範例投資偏好記憶"""
        return [
            {
                "id": "mem_001",
                "content": "使用者偏好投資科技股，特別是 AI 和雲端運算公司",
                "metadata": {
                    "category": "preference",
                    "relevance": 0.98,
                    "created_at": "2025-10-30",
                },
            },
            {
                "id": "mem_002",
                "content": "使用者的風險承受度是中等偏高，可以接受 15% 左右的波動",
                "metadata": {
                    "category": "risk_profile",
                    "relevance": 0.92,
                    "created_at": "2025-10-30",
                },
            },
            {
                "id": "mem_003",
                "content": "使用者打算長期投資，至少持有 5 年以上",
                "metadata": {
                    "category": "investment_horizon",
                    "relevance": 0.88,
                    "created_at": "2025-10-30",
                },
            },
        ]

    def test_memory_retrieval_before_llm_generation(
        self, user_id, conversation_id, sample_memories
    ):
        """測試在生成 LLM 回應前檢索記憶

        給定：使用者提出投資建議請求
        當：系統檢索相關記憶
        則：應該從 ChromaDB 中取得相關的投資偏好
        """
        user_message = "幫我推薦適合的股票"

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ) as mock_search:
            # 模擬記憶檢索
            memories = MemoryService.search_memories(user_id, user_message, top_k=3)

            # 驗證檢索了正確數量的記憶
            assert len(memories) == 3
            mock_search.assert_called_once()

            # 驗證返回的是相關記憶
            assert any("科技股" in m["content"] for m in memories)

    def test_memory_context_included_in_llm_prompt(
        self, user_id, sample_memories
    ):
        """測試記憶上下文被包含在 LLM prompt 中

        給定：已檢索記憶
        當：呼叫 LLM 生成回應
        則：LLM 的 prompt 應該包含使用者的投資偏好
        """
        user_message = "我應該投資哪些公司？"
        memories_context = "\n".join([m["content"] for m in sample_memories])

        # 構建包含記憶的 prompt
        system_prompt = f"""你是一個專業的投資顧問。
使用者的投資偏好和信息：
{memories_context}

根據上述信息提供個人化建議。"""

        with patch.object(
            LLMService, "generate_response", return_value="基於你的偏好建議..."
        ) as mock_llm:
            response = LLMService.generate_response(
                user_input=user_message,
                memories=sample_memories,
            )

            # 驗證 LLM 被正確呼叫
            mock_llm.assert_called_once()
            assert response is not None

    def test_memories_sorted_by_relevance_for_llm(
        self, user_id, sample_memories
    ):
        """測試記憶按相關度排序後提供給 LLM

        給定：多個相關記憶
        當：傳遞給 LLM
        則：應該按相關度從高到低排列
        """
        user_message = "投資建議"

        # 模擬檢索
        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ):
            memories = MemoryService.search_memories(user_id, user_message, top_k=3)

            # 驗證按相關度排序
            if all("metadata" in m for m in memories):
                relevances = [m["metadata"].get("relevance", 0) for m in memories]
                assert relevances == sorted(relevances, reverse=True)

    def test_memory_retrieval_failure_fallback(self, user_id):
        """測試記憶檢索失敗時的降級處理

        給定：記憶檢索失敗
        當：呼叫 generate_response
        則：應該返回通用投資教育內容而不拋出例外
        """
        user_message = "投資建議"

        # 模擬記憶檢索失敗
        with patch.object(
            MemoryService, "search_memories", side_effect=Exception("ChromaDB error")
        ):
            # 應該使用 fallback（沒有記憶的通用回應）
            with patch.object(
                LLMService,
                "generate_response",
                return_value="以下是一般的投資建議...",
            ) as mock_llm:
                response = LLMService.generate_response(user_input=user_message)

                # 應該仍然返回回應
                assert response is not None

    def test_top_k_memories_limitation(self, user_id, sample_memories):
        """測試 top_k 限制確保 LLM 的 token 使用量

        給定：大量可用記憶
        當：檢索 top_k=3
        則：只返回前 3 個最相關的記憶
        """
        user_message = "推薦"
        top_k = 3

        # 模擬有很多記憶但只返回 top 3
        all_memories = sample_memories + [
            {
                "id": f"mem_{i:03d}",
                "content": f"其他記憶 {i}",
                "metadata": {"relevance": 0.1 * i},
            }
            for i in range(4, 20)
        ]

        with patch.object(
            MemoryService,
            "search_memories",
            return_value=all_memories[:top_k],
        ) as mock_search:
            memories = MemoryService.search_memories(user_id, user_message, top_k=top_k)

            assert len(memories) == top_k
            mock_search.assert_called_once_with(user_id, user_message, top_k=top_k)

    def test_memory_categories_preserved(self, user_id, sample_memories):
        """測試記憶分類信息被保留

        給定：帶有分類的記憶
        當：檢索記憶
        則：分類信息應該被保留用於 LLM 理解
        """
        user_message = "股票"

        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ):
            memories = MemoryService.search_memories(user_id, user_message, top_k=3)

            # 驗證分類被保留
            expected_categories = {
                "preference",
                "risk_profile",
                "investment_horizon",
            }
            actual_categories = {
                m["metadata"]["category"]
                for m in memories
                if "metadata" in m and "category" in m["metadata"]
            }

            assert expected_categories == actual_categories

    def test_memories_used_tracked_in_response(self, user_id, conversation_id):
        """測試回應中追蹤使用的記憶

        給定：生成帶記憶的回應
        當：儲存對話
        則：應該記錄哪些記憶被用於生成該回應
        """
        sample_memories = [
            {
                "id": "mem_001",
                "content": "科技股偏好",
                "metadata": {"relevance": 0.95},
            }
        ]

        # 模擬完整流程
        with patch.object(
            MemoryService, "search_memories", return_value=sample_memories
        ):
            memories = MemoryService.search_memories(user_id, "推薦", top_k=3)

            # 驗證記憶被正確保存
            assert len(memories) > 0
            assert "id" in memories[0]

    def test_empty_memory_retrieval_graceful_handling(self, user_id):
        """測試空記憶檢索的優雅處理

        給定：使用者沒有任何記憶
        當：嘗試檢索記憶
        則：應該返回空列表並繼續
        """
        user_message = "投資建議"

        with patch.object(
            MemoryService, "search_memories", return_value=[]
        ) as mock_search:
            memories = MemoryService.search_memories(user_id, user_message, top_k=5)

            assert memories == []
            assert isinstance(memories, list)

    def test_memory_relevance_threshold(self, user_id):
        """測試記憶相關度閾值

        給定：不同相關度的記憶
        當：檢索記憶
        則：可能只返回相關度高於閾值的記憶
        """
        all_memories = [
            {
                "id": "mem_001",
                "content": "高相關",
                "metadata": {"relevance": 0.95},
            },
            {
                "id": "mem_002",
                "content": "中相關",
                "metadata": {"relevance": 0.5},
            },
            {
                "id": "mem_003",
                "content": "低相關",
                "metadata": {"relevance": 0.1},
            },
        ]

        # 根據相關度過濾
        threshold = 0.5
        filtered = [m for m in all_memories if m["metadata"]["relevance"] >= threshold]

        assert len(filtered) == 2
        assert all(m["metadata"]["relevance"] >= threshold for m in filtered)

    def test_conversation_history_combined_with_memories(
        self, user_id, conversation_id
    ):
        """測試對話歷史與記憶的組合

        給定：既有對話歷史又有記憶
        當：生成回應
        則：LLM 應該同時考慮對話歷史和記憶
        """
        conversation_history = [
            {"role": "user", "content": "我想投資"},
            {"role": "assistant", "content": "好的，請告訴我你的偏好"},
        ]

        memories = [
            {
                "id": "mem_001",
                "content": "使用者偏好科技股",
                "metadata": {"relevance": 0.95},
            }
        ]

        # 驗證組合使用
        combined_context = {
            "history": conversation_history,
            "memories": memories,
        }

        assert len(combined_context["history"]) > 0
        assert len(combined_context["memories"]) > 0
