"""Distance normalization for Lap Dist signals.

Converts Lap Dist to monotonic 0..track_length coordinates.
Handles wrap-around at start/finish and negative value artifacts.
"""

import logging

from app.models.segment import NormalizedDistance

logger = logging.getLogger(__name__)


class DistanceNormalizer:
    """Normalizes Lap Dist signals to monotonic track coordinates."""

    # Threshold for detecting wrap-around (meters)
    WRAP_THRESHOLD: float = 50.0
    # Threshold for detecting negative jumps (artifacts)
    NEGATIVE_JUMP_THRESHOLD: float = 10.0

    def normalize(
        self,
        lap_distances: list[float],
        lap_start_offset: float = 0.0,
    ) -> NormalizedDistance:
        """Convert Lap Dist to monotonic 0..track_length.

        Algorithm:
        1. Detect track length (max value before wrap)
        2. Detect wrap-around points (sudden drop > WRAP_THRESHOLD)
        3. Accumulate offset at each wrap to maintain monotonicity
        4. Handle negative values by clamping to 0 or interpolation

        Args:
            lap_distances: Raw Lap Dist values from telemetry
            lap_start_offset: Starting offset for multi-lap continuity

        Returns:
            NormalizedDistance with monotonic distances and metadata
        """
        if not lap_distances:
            return NormalizedDistance(
                original_distances=[],
                normalized_distances=[],
                track_length=0.0,
                wrap_points=[],
            )

        if len(lap_distances) < 2:
            return NormalizedDistance(
                original_distances=list(lap_distances),
                normalized_distances=[lap_start_offset],
                track_length=max(lap_distances) if lap_distances else 0.0,
                wrap_points=[],
            )

        # Track length is the maximum value before any wrap
        # We detect this from the first few non-negative values
        track_length = self._estimate_track_length(lap_distances)

        normalized: list[float] = []
        wrap_points: list[int] = []
        accumulated_offset = lap_start_offset

        for i, dist in enumerate(lap_distances):
            # Handle negative values (artifacts)
            if dist < 0:
                if i == 0:
                    # First point negative - clamp to 0
                    normalized.append(accumulated_offset)
                else:
                    # Interpolate from previous valid point
                    prev_valid = normalized[-1]
                    next_valid = self._find_next_valid(lap_distances, i)
                    if next_valid is not None:
                        # Simple linear interpolation
                        interp = prev_valid + (next_valid - prev_valid) * 0.5
                        normalized.append(interp)
                    else:
                        # No valid future point, clamp to previous
                        normalized.append(prev_valid)
                continue

            # Detect wrap-around (sudden large drop)
            if i > 0 and lap_distances[i - 1] >= 0:
                prev_dist = lap_distances[i - 1]
                drop = prev_dist - dist

                if drop > self.WRAP_THRESHOLD:
                    # Wrap detected - add track length to offset
                    wrap_points.append(i)
                    accumulated_offset += track_length
                    logger.debug(f"Wrap at index {i}: {prev_dist:.1f} -> {dist:.1f}")
                elif dist < prev_dist - self.NEGATIVE_JUMP_THRESHOLD:
                    # Negative jump (artifact) - interpolate
                    if normalized:
                        normalized.append(normalized[-1])
                        continue

            normalized.append(dist + accumulated_offset)

        return NormalizedDistance(
            original_distances=list(lap_distances),
            normalized_distances=normalized,
            track_length=track_length,
            wrap_points=wrap_points,
        )

    def _estimate_track_length(self, lap_distances: list[float]) -> float:
        """Estimate track length from Lap Dist values.

        Finds the maximum reasonable value before any wrap.
        Ignores negative values and outliers.
        """
        valid_distances = [d for d in lap_distances if d >= 0]
        if not valid_distances:
            return 0.0

        # Look for sudden drops to detect wrap
        max_val = valid_distances[0]
        for i in range(1, len(valid_distances)):
            if valid_distances[i] < valid_distances[i - 1] - self.WRAP_THRESHOLD:
                # Wrap detected - max before this point is track length
                break
            max_val = max(max_val, valid_distances[i])

        return max_val

    def _find_next_valid(self, lap_distances: list[float], start_idx: int) -> float | None:
        """Find next non-negative distance value."""
        for i in range(start_idx + 1, len(lap_distances)):
            if lap_distances[i] >= 0:
                return lap_distances[i]
        return None

    def map_to_track_position(
        self,
        normalized_distance: NormalizedDistance,
        target_dist: float,
    ) -> int:
        """Find the index closest to a target track distance.

        Args:
            normalized_distance: Normalized distance data
            target_dist: Target distance in meters from S/F

        Returns:
            Index of closest sample
        """
        if not normalized_distance.normalized_distances:
            return 0

        best_idx = 0
        best_diff = abs(normalized_distance.normalized_distances[0] - target_dist)

        for i, dist in enumerate(normalized_distance.normalized_distances):
            diff = abs(dist - target_dist)
            if diff < best_diff:
                best_diff = diff
                best_idx = i

        return best_idx

    def get_distance_at_index(
        self,
        normalized_distance: NormalizedDistance,
        idx: int,
    ) -> float | None:
        """Get normalized distance at a specific index.

        Args:
            normalized_distance: Normalized distance data
            idx: Index to query

        Returns:
            Distance value or None if out of range
        """
        if 0 <= idx < len(normalized_distance.normalized_distances):
            return normalized_distance.normalized_distances[idx]
        return None
