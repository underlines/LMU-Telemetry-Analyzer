"""Signal service for retrieving and comparing telemetry signals."""

import logging
from pathlib import Path

from app.core.config import get_telemetry_path
from app.core.telemetry import TelemetryManager
from app.models.session import Lap
from app.models.signal import (
    LapComparison,
    LapComparisonRequest,
    SignalMetadata,
    SignalSlice,
)
from app.services.duckdb_service import DuckDBService

logger = logging.getLogger(__name__)


class SignalService:
    """Service for signal slicing, retrieval, and lap comparison."""

    def __init__(self, telemetry_manager: TelemetryManager | None = None) -> None:
        """Initialize with optional telemetry manager."""
        self.telemetry_manager = telemetry_manager or TelemetryManager(get_telemetry_path())

    def _get_service_for_session(self, session_id: str) -> DuckDBService:
        """Get DuckDBService for a session."""
        session = self.telemetry_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        return DuckDBService(Path(session.file_path))

    def _find_lap(self, laps: list[Lap], lap_number: int) -> Lap:
        """Find a lap by number in the list."""
        for lap in laps:
            if lap.lap_number == lap_number:
                return lap
        raise ValueError(f"Lap {lap_number} not found")

    def get_available_signals(self, session_id: str) -> list[SignalMetadata]:
        """Get list of available signals for a session."""
        service = self._get_service_for_session(session_id)
        return service.get_all_channel_metadata()

    def get_lap_signals(
        self,
        session_id: str,
        lap_number: int,
        channels: list[str],
        normalize_time: bool = True,
        use_distance: bool = False,
        max_points: int | None = None,
    ) -> list[SignalSlice]:
        """Retrieve signal data for specific channels within a lap.

        Args:
            session_id: Session identifier
            lap_number: Lap number to retrieve
            channels: List of channel names to fetch
            normalize_time: Whether to normalize timestamps to lap start
            use_distance: Whether to use distance for X-axis instead of time
            max_points: Maximum points per signal (downsampling)

        Returns:
            List of SignalSlice objects
        """
        service = self._get_service_for_session(session_id)
        laps = service.get_laps()
        lap = self._find_lap(laps, lap_number)

        slices: list[SignalSlice] = []

        for channel in channels:
            if not service.channel_exists(channel):
                logger.warning(f"Channel {channel} not found in session {session_id}")
                continue

            try:
                # Get signal data for the lap time range
                signal_data = service.get_signal_data(
                    channel_name=channel,
                    start_time=lap.start_time,
                    end_time=lap.end_time,
                    max_points=max_points,
                )

                # Get distance data if requested
                distance_data: list[float] | None = None
                if use_distance:
                    dist_signal = service.get_distance_data(
                        start_time=lap.start_time,
                        end_time=lap.end_time,
                        max_points=max_points,
                    )
                    if dist_signal:
                        distance_data = dist_signal.values

                # Calculate normalized time
                normalized_time: list[float] = []
                if normalize_time and signal_data.timestamps:
                    start = signal_data.timestamps[0]
                    normalized_time = [t - start for t in signal_data.timestamps]
                else:
                    normalized_time = signal_data.timestamps

                # Calculate actual sampling rate
                sampling_rate = 0
                if len(signal_data.timestamps) > 1:
                    duration = signal_data.timestamps[-1] - signal_data.timestamps[0]
                    if duration > 0:
                        sampling_rate = int(len(signal_data.timestamps) / duration)

                slices.append(
                    SignalSlice(
                        channel=channel,
                        lap_number=lap_number,
                        session_id=session_id,
                        timestamps=signal_data.timestamps,
                        normalized_time=normalized_time,
                        values=signal_data.values,
                        distance=distance_data,
                        unit=signal_data.unit,
                        sampling_rate=sampling_rate,
                    )
                )

            except Exception as e:
                logger.error(f"Error retrieving signal {channel} for lap {lap_number}: {e}")
                continue

        return slices

    def compare_laps(
        self,
        session_id: str,
        request: LapComparisonRequest,
    ) -> list[LapComparison]:
        """Compare signals between two laps.

        Args:
            session_id: Session identifier
            request: LapComparisonRequest with target, reference, and channels

        Returns:
            List of LapComparison objects (one per channel)
        """
        service = self._get_service_for_session(session_id)
        laps = service.get_laps()

        target_lap = self._find_lap(laps, request.target_lap)
        reference_lap = self._find_lap(laps, request.reference_lap)

        comparisons: list[LapComparison] = []

        for channel in request.channels:
            if not service.channel_exists(channel):
                logger.warning(f"Channel {channel} not found in session {session_id}")
                continue

            try:
                # Get signal data for both laps
                target_data = service.get_signal_data(
                    channel_name=channel,
                    start_time=target_lap.start_time,
                    end_time=target_lap.end_time,
                    max_points=request.max_points,
                )

                reference_data = service.get_signal_data(
                    channel_name=channel,
                    start_time=reference_lap.start_time,
                    end_time=reference_lap.end_time,
                    max_points=request.max_points,
                )

                # Get distance data if requested
                target_distance: list[float] | None = None
                reference_distance: list[float] | None = None
                if request.use_distance:
                    target_dist = service.get_distance_data(
                        start_time=target_lap.start_time,
                        end_time=target_lap.end_time,
                        max_points=request.max_points,
                    )
                    reference_dist = service.get_distance_data(
                        start_time=reference_lap.start_time,
                        end_time=reference_lap.end_time,
                        max_points=request.max_points,
                    )
                    if target_dist:
                        target_distance = target_dist.values
                    if reference_dist:
                        reference_distance = reference_dist.values

                # Normalize timestamps if requested
                target_timestamps = target_data.timestamps
                reference_timestamps = reference_data.timestamps
                normalized_x: list[float] = []

                if request.normalize_time:
                    if target_timestamps:
                        target_start = target_timestamps[0]
                        target_timestamps = [t - target_start for t in target_timestamps]
                    if reference_timestamps:
                        ref_start = reference_timestamps[0]
                        reference_timestamps = [t - ref_start for t in reference_timestamps]

                # Use distance as X-axis if requested and available
                if request.use_distance and target_distance:
                    normalized_x = target_distance
                elif request.normalize_time:
                    normalized_x = target_timestamps

                comparisons.append(
                    LapComparison(
                        channel=channel,
                        unit=target_data.unit,
                        target_lap=request.target_lap,
                        target_timestamps=target_timestamps,
                        target_values=target_data.values,
                        target_distance=target_distance,
                        reference_lap=request.reference_lap,
                        reference_timestamps=reference_timestamps,
                        reference_values=reference_data.values,
                        reference_distance=reference_distance,
                        normalized_x=normalized_x,
                    )
                )

            except Exception as e:
                logger.error(
                    f"Error comparing channel {channel} for laps "
                    f"{request.target_lap} vs {request.reference_lap}: {e}"
                )
                continue

        return comparisons
