"""Telemetry core module for session discovery and management."""

import logging
from pathlib import Path

from app.core.config import get_telemetry_path
from app.models.session import Lap, Session, SessionDetail
from app.services.duckdb_service import DuckDBService

logger = logging.getLogger(__name__)


class TelemetryManager:
    """Manages discovery and access to telemetry sessions."""

    def __init__(self, telemetry_path: Path | None = None) -> None:
        """Initialize telemetry manager."""
        self.telemetry_path = telemetry_path or get_telemetry_path()
        self._sessions_cache: dict[str, Session] | None = None

    def _discover_duckdb_files(self) -> list[Path]:
        """Find all .duckdb files in the telemetry directory."""
        if not self.telemetry_path.exists():
            logger.error(f"Telemetry path does not exist: {self.telemetry_path}")
            return []

        duckdb_files = list(self.telemetry_path.glob("*.duckdb"))
        logger.info(f"Discovered {len(duckdb_files)} telemetry files")
        return sorted(duckdb_files)

    def list_sessions(self, force_refresh: bool = False) -> list[Session]:
        """List all available telemetry sessions."""
        if self._sessions_cache is not None and not force_refresh:
            return list(self._sessions_cache.values())

        sessions: dict[str, Session] = {}

        for file_path in self._discover_duckdb_files():
            try:
                service = DuckDBService(file_path)
                session = service.get_session_info()
                sessions[session.id] = session
            except Exception as e:
                logger.error(f"Error reading session from {file_path}: {e}")

        self._sessions_cache = sessions
        return list(sessions.values())

    def get_session(self, session_id: str) -> Session | None:
        """Get a specific session by ID."""
        sessions = self.list_sessions()
        for session in sessions:
            if session.id == session_id:
                return session
        return None

    def get_session_laps(self, session_id: str) -> list[Lap] | None:
        """Get all laps for a specific session."""
        session = self.get_session(session_id)
        if not session:
            return None

        try:
            service = DuckDBService(session.file_path)
            return service.get_laps()
        except Exception as e:
            logger.error(f"Error reading laps from session {session_id}: {e}")
            return None

    def get_session_detail(self, session_id: str) -> SessionDetail | None:
        """Get detailed session info including channels and events."""
        session = self.get_session(session_id)
        if not session:
            return None

        try:

            service = DuckDBService(session.file_path)
            return service.get_session_detail()
        except Exception as e:
            logger.error(f"Error reading session detail from {session_id}: {e}")
            return None


# Global telemetry manager instance
telemetry_manager = TelemetryManager()
