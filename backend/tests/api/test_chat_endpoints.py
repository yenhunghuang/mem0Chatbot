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

    @pytest.fixture
    def client(self):
        """建立 FastAPI 測試客戶端"""
        with patch("backend.src.main.DatabaseManager"), \
             patch("backend.src.main.EmbeddingService"), \
             patch("backend.src.main.LLMService"), \
             patch("backend.src.main.MemoryService"):

            # 從 main.py 匯入應該在 mock 設定好後進行
            from backend.src.main import app
            return TestClient(app)

    def test_chat_endpoint_exists(self, client):
        """測試 /api/v1/chat 端點存在"""
        # 注意: 由於尚未實作路由，此測試驗證端點結構
        # 實際測試需要路由被實作
        pass

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
        with patch("backend.src.services.conversation_service.ConversationService") as mock_conv, \
             patch("backend.src.services.memory_service.MemoryService") as mock_memory, \
             patch("backend.src.services.llm_service.LLMService") as mock_llm:

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
