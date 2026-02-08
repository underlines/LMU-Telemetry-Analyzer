"""Tests for FastAPI endpoints."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# Use the sample duckdb file from repo root
SAMPLE_DB = Path(__file__).parent.parent.parent / "Autódromo José Carlos Pace_P_2026-02-07T22_56_50Z.duckdb"


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self) -> None:
        """Test root endpoint returns API info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "LMU Telemetry Analyzer API"
        assert "version" in data
        assert "docs" in data

    def test_health_endpoint(self) -> None:
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "checks" in data
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


class TestSessionEndpoints:
    """Tests for session-related endpoints."""

    def test_list_sessions(self) -> None:
        """Test listing sessions."""
        response = client.get("/api/v1/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "total" in data
        assert isinstance(data["sessions"], list)
        assert isinstance(data["total"], int)

    def test_get_session_detail(self) -> None:
        """Test getting session details."""
        session_id = SAMPLE_DB.stem
        response = client.get(f"/api/v1/sessions/{session_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == session_id
        assert "track_name" in data
        assert "car_name" in data
        assert "channels" in data
        assert "events" in data

    def test_get_session_not_found(self) -> None:
        """Test getting non-existent session."""
        response = client.get("/api/v1/sessions/nonexistent")
        assert response.status_code == 404
        assert "detail" in response.json()


class TestLapEndpoints:
    """Tests for lap-related endpoints."""

    def test_get_session_laps(self) -> None:
        """Test getting laps for a session."""
        session_id = SAMPLE_DB.stem
        response = client.get(f"/api/v1/sessions/{session_id}/laps")
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
        assert "laps" in data
        assert "total" in data
        assert isinstance(data["laps"], list)
        assert len(data["laps"]) > 0

        # Check lap structure
        lap = data["laps"][0]
        assert "lap_number" in lap
        assert "start_time" in lap
        assert "end_time" in lap
        assert "lap_time" in lap
        assert "valid" in lap

    def test_get_session_laps_not_found(self) -> None:
        """Test getting laps for non-existent session."""
        response = client.get("/api/v1/sessions/nonexistent/laps")
        assert response.status_code == 404
        assert "detail" in response.json()
