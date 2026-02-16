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
        sampling_percent: int = 20,
    ) -> list[SignalSlice]:
        """Retrieve signal data for specific channels within a lap.

        Args:
            session_id: Session identifier
            lap_number: Lap number to retrieve
            channels: List of channel names to fetch
            normalize_time: Whether to normalize timestamps to lap start
            use_distance: Whether to use distance for X-axis instead of time
            sampling_percent: Sampling percentage (1-100) for downsampling

        Returns:
            List of SignalSlice objects
        """
        service = self._get_service_for_session(session_id)
        laps = service.get_laps()
        lap = self._find_lap(laps, lap_number)

        # Calculate lap duration for sample count estimation
        lap_duration = 0.0
        if lap.end_time is not None:
            lap_duration = lap.end_time - lap.start_time
        elif lap.lap_time is not None and lap.lap_time > 0:
            lap_duration = lap.lap_time
        else:
            # Estimate from average lap time of other laps
            valid_lap_times = [l.lap_time for l in laps if l.lap_time and l.lap_time > 0]
            if valid_lap_times:
                lap_duration = sum(valid_lap_times) / len(valid_lap_times)

        # Get metadata for all channels to calculate max sample count
        max_samples = 0
        channel_metadata: dict[str, tuple[float, str | None]] = {}  # frequency, unit

        for channel in channels:
            if not service.channel_exists(channel):
                logger.warning(f"Channel {channel} not found in session {session_id}")
                continue
            try:
                metadata = service.get_channel_metadata(channel)
                if metadata:
                    freq = metadata.frequency
                    # Calculate expected samples for this channel in this lap
                    expected_samples = int(lap_duration * freq)
                    channel_metadata[channel] = (freq, metadata.unit)
                    if expected_samples > max_samples:
                        max_samples = expected_samples
            except Exception as e:
                logger.error(f"Error getting metadata for {channel}: {e}")
                continue

        # Calculate max_points from sampling percentage
        max_points: int | None = None
        if max_samples > 0 and sampling_percent < 100:
            max_points = max(1, int(max_samples * sampling_percent / 100))

        # Fetch data with consistent downsampling
        slices: list[SignalSlice] = []
        for channel in channels:
            if channel not in channel_metadata:
                continue

            try:
                # Get signal data with downsampling
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

                # Calculate normalized time (relative to lap start)
                normalized_time: list[float] = []
                if signal_data.timestamps:
                    start = signal_data.timestamps[0]
                    normalized_time = [t - start for t in signal_data.timestamps]

                # Calculate actual sampling rate from returned data
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
                        total_samples=signal_data.total_samples,
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

        # Calculate max sample count across both laps for consistent downsampling
        target_duration = (
            target_lap.end_time - target_lap.start_time
            if target_lap.end_time
            else (target_lap.lap_time or 0)
        )
        ref_duration = (
            reference_lap.end_time - reference_lap.start_time
            if reference_lap.end_time
            else (reference_lap.lap_time or 0)
        )
        max_duration = max(target_duration, ref_duration)

        # Get max frequency across all channels to calculate max samples
        max_samples = 0
        for channel in request.channels:
            if not service.channel_exists(channel):
                continue
            metadata = service.get_channel_metadata(channel)
            if metadata:
                expected_samples = int(max_duration * metadata.frequency)
                if expected_samples > max_samples:
                    max_samples = expected_samples

        # Calculate max_points from sampling percentage
        max_points: int | None = None
        if max_samples > 0 and request.sampling_percent < 100:
            max_points = max(1, int(max_samples * request.sampling_percent / 100))

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
                    max_points=max_points,
                )

                reference_data = service.get_signal_data(
                    channel_name=channel,
                    start_time=reference_lap.start_time,
                    end_time=reference_lap.end_time,
                    max_points=max_points,
                )

                # Get distance data if requested
                target_distance: list[float] | None = None
                reference_distance: list[float] | None = None
                if request.use_distance:
                    target_dist = service.get_distance_data(
                        start_time=target_lap.start_time,
                        end_time=target_lap.end_time,
                        max_points=max_points,
                    )
                    reference_dist = service.get_distance_data(
                        start_time=reference_lap.start_time,
                        end_time=reference_lap.end_time,
                        max_points=max_points,
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
