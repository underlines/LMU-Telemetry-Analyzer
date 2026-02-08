"""Metrics calculator for per-segment telemetry analysis.

Computes derived metrics for each segment:
- Speed metrics (entry, mid, exit, min, max, avg)
- Time metrics (segment time, delta to reference)
- Technique metrics (braking distance, throttle application, steering smoothness)
"""

import logging

from app.core.distance_normalizer import DistanceNormalizer
from app.models.segment import (
    LapSegmentMetrics,
    NormalizedDistance,
    Segment,
    SegmentMetrics,
    TrackLayout,
)
from app.models.signal import SignalSlice

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculator for per-segment metrics."""

    def __init__(self) -> None:
        """Initialize calculator."""
        self.distance_normalizer = DistanceNormalizer()

    def calculate_lap_metrics(
        self,
        session_id: str,
        lap_number: int,
        layout: TrackLayout,
        signals: dict[str, SignalSlice],
        lap_time: float | None = None,
        reference_metrics: LapSegmentMetrics | None = None,
    ) -> LapSegmentMetrics:
        """Calculate all segment metrics for a lap.

        Args:
            session_id: Session identifier
            lap_number: Lap number
            layout: Track layout with segment boundaries
            signals: Dict of signals including 'Speed', 'Brake', 'Throttle', 'Steering'
            lap_time: Total lap time (if available)
            reference_metrics: Reference lap metrics for delta calculation

        Returns:
            LapSegmentMetrics with per-segment data
        """
        # Get LapDist and normalize
        lap_dist_signal = signals.get("LapDist")
        if lap_dist_signal is None:
            raise ValueError("LapDist signal required for metrics calculation")

        normalized = self.distance_normalizer.normalize(lap_dist_signal.values)

        # Calculate metrics for each segment
        segment_metrics = []
        total_segment_time = 0.0

        for segment in layout.segments:
            metrics = self._calculate_segment_metrics(
                segment=segment,
                normalized=normalized,
                signals=signals,
            )
            segment_metrics.append(metrics)
            total_segment_time += metrics.segment_time

        # Calculate time deltas if reference provided
        if reference_metrics:
            segment_metrics = self._calculate_time_deltas(
                segment_metrics, reference_metrics
            )

        return LapSegmentMetrics(
            session_id=session_id,
            lap_number=lap_number,
            layout_version=layout.version,
            track_length=layout.track_length,
            total_time=lap_time or total_segment_time,
            segments=segment_metrics,
        )

    def _calculate_segment_metrics(
        self,
        segment: Segment,
        normalized: NormalizedDistance,
        signals: dict[str, SignalSlice],
    ) -> SegmentMetrics:
        """Calculate metrics for a single segment."""
        # Find indices for segment boundaries
        start_idx = self._find_index_for_distance(normalized, segment.start_dist)
        end_idx = self._find_index_for_distance(normalized, segment.end_dist)

        if start_idx >= end_idx:
            # Handle wrap-around (segment crosses S/F)
            indices = list(range(start_idx, len(normalized.normalized_distances)))
            indices.extend(range(0, end_idx))
        else:
            indices = list(range(start_idx, end_idx))

        if not indices:
            return SegmentMetrics(
                segment_id=segment.segment_id,
                lap_number=0,  # Will be set by caller
                session_id="",  # Will be set by caller
                segment_time=0.0,
                entry_speed=None,
                mid_speed=None,
                exit_speed=None,
                min_speed=None,
                max_speed=None,
                time_delta_to_reference=None,
                braking_distance=None,
                max_brake_pressure=None,
                throttle_application=None,
                steering_smoothness=None,
                avg_speed=None,
            )

        # Extract signal values for this segment
        speed_values = self._extract_values(signals.get("Speed"), indices)
        brake_values = self._extract_values(signals.get("Brake"), indices)
        throttle_values = self._extract_values(signals.get("Throttle"), indices)
        steering_values = self._extract_values(signals.get("Steering"), indices)

        # Speed metrics
        entry_speed = self._get_speed_at_distance(signals.get("Speed"), normalized, segment.start_dist)
        mid_dist = (segment.start_dist + segment.end_dist) / 2
        mid_speed = self._get_speed_at_distance(signals.get("Speed"), normalized, mid_dist)
        exit_speed = self._get_speed_at_distance(signals.get("Speed"), normalized, segment.end_dist)
        min_speed = min(speed_values) if speed_values else None
        max_speed = max(speed_values) if speed_values else None
        avg_speed = sum(speed_values) / len(speed_values) if speed_values else None

        # Segment time calculation
        segment_time = self._calculate_segment_time(normalized, indices)

        # Technique metrics
        braking_distance = self._calculate_braking_distance(
            brake_values, normalized, indices, segment.start_dist
        )
        max_brake = max(brake_values) if brake_values else None
        throttle_app = self._calculate_throttle_application(
            throttle_values, normalized, indices, segment.end_dist
        )
        steering_smoothness = self._calculate_steering_smoothness(steering_values)

        return SegmentMetrics(
            segment_id=segment.segment_id,
            lap_number=0,  # Set by caller
            session_id="",  # Set by caller
            entry_speed=entry_speed,
            mid_speed=mid_speed,
            exit_speed=exit_speed,
            min_speed=min_speed,
            max_speed=max_speed,
            segment_time=segment_time,
            time_delta_to_reference=None,
            braking_distance=braking_distance,
            max_brake_pressure=max_brake,
            throttle_application=throttle_app,
            steering_smoothness=steering_smoothness,
            avg_speed=avg_speed,
        )

    def _find_index_for_distance(
        self,
        normalized: NormalizedDistance,
        target_dist: float,
    ) -> int:
        """Find closest index for a target distance."""
        best_idx = 0
        best_diff = abs(normalized.normalized_distances[0] - target_dist)

        for i, dist in enumerate(normalized.normalized_distances):
            diff = abs(dist - target_dist)
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        return best_idx

    def _extract_values(
        self,
        signal: SignalSlice | None,
        indices: list[int],
    ) -> list[float]:
        """Extract values at specific indices from a signal."""
        if signal is None or not signal.values:
            return []

        values = []
        for idx in indices:
            if 0 <= idx < len(signal.values):
                values.append(signal.values[idx])
        return values

    def _get_speed_at_distance(
        self,
        speed_signal: SignalSlice | None,
        normalized: NormalizedDistance,
        target_dist: float,
    ) -> float | None:
        """Get speed at a specific distance."""
        if speed_signal is None or not speed_signal.values:
            return None

        idx = self._find_index_for_distance(normalized, target_dist)
        if 0 <= idx < len(speed_signal.values):
            return speed_signal.values[idx]
        return None

    def _calculate_segment_time(
        self,
        normalized: NormalizedDistance,
        indices: list[int],
    ) -> float:
        """Calculate time spent in segment."""
        if len(indices) < 2:
            return 0.0

        # Use normalized distances and assume constant speed interpolation
        # For more accuracy, we could use actual timestamps
        first_idx = indices[0]
        last_idx = indices[-1]

        if first_idx < len(normalized.normalized_distances) and last_idx < len(normalized.normalized_distances):
            # Estimate time based on typical sampling rate
            # This is a simplification - ideally we'd use actual timestamps
            num_points = len(indices)
            if num_points > 0:
                # Assume ~60Hz sampling
                return num_points / 60.0

        return 0.0

    def _calculate_braking_distance(
        self,
        brake_values: list[float],
        normalized: NormalizedDistance,
        indices: list[int],
        entry_dist: float,
    ) -> float | None:
        """Calculate braking distance before entry."""
        if not brake_values or not indices:
            return None

        brake_threshold = 0.1

        # Find first braking point in segment
        for i, brake in enumerate(brake_values):
            if brake > brake_threshold:
                brake_idx = indices[i]
                if brake_idx < len(normalized.normalized_distances):
                    brake_dist = normalized.normalized_distances[brake_idx]
                    return entry_dist - brake_dist

        return None

    def _calculate_throttle_application(
        self,
        throttle_values: list[float],
        normalized: NormalizedDistance,
        indices: list[int],
        exit_dist: float,
    ) -> float | None:
        """Calculate distance from exit to full throttle."""
        if not throttle_values or not indices:
            return None

        throttle_full = 0.95

        # Find full throttle point after segment
        for i, throttle in enumerate(throttle_values):
            if throttle >= throttle_full:
                throttle_idx = indices[i]
                if throttle_idx < len(normalized.normalized_distances):
                    throttle_dist = normalized.normalized_distances[throttle_idx]
                    return throttle_dist - exit_dist

        return None

    def _calculate_steering_smoothness(self, steering_values: list[float]) -> float | None:
        """Calculate steering smoothness (std dev of rate)."""
        if len(steering_values) < 2:
            return None

        # Calculate steering rate
        rates = [abs(steering_values[i] - steering_values[i - 1]) for i in range(1, len(steering_values))]

        if not rates:
            return None

        # Standard deviation
        mean_rate = sum(rates) / len(rates)
        variance = sum((r - mean_rate) ** 2 for r in rates) / len(rates)
        return float(variance ** 0.5)

    def _calculate_time_deltas(
        self,
        segment_metrics: list[SegmentMetrics],
        reference_metrics: LapSegmentMetrics,
    ) -> list[SegmentMetrics]:
        """Calculate time deltas vs reference lap."""
        # Create lookup by segment_id
        ref_lookup = {seg.segment_id: seg for seg in reference_metrics.segments}

        for seg_metric in segment_metrics:
            ref_seg = ref_lookup.get(seg_metric.segment_id)
            if ref_seg and ref_seg.segment_time > 0:
                delta = seg_metric.segment_time - ref_seg.segment_time
                seg_metric.time_delta_to_reference = delta

        return segment_metrics
