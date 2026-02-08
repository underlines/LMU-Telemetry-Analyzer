"""Models for track segmentation and derived metrics."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Segment(BaseModel):
    """A meaningful subdivision of a lap (corner, straight, or complex)."""

    segment_id: str = Field(..., description="Unique identifier (e.g., 'T1', 'T2-3', 'S1')")
    segment_type: Literal["corner", "straight", "complex"] = Field(
        ..., description="Type of driving section"
    )
    start_dist: float = Field(..., description="Start distance in meters from S/F line")
    end_dist: float = Field(..., description="End distance in meters from S/F line")
    entry_dist: float | None = Field(None, description="Braking/turn-in point distance")
    apex_dist: float | None = Field(None, description="Apex point distance")
    exit_dist: float | None = Field(None, description="Full throttle point distance")


class TrackLayout(BaseModel):
    """Track layout with distance-based segment boundaries."""

    track_name: str = Field(..., description="Track name")
    track_layout: str | None = Field(None, description="Track layout variant")
    version: int = Field(1, description="Layout version for cache invalidation")
    track_length: float = Field(..., description="Track length in meters")
    segments: list[Segment] = Field(default_factory=list, description="Track segments")
    reference_lap_number: int = Field(..., description="Lap used for detection")
    reference_session_id: str = Field(..., description="Session used for detection")


class SegmentMetrics(BaseModel):
    """Derived metrics for a single segment in a lap."""

    segment_id: str = Field(..., description="Segment identifier")
    lap_number: int = Field(..., description="Lap number")
    session_id: str = Field(..., description="Session identifier")

    # Speed metrics (m/s or km/h - use signal units)
    entry_speed: float | None = Field(None, description="Speed at segment entry")
    mid_speed: float | None = Field(None, description="Speed at segment midpoint")
    exit_speed: float | None = Field(None, description="Speed at segment exit")
    min_speed: float | None = Field(None, description="Minimum speed in segment")
    max_speed: float | None = Field(None, description="Maximum speed in segment")

    # Time metrics
    segment_time: float = Field(..., description="Time spent in segment (seconds)")
    time_delta_to_reference: float | None = Field(
        None, description="Time delta vs reference lap (positive = slower)"
    )

    # Technique metrics
    braking_distance: float | None = Field(
        None, description="Distance from braking start to entry (meters)"
    )
    max_brake_pressure: float | None = Field(None, description="Maximum brake pressure")
    throttle_application: float | None = Field(
        None, description="Distance from exit to full throttle (meters, 0 = good)"
    )
    steering_smoothness: float | None = Field(
        None, description="Standard deviation of steering rate (lower = smoother)"
    )

    # Derived data
    avg_speed: float | None = Field(None, description="Average speed through segment")


class LapSegmentMetrics(BaseModel):
    """All segment metrics for a single lap."""

    session_id: str = Field(..., description="Session identifier")
    lap_number: int = Field(..., description="Lap number")
    layout_version: int = Field(..., description="Layout version used")
    track_length: float = Field(..., description="Track length in meters")
    total_time: float | None = Field(None, description="Total lap time")
    segments: list[SegmentMetrics] = Field(default_factory=list, description="Per-segment metrics")


class SegmentComparisonRequest(BaseModel):
    """Request model for comparing segments between laps."""

    target_lap: int = Field(..., description="Target lap number")
    reference_lap: int = Field(..., description="Reference lap number")
    segment_ids: list[str] | None = Field(
        None, description="Specific segments to compare (None = all)"
    )


class SegmentComparison(BaseModel):
    """Comparison of a single segment between two laps."""

    segment_id: str = Field(..., description="Segment identifier")
    target_lap: int = Field(..., description="Target lap number")
    reference_lap: int = Field(..., description="Reference lap number")

    # Time comparison
    target_time: float = Field(..., description="Target lap segment time")
    reference_time: float = Field(..., description="Reference lap segment time")
    time_delta: float = Field(..., description="Time difference (target - reference)")

    # Speed comparison
    target_min_speed: float | None = Field(None, description="Target minimum speed")
    reference_min_speed: float | None = Field(None, description="Reference minimum speed")
    min_speed_delta: float | None = Field(None, description="Min speed difference")

    # Key differences
    key_differences: list[str] = Field(
        default_factory=list, description="Human-readable key differences"
    )


class SegmentComparisonResponse(BaseModel):
    """Response model for segment comparison."""

    session_id: str = Field(..., description="Session identifier")
    target_lap: int = Field(..., description="Target lap number")
    reference_lap: int = Field(..., description="Reference lap number")
    track_length: float = Field(..., description="Track length in meters")
    total_time_delta: float = Field(..., description="Total lap time difference")
    comparisons: list[SegmentComparison] = Field(
        default_factory=list, description="Per-segment comparisons"
    )
    largest_time_loss_segments: list[str] = Field(
        default_factory=list, description="Segments with biggest time losses"
    )
    largest_time_gain_segments: list[str] = Field(
        default_factory=list, description="Segments with biggest time gains"
    )


class NormalizedDistance(BaseModel):
    """Normalized distance data for a lap."""

    original_distances: list[float] = Field(
        default_factory=list, description="Raw LapDist values"
    )
    normalized_distances: list[float] = Field(
        default_factory=list, description="Monotonic 0..track_length values"
    )
    track_length: float = Field(..., description="Detected track length")
    wrap_points: list[int] = Field(
        default_factory=list, description="Indices where wrap-around occurred"
    )
