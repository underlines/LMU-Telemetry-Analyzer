"""Track layout service for segment detection.

Detects corners, straights, and complexes from telemetry signals.
Uses steering, brake, throttle, and speed signals to identify driving sections.

Algorithm:
1. Calculate curvature from steering signal
2. Identify high-curvature zones (corners)
3. Find entry (brake + turn-in), apex (min curvature), exit (throttle) points
4. Join adjacent corners into complexes if within COMPLEX_DISTANCE_THRESHOLD
5. Label remaining sections as straights
"""

import logging
from typing import Any

from app.core.distance_normalizer import DistanceNormalizer
from app.models.segment import NormalizedDistance, Segment, TrackLayout
from app.models.signal import SignalSlice

logger = logging.getLogger(__name__)


class TrackLayoutService:
    """Service for detecting track segments from telemetry."""

    # Detection parameters (tunable)
    CURVATURE_THRESHOLD: float = 0.003  # Steering rate threshold for corner detection
    MIN_CORNER_DURATION: float = 0.5  # Minimum seconds to be considered a corner
    COMPLEX_DISTANCE_THRESHOLD: float = 30.0  # Max meters between corners to merge
    STRAIGHT_MIN_LENGTH: float = 20.0  # Minimum meters to be a straight
    BRAKE_THRESHOLD: float = 0.1  # Brake pressure to detect braking
    THROTTLE_FULL: float = 0.95  # Throttle position considered "full"
    ENTRY_BRAKE_WINDOW: float = 50.0  # Max meters before turn to look for braking
    EXIT_THROTTLE_WINDOW: float = 30.0  # Max meters after turn to look for full throttle

    def __init__(self) -> None:
        """Initialize service."""
        self.distance_normalizer = DistanceNormalizer()

    def detect_layout(
        self,
        track_name: str,
        track_layout: str | None,
        steering_signal: SignalSlice | None,
        brake_signal: SignalSlice | None,
        throttle_signal: SignalSlice | None,
        speed_signal: SignalSlice | None,
        lap_dist_signal: SignalSlice | None,
        lap_number: int,
        session_id: str,
    ) -> TrackLayout:
        """Detect track layout from reference lap signals.

        Args:
            track_name: Track name
            track_layout: Layout variant
            steering_signal: Steering angle signal
            brake_signal: Brake pressure signal
            throttle_signal: Throttle position signal
            speed_signal: Speed signal
            lap_dist_signal: Lap Dist signal (will be normalized)
            lap_number: Reference lap number
            session_id: Reference session ID

        Returns:
            TrackLayout with detected segments
        """
        if lap_dist_signal is None or not lap_dist_signal.values:
            raise ValueError("Lap Dist signal is required for layout detection")

        # Normalize distance
        normalized = self.distance_normalizer.normalize(lap_dist_signal.values)
        track_length = normalized.track_length

        logger.info(f"Detecting layout for {track_name}, length: {track_length:.1f}m")

        # Calculate curvature from steering (use dummy if not available)
        if steering_signal is None or not steering_signal.values:
            logger.warning("No steering signal available, using placeholder layout")
            curvature = [0.0] * len(lap_dist_signal.values)
        else:
            curvature = self._calculate_curvature(steering_signal)

        # Detect corner zones from curvature
        corner_zones = self._detect_corner_zones(
            curvature, normalized, self.CURVATURE_THRESHOLD
        )

        logger.info(f"Detected {len(corner_zones)} corner zones")

        # Enhance corners with entry/apex/exit points
        enhanced_corners = []
        for zone in corner_zones:
            corner = self._enhance_corner(
                zone, normalized, steering_signal, brake_signal, throttle_signal
            )
            enhanced_corners.append(corner)

        # Merge nearby corners into complexes
        merged_segments = self._merge_adjacent_corners(enhanced_corners, track_length)

        # Fill in straights between corners
        all_segments = self._fill_straights(merged_segments, track_length)

        # Sort by start distance
        all_segments.sort(key=lambda s: s.start_dist)

        # Generate segment IDs
        all_segments = self._generate_segment_ids(all_segments)

        logger.info(f"Final layout: {len(all_segments)} segments")

        return TrackLayout(
            track_name=track_name,
            track_layout=track_layout,
            version=1,
            track_length=track_length,
            segments=all_segments,
            reference_lap_number=lap_number,
            reference_session_id=session_id,
        )

    def _calculate_curvature(self, steering_signal: SignalSlice) -> list[float]:
        """Calculate curvature (steering rate) from steering signal.

        Returns:
            List of curvature values (steering change per sample)
        """
        values = steering_signal.values
        if len(values) < 2:
            return [0.0] * len(values)

        # Rate of change of steering
        rates = []
        for i in range(len(values)):
            if i == 0:
                rates.append(0.0)
            else:
                rate = abs(values[i] - values[i - 1])
                rates.append(rate)

        return rates

    def _detect_corner_zones(
        self,
        curvature: list[float],
        normalized: NormalizedDistance,
        threshold: float,
    ) -> list[dict[str, Any]]:
        """Detect corner zones from curvature signal.

        Returns:
            List of corner zones with start_idx, end_idx
        """
        zones = []
        in_corner = False
        start_idx = 0
        start_dist = 0.0

        for i, curv in enumerate(curvature):
            if curv > threshold and not in_corner:
                # Corner start
                in_corner = True
                start_idx = i
                # Initialize start_dist
                if len(normalized.normalized_distances) > start_idx:
                    start_dist = normalized.normalized_distances[start_idx]
            elif curv <= threshold and in_corner:
                # Corner end
                in_corner = False
                end_idx = i

                # Calculate duration
                if len(normalized.normalized_distances) > end_idx:
                    end_dist = normalized.normalized_distances[end_idx]
                    duration = end_dist - start_dist
                else:
                    end_dist = start_dist
                    duration = 0.0

                # Only keep significant corners
                if duration > 10.0:  # At least 10 meters
                    zones.append({
                        "start_idx": start_idx,
                        "end_idx": end_idx,
                        "start_dist": start_dist,
                        "end_dist": end_dist,
                    })

        # Handle corner at end of lap
        if in_corner:
            zones.append({
                "start_idx": start_idx,
                "end_idx": len(curvature) - 1,
                "start_dist": normalized.normalized_distances[start_idx],
                "end_dist": normalized.track_length,
            })

        return zones

    def _enhance_corner(
        self,
        zone: dict[str, Any],
        normalized: NormalizedDistance,
        steering: SignalSlice | None,
        brake: SignalSlice | None,
        throttle: SignalSlice | None,
    ) -> Segment:
        """Enhance corner zone with entry/apex/exit points."""
        start_idx = zone["start_idx"]
        end_idx = zone["end_idx"]
        start_dist = zone["start_dist"]
        end_dist = zone["end_dist"]

        # Find apex: point of maximum steering (minimum radius)
        apex_dist = None
        if steering is not None and steering.values:
            apex_idx = start_idx
            max_steering = 0.0
            for i in range(start_idx, min(end_idx + 1, len(steering.values))):
                if abs(steering.values[i]) > max_steering:
                    max_steering = abs(steering.values[i])
                    apex_idx = i
            if apex_idx < len(normalized.normalized_distances):
                apex_dist = normalized.normalized_distances[apex_idx]

        # Find entry: braking point before turn-in
        entry_dist = None
        if brake is not None and brake.values:
            search_start = max(0, start_idx - int(self.ENTRY_BRAKE_WINDOW))
            for i in range(start_idx, search_start, -1):
                if i < len(brake.values) and brake.values[i] > self.BRAKE_THRESHOLD:
                    entry_dist = normalized.normalized_distances[i]
                    break

        # Find exit: full throttle after apex
        exit_dist = None
        if throttle is not None and throttle.values and apex_dist is not None:
            search_end = min(len(throttle.values), end_idx + int(self.EXIT_THROTTLE_WINDOW))
            for i in range(start_idx, search_end):
                if i < len(throttle.values) and throttle.values[i] >= self.THROTTLE_FULL:
                    exit_dist = normalized.normalized_distances[i]
                    break

        return Segment(
            segment_id="",  # Will be assigned later
            segment_type="corner",
            start_dist=start_dist,
            end_dist=end_dist,
            entry_dist=entry_dist,
            apex_dist=apex_dist,
            exit_dist=exit_dist,
        )

    def _merge_adjacent_corners(
        self,
        corners: list[Segment],
        track_length: float,
    ) -> list[Segment]:
        """Merge adjacent corners into complexes if close together."""
        if len(corners) < 2:
            return corners

        merged = []
        i = 0
        while i < len(corners):
            current = corners[i]

            # Check if next corner is close
            if i + 1 < len(corners):
                next_corner = corners[i + 1]
                gap = next_corner.start_dist - current.end_dist

                # Handle wrap-around
                if gap < 0:
                    gap += track_length

                if gap < self.COMPLEX_DISTANCE_THRESHOLD:
                    # Merge into complex
                    complex_seg = Segment(
                        segment_id="",
                        segment_type="complex",
                        start_dist=current.start_dist,
                        end_dist=next_corner.end_dist,
                        entry_dist=current.entry_dist,
                        apex_dist=None,  # Multiple apexes
                        exit_dist=next_corner.exit_dist,
                    )
                    merged.append(complex_seg)
                    i += 2
                    continue

            merged.append(current)
            i += 1

        return merged

    def _fill_straights(
        self,
        segments: list[Segment],
        track_length: float,
    ) -> list[Segment]:
        """Fill in straights between corners."""
        if not segments:
            # Entire track is a straight
            return [
                Segment(
                    segment_id="S1",
                    segment_type="straight",
                    start_dist=0.0,
                    end_dist=track_length,
                    entry_dist=None,
                    apex_dist=None,
                    exit_dist=None,
                )
            ]

        all_segments = []

        # Sort by start distance
        sorted_segments = sorted(segments, key=lambda s: s.start_dist)

        # Check for straight from start to first corner
        first_start = sorted_segments[0].start_dist
        if first_start > self.STRAIGHT_MIN_LENGTH:
            all_segments.append(
                Segment(
                    segment_id="",
                    segment_type="straight",
                    start_dist=0.0,
                    end_dist=first_start,
                    entry_dist=None,
                    apex_dist=None,
                    exit_dist=None,
                )
            )

        # Add corners and straights between them
        for i, seg in enumerate(sorted_segments):
            all_segments.append(seg)

            # Check for straight to next corner
            if i + 1 < len(sorted_segments):
                next_start = sorted_segments[i + 1].start_dist
                gap = next_start - seg.end_dist

                if gap > self.STRAIGHT_MIN_LENGTH:
                    all_segments.append(
                        Segment(
                            segment_id="",
                            segment_type="straight",
                            start_dist=seg.end_dist,
                            end_dist=next_start,
                            entry_dist=None,
                            apex_dist=None,
                            exit_dist=None,
                        )
                    )

        # Check for straight from last corner to end (with wrap)
        last_end = sorted_segments[-1].end_dist
        first_start = sorted_segments[0].start_dist

        # Distance from last corner end to track end
        gap_to_end = track_length - last_end
        # Distance from track start to first corner
        gap_from_start = first_start
        total_gap = gap_to_end + gap_from_start

        if total_gap > self.STRAIGHT_MIN_LENGTH:
            # This is the main straight (usually)
            all_segments.append(
                Segment(
                    segment_id="",
                    segment_type="straight",
                    start_dist=last_end,
                    end_dist=track_length,  # Will wrap to first_start
                    entry_dist=None,
                    apex_dist=None,
                    exit_dist=None,
                )
            )

        return all_segments

    def _generate_segment_ids(self, segments: list[Segment]) -> list[Segment]:
        """Generate sequential IDs for segments (T1, T2, S1, etc.)."""
        corner_num = 1
        straight_num = 1
        complex_num = 1

        for seg in segments:
            if seg.segment_type == "corner":
                seg.segment_id = f"T{corner_num}"
                corner_num += 1
            elif seg.segment_type == "straight":
                seg.segment_id = f"S{straight_num}"
                straight_num += 1
            elif seg.segment_type == "complex":
                seg.segment_id = f"C{complex_num}"
                complex_num += 1

        return segments
