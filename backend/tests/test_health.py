"""Tests for health endpoints."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Test client fixture."""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint."""

    def test_health_returns_200(self, client: TestClient) -> None:
        """Health endpoint should return 200 OK."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_response_structure(self, client: TestClient) -> None:
        """Health response should have correct structure."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data

    def test_health_status_values(self, client: TestClient) -> None:
        """Health status should be one of expected values."""
        response = client.get("/health")
        data = response.json()

        assert data["status"] in ["healthy", "degraded", "unhealthy"]
        assert data["version"] == "0.1.0"

    def test_health_checks_structure(self, client: TestClient) -> None:
        """Health checks should have correct structure."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["checks"], list)
        assert len(data["checks"]) >= 1

        for check in data["checks"]:
            assert "name" in check
            assert "status" in check
            assert check["status"] in ["healthy", "unhealthy", "unknown", "degraded"]

    def test_health_duckdb_check_present(self, client: TestClient) -> None:
        """Health check should include DuckDB connectivity check."""
        response = client.get("/health")
        data = response.json()

        check_names = [c["name"] for c in data["checks"]]
        assert "duckdb" in check_names

    def test_health_cache_directory_check_present(self, client: TestClient) -> None:
        """Health check should include cache directory check."""
        response = client.get("/health")
        data = response.json()

        check_names = [c["name"] for c in data["checks"]]
        assert "cache_directory" in check_names

    def test_health_timestamp_is_valid_iso(self, client: TestClient) -> None:
        """Health timestamp should be valid ISO format."""
        response = client.get("/health")
        data = response.json()

        # Should be able to parse as datetime
        timestamp = datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        assert isinstance(timestamp, datetime)


class TestReadinessEndpoint:
    """Tests for /ready endpoint."""

    def test_ready_returns_200(self, client: TestClient) -> None:
        """Readiness endpoint should return 200 OK."""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_ready_response_structure(self, client: TestClient) -> None:
        """Readiness response should have correct structure."""
        response = client.get("/ready")
        data = response.json()

        assert "ready" in data
        assert isinstance(data["ready"], bool)
        assert "timestamp" in data
        assert "dependencies" in data

    def test_ready_dependencies_structure(self, client: TestClient) -> None:
        """Readiness dependencies should have correct structure."""
        response = client.get("/ready")
        data = response.json()

        assert isinstance(data["dependencies"], list)

        for dep in data["dependencies"]:
            assert "name" in dep
            assert "required" in dep
            assert isinstance(dep["required"], bool)
            assert "available" in dep
            assert isinstance(dep["available"], bool)

    def test_ready_telemetry_path_dependency_present(self, client: TestClient) -> None:
        """Readiness check should include telemetry path dependency."""
        response = client.get("/ready")
        data = response.json()

        dep_names = [d["name"] for d in data["dependencies"]]
        assert "telemetry_path" in dep_names

    def test_ready_when_telemetry_path_missing(self, client: TestClient) -> None:
        """Readiness should be false when telemetry path is missing."""
        with patch("app.api.health.get_telemetry_path") as mock_path:
            mock_path.return_value = MagicMock(
                exists=lambda: False,
                is_dir=lambda: False,
                __str__=lambda: "/nonexistent/path"
            )
            response = client.get("/ready")
            data = response.json()

            assert data["ready"] is False
            telemetry_dep = next(
                d for d in data["dependencies"] if d["name"] == "telemetry_path"
            )
            assert telemetry_dep["available"] is False
            assert telemetry_dep["required"] is True


class TestMetricsEndpoint:
    """Tests for /metrics endpoint."""

    def test_metrics_returns_200(self, client: TestClient) -> None:
        """Metrics endpoint should return 200 OK."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_response_structure(self, client: TestClient) -> None:
        """Metrics response should have correct structure."""
        response = client.get("/metrics")
        data = response.json()

        assert "timestamp" in data
        assert "stats" in data

    def test_metrics_stats_structure(self, client: TestClient) -> None:
        """Metrics stats should have correct structure."""
        response = client.get("/metrics")
        data = response.json()

        stats = data["stats"]
        assert "total_sessions" in stats
        assert "total_files" in stats
        assert "total_laps" in stats
        assert "cached_layouts" in stats
        assert "cache_size_mb" in stats

        # All should be numeric
        assert isinstance(stats["total_sessions"], int)
        assert isinstance(stats["total_files"], int)
        assert isinstance(stats["total_laps"], int)
        assert isinstance(stats["cached_layouts"], int)
        assert isinstance(stats["cache_size_mb"], (int, float))

    def test_metrics_stats_non_negative(self, client: TestClient) -> None:
        """Metrics stats should be non-negative."""
        response = client.get("/metrics")
        data = response.json()

        stats = data["stats"]
        assert stats["total_sessions"] >= 0
        assert stats["total_files"] >= 0
        assert stats["total_laps"] >= 0
        assert stats["cached_layouts"] >= 0
        assert stats["cache_size_mb"] >= 0


class TestRootEndpoint:
    """Tests for root endpoint."""

    def test_root_returns_200(self, client: TestClient) -> None:
        """Root endpoint should return 200 OK."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self, client: TestClient) -> None:
        """Root response should have correct structure."""
        response = client.get("/")
        data = response.json()

        assert "message" in data
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    def test_root_has_correct_values(self, client: TestClient) -> None:
        """Root response should have correct values."""
        response = client.get("/")
        data = response.json()

        assert "LMU Telemetry Analyzer" in data["message"]
        assert data["docs"] == "/docs"
        assert data["health"] == "/health"


class TestOpenAPIDocs:
    """Tests for OpenAPI documentation."""

    def test_openapi_json_available(self, client: TestClient) -> None:
        """OpenAPI JSON spec should be available."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_has_required_paths(self, client: TestClient) -> None:
        """OpenAPI spec should have required paths."""
        response = client.get("/openapi.json")
        data = response.json()

        paths = data.get("paths", {})
        assert "/health" in paths
        assert "/ready" in paths
        assert "/metrics" in paths

    def test_openapi_has_tags(self, client: TestClient) -> None:
        """OpenAPI spec should have tags defined."""
        response = client.get("/openapi.json")
        data = response.json()

        tags = data.get("tags", [])
        tag_names = [t["name"] for t in tags]
        assert "health" in tag_names
        assert "sessions" in tag_names
        assert "signals" in tag_names
        assert "segments" in tag_names

    def test_swagger_ui_available(self, client: TestClient) -> None:
        """Swagger UI should be available at /docs."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_available(self, client: TestClient) -> None:
        """ReDoc should be available at /redoc."""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
