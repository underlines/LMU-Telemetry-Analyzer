"""DuckDB service for read-only access to LMU telemetry files."""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from app.models.session import Lap, Session, SessionDetail
from app.models.signal import SignalData, SignalMetadata

logger = logging.getLogger(__name__)


class DuckDBService:
    """Service for safely accessing DuckDB telemetry files in read-only mode."""

    def __init__(self, file_path: Path) -> None:
        """Initialize service for a specific DuckDB file."""
        self.file_path = file_path
        self._connection: duckdb.DuckDBPyConnection | None = None

    @contextmanager
    def _connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        """Context manager for read-only DuckDB connections."""
        conn = None
        try:
            conn = duckdb.connect(database=str(self.file_path), read_only=True)
            yield conn
        except Exception as e:
            logger.error(f"Error connecting to {self.file_path}: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _get_metadata(self) -> dict[str, str]:
        """Extract metadata from the DuckDB file."""
        metadata: dict[str, str] = {}
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT key, value FROM metadata").fetchall()
                metadata = dict(rows)
        except Exception as e:
            logger.warning(f"Could not read metadata from {self.file_path}: {e}")
        return metadata

    def _get_channels(self) -> list[dict[str, Any]]:
        """Get list of available telemetry channels."""
        channels: list[dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT channelName, frequency, unit FROM channelsList"
                ).fetchall()
                channels = [
                    {"name": name, "frequency": freq, "unit": unit}
                    for name, freq, unit in rows
                ]
        except Exception as e:
            logger.warning(f"Could not read channels from {self.file_path}: {e}")
        return channels

    def _get_events(self) -> list[dict[str, Any]]:
        """Get list of available telemetry events."""
        events: list[dict[str, Any]] = []
        try:
            with self._connect() as conn:
                rows = conn.execute("SELECT eventName, unit FROM eventsList").fetchall()
                events = [{"name": name, "unit": unit} for name, unit in rows]
        except Exception as e:
            logger.warning(f"Could not read events from {self.file_path}: {e}")
        return events

    def _parse_recording_time(self, time_str: str | None) -> datetime | None:
        """Parse recording time from metadata format."""
        if not time_str:
            return None
        try:
            # Format: 2026-02-07T22_56_50Z
            normalized = time_str.replace("_", ":")
            return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError as e:
            logger.warning(f"Could not parse recording time '{time_str}': {e}")
            return None

    def get_session_info(self) -> Session:
        """Extract session information from the DuckDB file."""
        metadata = self._get_metadata()

        # Get lap count from Lap table
        lap_count = 0
        try:
            with self._connect() as conn:
                result = conn.execute('SELECT COUNT(DISTINCT value) FROM "Lap"').fetchone()
                lap_count = result[0] if result else 0
        except Exception as e:
            logger.warning(f"Could not count laps in {self.file_path}: {e}")

        return Session(
            id=self.file_path.stem,
            file_path=self.file_path,
            recording_time=self._parse_recording_time(metadata.get("RecordingTime")),
            session_time=metadata.get("SessionTime"),
            session_type=metadata.get("SessionType"),
            track_name=metadata.get("TrackName"),
            track_layout=metadata.get("TrackLayout"),
            driver_name=metadata.get("DriverName"),
            car_name=metadata.get("CarName"),
            car_class=metadata.get("CarClass"),
            weather_conditions=metadata.get("WeatherConditions"),
            lap_count=lap_count,
        )

    def get_laps(self) -> list[Lap]:
        """Extract lap information from the DuckDB file."""
        laps: list[Lap] = []

        try:
            with self._connect() as conn:
                # Get lap start times
                lap_starts = conn.execute(
                    'SELECT ts, value FROM "Lap" ORDER BY ts'
                ).fetchall()

                # Get lap times (completed laps only)
                lap_times = conn.execute(
                    'SELECT ts, value FROM "Lap Time" WHERE value > 0 ORDER BY ts'
                ).fetchall()
                lap_time_map = dict(lap_times)

                # Build lap info
                for i, (start_ts, lap_num) in enumerate(lap_starts):
                    # Calculate end time from next lap start, or None if last lap
                    end_ts = lap_starts[i + 1][0] if i + 1 < len(lap_starts) else None

                    # Lap time is recorded at start of next lap
                    lap_time = lap_time_map.get(end_ts) if end_ts else None

                    laps.append(
                        Lap(
                            lap_number=int(lap_num),
                            start_time=float(start_ts),
                            end_time=float(end_ts) if end_ts else None,
                            lap_time=float(lap_time) if lap_time else None,
                            valid=lap_time is not None and lap_time > 0,
                        )
                    )

        except Exception as e:
            logger.error(f"Error extracting laps from {self.file_path}: {e}")

        return laps

    def get_available_tables(self) -> list[str]:
        """Get list of all tables in the DuckDB file."""
        tables: list[str] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'main' ORDER BY table_name"
                ).fetchall()
                tables = [row[0] for row in rows]
        except Exception as e:
            logger.error(f"Error listing tables in {self.file_path}: {e}")
        return tables

    def get_session_detail(self) -> SessionDetail:
        """Get detailed session info including channels and events."""
        session = self.get_session_info()
        return SessionDetail(
            **session.model_dump(),
            channels=self._get_channels(),
            events=self._get_events(),
        )

    def get_channel_metadata(self, channel_name: str) -> SignalMetadata | None:
        """Get metadata for a specific channel."""
        try:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT channelName, frequency, unit FROM channelsList WHERE channelName = ?",
                    [channel_name],
                ).fetchone()

                if row:
                    name, frequency, unit = row
                    # Get min/max values from the channel table if it exists
                    min_val: float | None = None
                    max_val: float | None = None
                    try:
                        stats = conn.execute(
                            f'SELECT MIN(value), MAX(value) FROM "{name}"'
                        ).fetchone()
                        if stats:
                            min_val, max_val = stats
                    except Exception:
                        pass  # Table might not exist or be accessible

                    return SignalMetadata(
                        name=name,
                        frequency=frequency,
                        unit=unit,
                        min_value=float(min_val) if min_val is not None else None,
                        max_value=float(max_val) if max_val is not None else None,
                    )
        except Exception as e:
            logger.warning(f"Could not get metadata for channel {channel_name}: {e}")
        return None

    def get_all_channel_metadata(self) -> list[SignalMetadata]:
        """Get metadata for all available channels."""
        metadata_list: list[SignalMetadata] = []
        channels = self._get_channels()

        for channel_info in channels:
            name = channel_info["name"]
            metadata = self.get_channel_metadata(name)
            if metadata:
                metadata_list.append(metadata)

        return metadata_list

    def _get_table_columns(self, table_name: str) -> list[str]:
        """Get list of columns for a table."""
        columns: list[str] = []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = ? ORDER BY ordinal_position",
                    [table_name],
                ).fetchall()
                columns = [row[0] for row in rows]
        except Exception as e:
            logger.warning(f"Could not get columns for table {table_name}: {e}")
        return columns

    def get_signal_data(
        self,
        channel_name: str,
        start_time: float | None = None,
        end_time: float | None = None,
        max_points: int | None = None,
    ) -> SignalData:
        """Retrieve signal data for a channel, optionally filtered by time range.

        Args:
            channel_name: Name of the channel/signal to retrieve
            start_time: Optional start time filter (session time in seconds)
            end_time: Optional end time filter (session time in seconds)
            max_points: Optional maximum number of points (for downsampling)

        Returns:
            SignalData with timestamps and values
        """
        timestamps: list[float] = []
        values: list[float] = []
        unit: str | None = None

        try:
            with self._connect() as conn:
                # Get unit from channelsList
                row = conn.execute(
                    "SELECT unit FROM channelsList WHERE channelName = ?",
                    [channel_name],
                ).fetchone()
                if row:
                    unit = row[0]

                # Check if table has timestamp column
                columns = self._get_table_columns(channel_name)
                has_timestamp = "ts" in columns

                if not has_timestamp:
                    # Table without timestamp - just get all values with dummy timestamps
                    query = f'SELECT value FROM "{channel_name}"'
                    rows = conn.execute(query).fetchall()
                    values = [float(row[0]) for row in rows]
                    # Generate sequential timestamps
                    timestamps = [float(i) for i in range(len(values))]
                else:
                    # Build query with optional time filtering
                    query = f'SELECT ts, value FROM "{channel_name}"'
                    params: list[Any] = []

                    if start_time is not None or end_time is not None:
                        conditions = []
                        if start_time is not None:
                            conditions.append("ts >= ?")
                            params.append(start_time)
                        if end_time is not None:
                            conditions.append("ts <= ?")
                            params.append(end_time)
                        query += " WHERE " + " AND ".join(conditions)

                    query += " ORDER BY ts"

                    rows = conn.execute(query, params).fetchall()
                    timestamps = [float(row[0]) for row in rows]
                    values = [float(row[1]) for row in rows]

                    # Apply downsampling if max_points specified and data is larger
                    if max_points is not None and max_points > 0 and len(values) > max_points:
                        step = len(values) // max_points
                        if step > 1:
                            timestamps = timestamps[::step]
                            values = values[::step]

        except Exception as e:
            logger.error(f"Error retrieving signal data for {channel_name}: {e}")
            raise

        return SignalData(
            channel=channel_name,
            timestamps=timestamps,
            values=values,
            unit=unit,
        )

    def channel_exists(self, channel_name: str) -> bool:
        """Check if a channel exists in the database."""
        try:
            with self._connect() as conn:
                result = conn.execute(
                    "SELECT 1 FROM channelsList WHERE channelName = ?",
                    [channel_name],
                ).fetchone()
                return result is not None
        except Exception as e:
            logger.warning(f"Error checking if channel exists {channel_name}: {e}")
            return False

    def get_distance_data(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        max_points: int | None = None,
    ) -> SignalData | None:
        """Retrieve distance traveled data if available.

        Distance is typically stored in a channel like 'Distance' or 'LapDistance'.
        """
        # Common distance channel names in racing telemetry
        distance_channels = ["Distance", "LapDistance", "mTotalDistance", "LapDist"]

        for channel in distance_channels:
            if self.channel_exists(channel):
                try:
                    return self.get_signal_data(channel, start_time, end_time, max_points)
                except Exception as e:
                    logger.warning(f"Could not retrieve distance from {channel}: {e}")
                    continue

        return None
