"""Segment service - main orchestrator for Step 3 functionality.

Coordinates:
- Reference lap selection
- Track layout detection
- Metrics calculation
- Two-tier caching
"""

import logging
from pathlib import Path

from app.core.config import get_telemetry_path
from app.core.metrics import MetricsCalculator
from app.core.reference_lap import ReferenceLapSelector
from app.core.signals import SignalService
from app.core.telemetry import TelemetryManager
from app.core.track_layout import TrackLayoutService
from app.models.segment import (
    LapSegmentMetrics,
    Segment,
    SegmentComparison,
    SegmentComparisonRequest,
    SegmentComparisonResponse,
    TrackLayout,
)
from app.models.session import Lap
from app.models.signal import SignalSlice
from app.services.duckdb_service import DuckDBService
from app.services.segment_cache import SegmentCache

logger = logging.getLogger(__name__)


class SegmentService:
    """Main service for track segmentation and metrics."""

    def __init__(
        self,
        telemetry_manager: TelemetryManager | None = None,
        signal_service: SignalService | None = None,
        segment_cache: SegmentCache | None = None,
    ) -> None:
        """Initialize segment service with dependencies."""
        self.telemetry_manager = telemetry_manager or TelemetryManager(get_telemetry_path())
        self.signal_service = signal_service or SignalService(self.telemetry_manager)
        self.segment_cache = segment_cache or SegmentCache()
        self.layout_service = TrackLayoutService()
        self.metrics_calculator = MetricsCalculator()
        self.reference_selector = ReferenceLapSelector()

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

    def get_or_create_layout(
        self,
        session_id: str,
        preferred_lap: int | None = None,
        force_regenerate: bool = False,
    ) -> TrackLayout:
        """Get cached layout or detect new one from reference lap.

        Args:
            session_id: Session identifier
            preferred_lap: Optional user override for reference lap
            force_regenerate: Force new layout detection even if cached

        Returns:
            TrackLayout with segment definitions
        """
        # Get session info
        session = self.telemetry_manager.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        track_name = session.track_name or "Unknown"
        track_layout = session.track_layout

        # Check cache first
        if not force_regenerate:
            cached_layout = self.segment_cache.get_layout(track_name, track_layout, version=1)
            if cached_layout:
                logger.info(f"Using cached layout for {track_name}")
                return cached_layout

        # Need to detect new layout
        logger.info(f"Detecting new layout for {track_name}")

        # Get laps and select reference
        laps = self._get_service_for_session(session_id).get_laps()
        if not laps:
            raise ValueError(f"No laps found in session {session_id}")

        # Get signals for reference lap selection (if we have steering/brake)
        steering_signal: SignalSlice | None = None
        brake_signal: SignalSlice | None = None

        try:
            steering_data = self.signal_service.get_lap_signals(
                session_id=session_id,
                lap_number=laps[0].lap_number,
                channels=["Steering Pos"],
                normalize_time=True,
                use_distance=False,
            )
            if steering_data:
                steering_signal = steering_data[0]
        except Exception:
            pass

        try:
            brake_data = self.signal_service.get_lap_signals(
                session_id=session_id,
                lap_number=laps[0].lap_number,
                channels=["Brake Pos"],
                normalize_time=True,
                use_distance=False,
            )
            if brake_data:
                brake_signal = brake_data[0]
        except Exception:
            pass

        # Select reference lap
        ref_lap_number = self.reference_selector.select_reference_lap(
            laps=laps,
            steering_signal=steering_signal,
            brake_signal=brake_signal,
            preferred_lap=preferred_lap,
        )

        if ref_lap_number is None:
            raise ValueError(f"Could not select reference lap for {session_id}")

        logger.info(f"Using reference lap {ref_lap_number} for layout detection")

        # Get signals for layout detection (full sampling, no downsampling)
        channels = ["Steering Pos", "Brake Pos", "Throttle Pos", "Ground Speed", "Lap Dist"]
        signals = self.signal_service.get_lap_signals(
            session_id=session_id,
            lap_number=ref_lap_number,
            channels=channels,
            normalize_time=True,
            use_distance=False,
            sampling_percent=100,
        )

        signal_map = {s.channel: s for s in signals}

        # Detect layout
        layout = self.layout_service.detect_layout(
            track_name=track_name,
            track_layout=track_layout,
            steering_signal=signal_map.get("Steering Pos"),
            brake_signal=signal_map.get("Brake Pos"),
            throttle_signal=signal_map.get("Throttle Pos"),
            speed_signal=signal_map.get("Ground Speed"),
            lap_dist_signal=signal_map.get("Lap Dist"),
            lap_number=ref_lap_number,
            session_id=session_id,
        )

        # Cache layout
        self.segment_cache.save_layout(layout)

        return layout

    def get_lap_metrics(
        self,
        session_id: str,
        lap_number: int,
        force_recompute: bool = False,
    ) -> LapSegmentMetrics:
        """Get segment metrics for a specific lap.

        Args:
            session_id: Session identifier
            lap_number: Lap number
            force_recompute: Force recalculation even if cached

        Returns:
            LapSegmentMetrics with per-segment data
        """
        # Get layout
        layout = self.get_or_create_layout(session_id)

        # Check cache
        if not force_recompute:
            cached_metrics = self.segment_cache.get_lap_metrics(
                session_id, lap_number, layout.version
            )
            if cached_metrics:
                logger.debug(f"Using cached metrics for {session_id} lap {lap_number}")
                return cached_metrics

        # Calculate metrics
        logger.info(f"Calculating metrics for {session_id} lap {lap_number}")

        # Get all required signals (full sampling, no downsampling)
        channels = ["Steering Pos", "Brake Pos", "Throttle Pos", "Ground Speed", "Lap Dist"]
        signals = self.signal_service.get_lap_signals(
            session_id=session_id,
            lap_number=lap_number,
            channels=channels,
            normalize_time=True,
            use_distance=False,
            sampling_percent=100,
        )

        signal_map = {s.channel: s for s in signals}

        # Get lap info for lap time
        laps = self._get_service_for_session(session_id).get_laps()
        lap = self._find_lap(laps, lap_number)

        # Get reference metrics for time deltas
        reference_metrics = None
        if lap_number != layout.reference_lap_number:
            try:
                reference_metrics = self.get_lap_metrics(
                    session_id, layout.reference_lap_number, force_recompute=False
                )
            except Exception as e:
                logger.warning(f"Could not get reference metrics: {e}")

        # Calculate metrics
        metrics = self.metrics_calculator.calculate_lap_metrics(
            session_id=session_id,
            lap_number=lap_number,
            layout=layout,
            signals=signal_map,
            lap_time=lap.lap_time,
            reference_metrics=reference_metrics,
        )

        # Cache metrics
        self.segment_cache.save_lap_metrics(metrics)

        return metrics

    def compare_laps(
        self,
        session_id: str,
        request: SegmentComparisonRequest,
    ) -> SegmentComparisonResponse:
        """Compare segments between two laps.

        Args:
            session_id: Session identifier
            request: Comparison request with target and reference lap numbers

        Returns:
            SegmentComparisonResponse with per-segment comparisons
        """
        # Get layout
        layout = self.get_or_create_layout(session_id)

        # Get metrics for both laps
        target_metrics = self.get_lap_metrics(session_id, request.target_lap)
        reference_metrics = self.get_lap_metrics(session_id, request.reference_lap)

        # Create lookup by segment_id
        target_lookup = {seg.segment_id: seg for seg in target_metrics.segments}
        ref_lookup = {seg.segment_id: seg for seg in reference_metrics.segments}

        # Compare segments
        comparisons: list[SegmentComparison] = []
        time_deltas: list[tuple[str, float]] = []

        segment_ids = request.segment_ids or [seg.segment_id for seg in layout.segments]

        for seg_id in segment_ids:
            target_seg = target_lookup.get(seg_id)
            ref_seg = ref_lookup.get(seg_id)

            if not target_seg or not ref_seg:
                continue

            time_delta = target_seg.segment_time - ref_seg.segment_time
            time_deltas.append((seg_id, time_delta))

            min_speed_delta = None
            if target_seg.min_speed is not None and ref_seg.min_speed is not None:
                min_speed_delta = target_seg.min_speed - ref_seg.min_speed

            # Generate key differences
            key_diffs: list[str] = []
            if time_delta > 0.5:
                key_diffs.append(f"{time_delta:.2f}s slower")
            elif time_delta < -0.5:
                key_diffs.append(f"{abs(time_delta):.2f}s faster")

            if min_speed_delta is not None and abs(min_speed_delta) > 5:
                if min_speed_delta > 0:
                    key_diffs.append(f"{min_speed_delta:.1f} km/h faster min")
                else:
                    key_diffs.append(f"{abs(min_speed_delta):.1f} km/h slower min")

            comparisons.append(
                SegmentComparison(
                    segment_id=seg_id,
                    target_lap=request.target_lap,
                    reference_lap=request.reference_lap,
                    target_time=target_seg.segment_time,
                    reference_time=ref_seg.segment_time,
                    time_delta=time_delta,
                    target_min_speed=target_seg.min_speed,
                    reference_min_speed=ref_seg.min_speed,
                    min_speed_delta=min_speed_delta,
                    key_differences=key_diffs,
                )
            )

        # Sort by time delta to find biggest losses/gains
        time_deltas.sort(key=lambda x: x[1], reverse=True)
        largest_losses = [seg_id for seg_id, delta in time_deltas[:3] if delta > 0]
        largest_gains = [seg_id for seg_id, delta in time_deltas[-3:] if delta < 0]

        # Calculate total delta
        total_delta = sum(delta for _, delta in time_deltas)

        return SegmentComparisonResponse(
            session_id=session_id,
            target_lap=request.target_lap,
            reference_lap=request.reference_lap,
            track_length=layout.track_length,
            total_time_delta=total_delta,
            comparisons=comparisons,
            largest_time_loss_segments=largest_losses,
            largest_time_gain_segments=largest_gains,
        )

    def get_segments_for_lap(
        self,
        session_id: str,
        lap_number: int,
    ) -> list[Segment]:
        """Get segment definitions for a lap (without metrics).

        Args:
            session_id: Session identifier
            lap_number: Lap number

        Returns:
            List of Segment definitions
        """
        layout = self.get_or_create_layout(session_id)
        return layout.segments
