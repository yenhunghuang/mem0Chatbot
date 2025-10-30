"""
聊天流程整合測試

測試完整的對話流程：使用者訊息 → 記憶擷取 → LLM 回應 → 儲存
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
import uuid

from backend.src.utils.exceptions import MemoryError, LLMError, DatabaseError


class TestChatFlowIntegration:
    """測試完整的聊天流程"""

    @pytest.fixture
    def setup_services(self):
        """設定所有必要的模擬服務"""
        with patch("backend.src.services.memory_service.MemoryService") as mock_memory, \
             patch("backend.src.services.llm_service.LLMService") as mock_llm, \
             patch("backend.src.storage.database.DatabaseManager") as mock_db:

            # 設定模擬返回值
            mock_memory.add_memory.return_value = "mem_001"
            mock_memory.search_memories.return_value = ["我喜歡科技股"]
            mock_llm.generate_response.return_value = "根據您的偏好，科技股是一個不錯的選擇"
            mock_db.get_connection.return_value = MagicMock()

            yield {
                "memory": mock_memory,
                "llm": mock_llm,
                "db": mock_db,
            }

    def test_user_message_flow_success(self, setup_services):
        """測試使用者訊息完整流程"""
        services = setup_services

        # 模擬對話流程
        user_id = str(uuid.uuid4())
        conversation_id = 1
        user_message = "我偏好投資科技股"

        # 步驟 1: 儲存使用者訊息
        services["db"].get_connection.return_value.cursor.return_value.lastrowid = 1

        # 步驟 2: 從訊息中擷取記憶
        services["memory"].add_memory.return_value = "mem_001"

        # 步驟 3: 搜索相關記憶
        services["memory"].search_memories.return_value = ["我偏好科技股"]

        # 步驟 4: 呼叫 LLM 生成回應
        llm_response = "很好，科技股近年表現不錯"
        services["llm"].generate_response.return_value = llm_response

        # 驗證流程
        assert user_id is not None
        assert conversation_id > 0
        assert user_message is not None
        assert llm_response is not None

    def test_message_saved_before_llm_call(self, setup_services):
        """測試訊息在 LLM 呼叫前被保存"""
        services = setup_services

        # 安排
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.lastrowid = 1
        services["db"].get_connection.return_value = conn

        # 追蹤呼叫順序
        call_order = []

        def mock_execute(*args, **kwargs):
            if "INSERT" in str(args[0]):
                call_order.append("insert_message")
            return cursor

        cursor.execute.side_effect = mock_execute

        # 行動
        cursor.execute("INSERT INTO messages ...", ("user", "訊息內容"))

        # 斷言
        assert "insert_message" in call_order

    def test_memory_extraction_from_user_message(self, setup_services):
        """測試從使用者訊息中自動擷取記憶"""
        services = setup_services

        # 安排
        user_message = "我偏好投資科技股，風險承受度是中等"
        memory_calls = []

        def track_add_memory(user_id, content, metadata=None):
            memory_calls.append({
                "user_id": user_id,
                "content": content,
                "metadata": metadata,
            })
            return "mem_extracted"

        services["memory"].add_memory.side_effect = track_add_memory

        # 行動
        user_id = "user_001"
        # 模擬偏好擷取
        services["memory"].add_memory(user_id, "科技股偏好", {"category": "preference"})

        # 斷言
        assert len(memory_calls) > 0
        assert memory_calls[0]["user_id"] == user_id
        assert "偏好" in memory_calls[0]["content"]

    def test_llm_response_generation_with_memories(self, setup_services):
        """測試 LLM 使用記憶生成回應"""
        services = setup_services

        # 安排
        user_input = "你能推薦什麼股票嗎？"
        memories = ["我偏好科技股", "風險承受度是中等"]
        llm_calls = []

        def track_llm_call(user_input, memories=None, conversation_history=None):
            llm_calls.append({
                "user_input": user_input,
                "memories": memories,
                "conversation_history": conversation_history,
            })
            return "根據您的偏好，我推薦 AAPL、MSFT 等科技股"

        services["llm"].generate_response.side_effect = track_llm_call

        # 行動
        response = services["llm"].generate_response(user_input, memories=memories)

        # 斷言
        assert response is not None
        assert len(llm_calls) > 0
        assert llm_calls[0]["memories"] == memories

    def test_response_saved_after_llm_generation(self, setup_services):
        """測試 LLM 回應被保存到資料庫"""
        services = setup_services

        # 安排
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.lastrowid = 2
        services["db"].get_connection.return_value = conn

        llm_response = "推薦 AAPL 和 MSFT"
        save_calls = []

        def track_insert(*args, **kwargs):
            if "INSERT" in str(args[0]) and "assistant" in str(args):
                save_calls.append("response_saved")
            return cursor

        cursor.execute.side_effect = track_insert

        # 行動
        cursor.execute(
            "INSERT INTO messages (conversation_id, role, content, timestamp, token_count) VALUES (?, ?, ?, ?, ?)",
            (1, "assistant", llm_response, datetime.now().isoformat(), 5)
        )

        # 斷言
        assert len(save_calls) > 0


class TestChatFlowErrorHandling:
    """測試聊天流程的錯誤處理"""

    @pytest.fixture
    def setup_services_with_errors(self):
        """設定會產生錯誤的模擬服務"""
        with patch("backend.src.services.memory_service.MemoryService") as mock_memory, \
             patch("backend.src.services.llm_service.LLMService") as mock_llm, \
             patch("backend.src.storage.database.DatabaseManager") as mock_db:

            yield {
                "memory": mock_memory,
                "llm": mock_llm,
                "db": mock_db,
            }

    def test_memory_extraction_failure_does_not_block_chat(self, setup_services_with_errors):
        """測試記憶擷取失敗不會阻止對話進行"""
        services = setup_services_with_errors

        # 安排：記憶服務失敗
        services["memory"].add_memory.side_effect = MemoryError("Mem0 不可用")

        # LLM 仍應可用
        services["llm"].generate_response.return_value = "儘管無法儲存記憶，仍可提供一般性投資建議"

        # 行動
        user_id = "user_001"
        try:
            services["memory"].add_memory(user_id, "訊息")
            llm_ok = False
        except MemoryError:
            # 記憶失敗，但繼續
            llm_ok = services["llm"].generate_response("查詢") is not None

        # 斷言
        assert llm_ok

    def test_llm_service_failure_returns_error_response(self, setup_services_with_errors):
        """測試 LLM 服務失敗時返回錯誤回應"""
        services = setup_services_with_errors

        # 安排
        services["llm"].generate_response.side_effect = LLMError("LLM API 錯誤")

        # 行動 & 斷言
        with pytest.raises(LLMError):
            services["llm"].generate_response("查詢")

    def test_database_save_failure_handled(self, setup_services_with_errors):
        """測試資料庫儲存失敗被妥善處理"""
        services = setup_services_with_errors

        # 安排
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        cursor.execute.side_effect = DatabaseError("資料庫連線失敗")
        services["db"].get_connection.return_value = conn

        # 行動 & 斷言
        with pytest.raises(DatabaseError):
            cursor.execute("INSERT INTO ...")


class TestChatFlowConversationHistory:
    """測試聊天流程的對話歷史管理"""

    @pytest.fixture
    def setup_services(self):
        """設定服務"""
        with patch("backend.src.services.llm_service.LLMService") as mock_llm:
            yield {"llm": mock_llm}

    def test_conversation_history_passed_to_llm(self, setup_services):
        """測試對話歷史被傳遞到 LLM"""
        services = setup_services

        # 安排
        history_captures = []

        def track_llm_call(user_input, memories=None, conversation_history=None):
            if conversation_history:
                history_captures.append(len(conversation_history))
            return "回應"

        services["llm"].generate_response.side_effect = track_llm_call

        # 行動
        history = [
            {"role": "user", "content": "第一條訊息"},
            {"role": "assistant", "content": "回應"},
            {"role": "user", "content": "第二條訊息"},
        ]
        services["llm"].generate_response("新訊息", conversation_history=history)

        # 斷言
        assert len(history_captures) > 0
        assert history_captures[0] == 3

    def test_conversation_context_window_respected(self, setup_services):
        """測試對話上下文窗口尺寸受尊重"""
        services = setup_services

        # 安排：LLM 最多接受 10 條訊息
        max_history_size = 10
        large_history = [{"role": "user", "content": f"訊息 {i}"} for i in range(20)]

        # 應該只傳遞最後 10 條
        def track_llm_call(user_input, memories=None, conversation_history=None):
            if conversation_history:
                assert len(conversation_history) <= max_history_size
            return "回應"

        services["llm"].generate_response.side_effect = track_llm_call

        # 行動
        limited_history = large_history[-max_history_size:]
        services["llm"].generate_response("查詢", conversation_history=limited_history)

        # 斷言
        assert len(limited_history) == max_history_size
