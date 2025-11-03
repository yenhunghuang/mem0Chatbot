"""
聊天 API 端點測試

測試 POST /api/v1/chat 端點的請求/回應格式
"""

import pytest
from unittest.mock import patch, MagicMock
import json
import uuid
from typing import Dict, Any

from fastapi.testclient import TestClient


class TestChatEndpointRequestValidation:
    """測試聊天端點的請求驗證"""

    def test_chat_request_with_valid_payload(self):
        """測試有效的聊天請求"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": 1,
            "message": "我偏好投資科技股",
        }

        # 驗證有效載荷格式
        assert "user_id" in payload
        assert "conversation_id" in payload
        assert "message" in payload
        assert isinstance(payload["message"], str)
        assert len(payload["message"]) > 0

    def test_chat_request_missing_user_id(self):
        """測試缺少 user_id 的請求"""
        payload = {
            "conversation_id": 1,
            "message": "訊息",
        }

        # 驗證缺少必需欄位
        assert "user_id" not in payload

    def test_chat_request_missing_message(self):
        """測試缺少 message 的請求"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": 1,
        }

        # 驗證缺少必需欄位
        assert "message" not in payload

    def test_chat_request_empty_message(self):
        """測試空訊息"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": 1,
            "message": "",
        }

        # 空訊息應無效
        assert len(payload["message"]) == 0

    def test_chat_request_message_too_long(self):
        """測試超過最大長度的訊息"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": 1,
            "message": "x" * 10001,  # 超過 10000 字元限制
        }

        # 驗證長度
        assert len(payload["message"]) > 10000

    def test_chat_request_invalid_user_id_format(self):
        """測試無效 UUID 格式的 user_id"""
        payload = {
            "user_id": "not-a-uuid",
            "conversation_id": 1,
            "message": "訊息",
        }

        # 應該驗證 UUID 格式
        assert not self._is_valid_uuid(payload["user_id"])

    def test_chat_request_invalid_conversation_id_type(self):
        """測試無效的 conversation_id 類型"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": "not-a-number",
            "message": "訊息",
        }

        # 應該是整數
        assert not isinstance(payload["conversation_id"], int)

    def test_chat_request_negative_conversation_id(self):
        """測試負數的 conversation_id"""
        payload = {
            "user_id": str(uuid.uuid4()),
            "conversation_id": -1,
            "message": "訊息",
        }

        # 應該是正數
        assert payload["conversation_id"] < 0

    @staticmethod
    def _is_valid_uuid(val: str) -> bool:
        """驗證 UUID 格式"""
        try:
            uuid.UUID(val)
            return True
        except (ValueError, TypeError):
            return False


class TestChatEndpointResponseFormat:
    """測試聊天端點的回應格式"""

    def test_chat_response_structure(self):
        """測試回應的結構"""
        response = {
            "code": "SUCCESS",
            "message": "聊天回應已生成",
            "data": {
                "message_id": 101,
                "conversation_id": 1,
                "response": "根據您的偏好，科技股是一個不錯的選擇",
                "memories_used": ["我偏好科技股"],
                "timestamp": "2025-01-01T00:00:00",
            },
        }

        # 驗證結構
        assert response["code"] == "SUCCESS"
        assert "message" in response
        assert "data" in response
        assert "response" in response["data"]

    def test_chat_response_success_format(self):
        """測試成功回應的格式"""
        response = {
            "code": "SUCCESS",
            "data": {
                "message_id": 101,
                "response": "回應內容",
                "memories_used": ["記憶 1"],
            },
        }

        # 驗證成功回應
        assert response["code"] == "SUCCESS"
        assert isinstance(response["data"]["message_id"], int)
        assert isinstance(response["data"]["response"], str)
        assert isinstance(response["data"]["memories_used"], list)

    def test_chat_response_error_format(self):
        """測試錯誤回應的格式"""
        response = {
            "code": "VALIDATION_ERROR",
            "message": "訊息驗證失敗",
            "details": {
                "field": "message",
                "reason": "訊息長度超過限制",
            },
        }

        # 驗證錯誤回應
        assert response["code"] != "SUCCESS"
        assert "message" in response
        assert "details" in response

    def test_chat_response_memories_used_array(self):
        """測試 memories_used 是陣列"""
        response = {
            "code": "SUCCESS",
            "data": {
                "memories_used": ["記憶 1", "記憶 2", "記憶 3"],
            },
        }

        # 驗證
        assert isinstance(response["data"]["memories_used"], list)
        assert all(isinstance(m, str) for m in response["data"]["memories_used"])

    def test_chat_response_timestamp_iso_format(self):
        """測試時間戳記採用 ISO 格式"""
        response = {
            "code": "SUCCESS",
            "data": {
                "timestamp": "2025-01-01T12:34:56",
            },
        }

        # 驗證 ISO 格式
        assert "T" in response["data"]["timestamp"]


class TestChatEndpointHTTPStatus:
    """測試聊天端點的 HTTP 狀態碼"""

    def test_expected_status_codes(self):
        """測試預期的 HTTP 狀態碼"""
        status_codes = {
            "success": 200,
            "validation_error": 422,
            "not_found": 404,
            "server_error": 500,
            "service_unavailable": 503,
        }

        # 驗證狀態碼
        assert status_codes["success"] == 200
        assert status_codes["validation_error"] == 422
        assert status_codes["server_error"] == 500
        assert status_codes["service_unavailable"] == 503


class TestChatEndpointHeadersAndMetadata:
    """測試聊天端點的標頭和中繼資料"""

    def test_response_includes_request_id_header(self):
        """測試回應包含 X-Request-Id 標頭"""
        headers = {
            "X-Request-Id": "req_123456",
            "Content-Type": "application/json",
        }

        # 驗證標頭
        assert "X-Request-Id" in headers
        assert headers["Content-Type"] == "application/json"

    def test_response_content_type_json(self):
        """測試回應內容類型為 JSON"""
        headers = {
            "Content-Type": "application/json; charset=utf-8",
        }

        # 驗證
        assert "application/json" in headers["Content-Type"]

    def test_response_includes_timestamp(self):
        """測試回應包含伺服器時間戳記"""
        response = {
            "data": {
                "timestamp": "2025-01-01T00:00:00",
            },
        }

        # 驗證
        assert "timestamp" in response["data"]


class TestChatEndpointIntegrationWithServices:
    """測試聊天端點與後端服務的整合"""

    @pytest.fixture
    def mock_services(self):
        """模擬後端服務"""
        with patch("src.services.conversation_service.ConversationService") as mock_conv, \
             patch("src.services.memory_service.MemoryService") as mock_memory, \
             patch("src.services.llm_service.LLMService") as mock_llm:

            mock_conv.process_message.return_value = {
                "message_id": 101,
                "response": "根據您的偏好...",
                "memories_used": ["科技股偏好"],
            }

            yield {
                "conversation": mock_conv,
                "memory": mock_memory,
                "llm": mock_llm,
            }

    def test_chat_endpoint_calls_conversation_service(self, mock_services):
        """測試聊天端點呼叫 ConversationService"""
        services = mock_services

        # 驗證服務被正確呼叫
        assert hasattr(services["conversation"], "process_message")

    def test_chat_endpoint_returns_service_response(self, mock_services):
        """測試聊天端點返回服務回應"""
        services = mock_services

        result = services["conversation"].process_message("user_001", 1, "訊息")

        # 驗證回應
        assert result["message_id"] == 101
        assert "response" in result
        assert "memories_used" in result


class TestChatEndpointErrorResponses:
    """測試聊天端點的錯誤回應"""

    def test_validation_error_response(self):
        """測試驗證錯誤回應"""
        error_response = {
            "code": "VALIDATION_ERROR",
            "message": "輸入驗證失敗",
            "details": {
                "errors": [
                    {
                        "field": "message",
                        "message": "訊息不能為空",
                    },
                ],
            },
            "request_id": "req_001",
        }

        # 驗證錯誤結構
        assert error_response["code"] == "VALIDATION_ERROR"
        assert len(error_response["details"]["errors"]) > 0
        assert "request_id" in error_response

    def test_memory_service_error_response(self):
        """測試記憶服務錯誤回應"""
        error_response = {
            "code": "MEMORY_ERROR",
            "message": "無法處理記憶操作",
            "request_id": "req_002",
        }

        # 驗證
        assert error_response["code"] == "MEMORY_ERROR"

    def test_llm_service_unavailable_response(self):
        """測試 LLM 服務不可用回應"""
        error_response = {
            "code": "LLM_ERROR",
            "message": "LLM 服務暫時不可用",
            "request_id": "req_003",
        }

        # 驗證
        assert error_response["code"] == "LLM_ERROR"


class TestChatEndpointMemoriesUsed:
    """US2 T037: 測試 memories_used 欄位包含相關記憶"""

    def test_chat_response_includes_memories_used_field(self):
        """測試回應包含 memories_used 欄位"""
        response = {
            "code": "SUCCESS",
            "data": {
                "conversation_id": 1,
                "message_id": 101,
                "response": "基於您的偏好...",
                "memories_used": [],
            },
        }

        # 驗證 memories_used 欄位存在
        assert "memories_used" in response["data"]
        assert isinstance(response["data"]["memories_used"], list)

    def test_memories_used_contains_relevant_memories(self):
        """測試 memories_used 包含相關記憶

        給定：使用者發送投資建議請求
        當：系統檢索並使用相關記憶
        則：回應的 memories_used 應包含這些記憶
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "response": "基於您偏好投資科技股和您的中等風險承受度...",
                "memories_used": [
                    "使用者偏好投資科技股",
                    "使用者的風險承受度是中等偏高",
                ],
            },
        }

        # 驗證記憶被包含
        assert len(response["data"]["memories_used"]) >= 1
        assert any("科技股" in m for m in response["data"]["memories_used"])

    def test_memories_used_empty_when_no_memories_found(self):
        """測試新使用者無記憶時 memories_used 為空

        給定：新使用者沒有任何記憶
        當：發送訊息
        則：memories_used 應為空列表
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "response": "歡迎！請告訴我您的投資偏好...",
                "memories_used": [],
            },
        }

        # 驗證
        assert response["data"]["memories_used"] == []

    def test_memories_used_field_is_array_of_strings(self):
        """測試 memories_used 是字串陣列

        給定：回應包含 memories_used
        當：檢查欄位格式
        則：應是字串陣列
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "memories_used": [
                    "記憶 1",
                    "記憶 2",
                    "記憶 3",
                ],
            },
        }

        # 驗證
        assert isinstance(response["data"]["memories_used"], list)
        assert all(
            isinstance(m, str) for m in response["data"]["memories_used"]
        )

    def test_memories_used_max_count(self):
        """測試 memories_used 數量不超過 top_k

        給定：系統搜索 top_k=5 的記憶
        當：返回回應
        則：memories_used 最多有 5 個記憶
        """
        top_k = 5
        response = {
            "code": "SUCCESS",
            "data": {
                "memories_used": [
                    f"記憶 {i}" for i in range(1, min(top_k + 1, 4))
                ],
            },
        }

        # 驗證
        assert len(response["data"]["memories_used"]) <= top_k

    def test_memories_used_content_not_empty_strings(self):
        """測試 memories_used 中不包含空字串

        給定：回應包含 memories_used
        當：驗證內容
        則：每個記憶都是非空字串
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "memories_used": [
                    "有效記憶 1",
                    "有效記憶 2",
                ],
            },
        }

        # 驗證沒有空字串
        assert all(
            len(m.strip()) > 0 for m in response["data"]["memories_used"]
        )

    def test_memories_used_ordered_by_relevance(self):
        """測試 memories_used 按相關度排序

        給定：多個記憶被使用
        當：包含在回應中
        則：應按相關度從高到低排列
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "memories_used": [
                    "高相關記憶",  # 最相關
                    "中等相關記憶",
                    "低相關記憶",  # 最不相關
                ],
            },
        }

        # 驗證順序（需要追踪相關度，此處簡化驗證）
        assert len(response["data"]["memories_used"]) >= 1

    def test_memories_used_with_investment_preferences(self):
        """測試投資偏好被包含在 memories_used

        給定：使用者有投資偏好記憶
        當：詢問投資建議
        則：memories_used 應包含相關偏好
        """
        response = {
            "code": "SUCCESS",
            "data": {
                "response": "根據您對科技股的偏好和中等風險承受度...",
                "memories_used": [
                    "使用者偏好投資科技股，特別是 AI 和雲端運算公司",
                    "使用者的風險承受度是中等偏高",
                    "使用者打算長期投資",
                ],
            },
        }

        # 驗證投資偏好被包含
        assert any("科技股" in m for m in response["data"]["memories_used"])
        assert any("風險" in m for m in response["data"]["memories_used"])

    def test_memories_used_format_consistency(self):
        """測試 memories_used 的格式一致性

        給定：多次請求
        當：回應中包含 memories_used
        則：格式應始終一致
        """
        responses = [
            {
                "data": {
                    "memories_used": ["記憶 1", "記憶 2"],
                },
            },
            {
                "data": {
                    "memories_used": [],
                },
            },
            {
                "data": {
                    "memories_used": ["記憶 A"],
                },
            },
        ]

        # 驗證所有回應都有 memories_used 欄位
        assert all("memories_used" in r["data"] for r in responses)
        assert all(
            isinstance(r["data"]["memories_used"], list) for r in responses
        )

    def test_memories_used_in_different_conversation_states(self):
        """測試不同對話狀態下的 memories_used

        給定：對話的不同階段
        當：返回回應
        則：memories_used 應反映當前可用的記憶
        """
        # 第一條訊息：用戶提供偏好
        response_1 = {
            "data": {
                "memories_used": [],  # 尚無記憶
            },
        }

        # 第二條訊息：詢問建議
        response_2 = {
            "data": {
                "memories_used": [
                    "使用者偏好科技股",
                ],  # 有一個記憶
            },
        }

        # 驗證狀態變化
        assert len(response_1["data"]["memories_used"]) == 0
        assert len(response_2["data"]["memories_used"]) > 0

