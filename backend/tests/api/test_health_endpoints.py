"""
健康檢查端點測試

測試 /health, /health/detailed, /metrics 端點
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestHealthServiceFunctions:
    """測試健康檢查服務函數"""

    def test_check_sqlite_success(self):
        """測試 SQLite 檢查成功"""
        from src.api.routes.health import _check_sqlite
        
        result = _check_sqlite()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result

    def test_check_chroma_returns_dict(self):
        """測試 Chroma 檢查返回字典"""
        from src.api.routes.health import _check_chroma
        
        result = _check_chroma()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result

    def test_check_mem0_returns_dict(self):
        """測試 Mem0 檢查返回字典"""
        from src.api.routes.health import _check_mem0
        
        result = _check_mem0()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result

    def test_get_database_stats_returns_dict(self):
        """測試數據庫統計返回字典"""
        from src.api.routes.health import _get_database_stats
        
        result = _get_database_stats()
        assert isinstance(result, dict)
        assert "message" in result or "error" in result

    def test_get_memory_stats_returns_dict(self):
        """測試記憶統計返回字典"""
        from src.api.routes.health import _get_memory_stats
        
        result = _get_memory_stats()
        assert isinstance(result, dict)

    def test_health_status_class_constants(self):
        """測試 HealthStatus 類常數"""
        from src.api.routes.health import HealthStatus
        
        assert hasattr(HealthStatus, 'HEALTHY')
        assert hasattr(HealthStatus, 'DEGRADED')
        assert hasattr(HealthStatus, 'UNHEALTHY')
        
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"

    def test_check_sqlite_error_handling(self):
        """測試 SQLite 檢查錯誤處理"""
        from src.api.routes.health import _check_sqlite
        
        # 即使發生錯誤，也應該返回字典結構
        with patch("src.api.routes.health.DatabaseManager") as mock_db:
            mock_db.return_value.get_connection.side_effect = Exception("Connection failed")
            result = _check_sqlite()
            assert isinstance(result, dict)
            assert "error" in result or "message" in result

    def test_check_chroma_with_collections(self):
        """測試 Chroma 檢查包含集合計數"""
        from src.api.routes.health import _check_chroma
        
        with patch("src.api.routes.health.MemoryService") as mock_mem:
            mock_mem._client = MagicMock()
            mock_mem._client.list_collections.return_value = [
                {"name": "col1"},
                {"name": "col2"}
            ]
            result = _check_chroma()
            assert isinstance(result, dict)
            assert "status" in result

    def test_get_database_stats_success(self):
        """測試數據庫統計成功"""
        from src.api.routes.health import _get_database_stats
        
        with patch("src.api.routes.health.DatabaseManager") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_db.return_value.get_connection.return_value = mock_conn
            mock_conn.cursor.return_value = mock_cursor
            mock_cursor.fetchone.side_effect = [(10,), (50,)]
            
            result = _get_database_stats()
            assert isinstance(result, dict)
            assert "message" in result or "error" in result


class TestHealthRouterRegistration:
    """測試健康檢查路由註冊"""

    def test_health_router_has_endpoints(self):
        """測試健康檢查路由包含端點"""
        from src.api.routes.health import router
        
        # 檢查路由是否已定義
        assert hasattr(router, 'routes')
        assert len(router.routes) > 0

    def test_health_router_path_prefix(self):
        """測試健康檢查路由前綴"""
        from src.api.routes.health import router
        
        assert router.prefix == "/api/v1/health"

    def test_health_router_has_basic_endpoint(self):
        """測試基本健康檢查端點已定義"""
        from src.api.routes.health import router
        
        # 尋找根路由 - 因為 prefix 已加入路徑
        found_root = False
        for route in router.routes:
            if hasattr(route, 'path') and 'health' in route.path and route.path.endswith('/'):
                # 基本端點是 /api/v1/health/
                if route.path == '/api/v1/health/':
                    found_root = True
                    break
        assert found_root, "基本健康檢查端點未找到"

    def test_health_router_has_detailed_endpoint(self):
        """測試詳細健康檢查端點已定義"""
        from src.api.routes.health import router
        
        found_detailed = False
        for route in router.routes:
            if hasattr(route, 'path') and "detailed" in route.path:
                found_detailed = True
                break
        assert found_detailed, "詳細健康檢查端點未找到"

    def test_health_router_has_metrics_endpoint(self):
        """測試指標端點已定義"""
        from src.api.routes.health import router
        
        found_metrics = False
        for route in router.routes:
            if hasattr(route, 'path') and "metrics" in route.path:
                found_metrics = True
                break
        assert found_metrics, "指標端點未找到"
