"""Tests for telemetry discovery and access (Step 1)."""

from pathlib import Path

from app.core.telemetry import TelemetryManager
from app.services.duckdb_service import DuckDBService

# Use the sample duckdb file from repo root
# tests/ is in backend/, so need to go up 2 levels to get to repo root
SAMPLE_DB = Path(__file__).parent.parent.parent / "Autódromo José Carlos Pace_P_2026-02-07T22_56_50Z.duckdb"


class TestDuckDBService:
    """Tests for DuckDBService."""

    def test_service_initialization(self) -> None:
        """Test service can be initialized."""
        service = DuckDBService(SAMPLE_DB)
        assert service.file_path == SAMPLE_DB

    def test_get_session_info(self) -> None:
        """Test session info extraction."""
        service = DuckDBService(SAMPLE_DB)
        session = service.get_session_info()

        assert session.id == SAMPLE_DB.stem
        assert session.track_name is not None
        assert session.car_name is not None
        assert session.lap_count > 0

    def test_get_laps(self) -> None:
        """Test lap extraction."""
        service = DuckDBService(SAMPLE_DB)
        laps = service.get_laps()

        assert len(laps) > 0
        # Lap 0 is out/in lap, may not have a time
        valid_laps = [lap for lap in laps if lap.valid]
        assert len(valid_laps) > 0

    def test_get_available_tables(self) -> None:
        """Test table listing."""
        service = DuckDBService(SAMPLE_DB)
        tables = service.get_available_tables()

        assert len(tables) > 0
        assert "metadata" in tables
        assert "channelsList" in tables
        assert "eventsList" in tables
        assert "Lap" in tables

    def test_get_session_detail(self) -> None:
        """Test detailed session info extraction."""
        service = DuckDBService(SAMPLE_DB)
        detail = service.get_session_detail()

        assert detail.channels is not None
        assert len(detail.channels) > 0
        assert detail.events is not None
        assert len(detail.events) > 0


class TestTelemetryManager:
    """Tests for TelemetryManager."""

    def test_list_sessions(self) -> None:
        """Test session discovery."""
        manager = TelemetryManager(SAMPLE_DB.parent)
        sessions = manager.list_sessions()

        assert len(sessions) >= 1
        session_ids = [s.id for s in sessions]
        assert SAMPLE_DB.stem in session_ids

    def test_get_session(self) -> None:
        """Test getting specific session."""
        manager = TelemetryManager(SAMPLE_DB.parent)
        session = manager.get_session(SAMPLE_DB.stem)

        assert session is not None
        assert session.id == SAMPLE_DB.stem

    def test_get_session_not_found(self) -> None:
        """Test getting non-existent session."""
        manager = TelemetryManager(SAMPLE_DB.parent)
        session = manager.get_session("nonexistent")

        assert session is None

    def test_get_session_laps(self) -> None:
        """Test getting laps for a session."""
        manager = TelemetryManager(SAMPLE_DB.parent)
        laps = manager.get_session_laps(SAMPLE_DB.stem)

        assert laps is not None
        assert len(laps) > 0

    def test_get_session_laps_not_found(self) -> None:
        """Test getting laps for non-existent session."""
        manager = TelemetryManager(SAMPLE_DB.parent)
        laps = manager.get_session_laps("nonexistent")

        assert laps is None
