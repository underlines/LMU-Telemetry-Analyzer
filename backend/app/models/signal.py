from __future__ import annotations

from pydantic import BaseModel, Field


class SignalMetadata(BaseModel):
    """Metadata for a telemetry signal/channel."""

    name: str = Field(..., description="Signal name/channel name")
    frequency: int = Field(..., description="Sampling frequency in Hz")
    unit: str | None = Field(None, description="Unit of measurement")
    min_value: float | None = Field(None, description="Minimum value in dataset")
    max_value: float | None = Field(None, description="Maximum value in dataset")

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Speed",
                "frequency": 60,
                "unit": "m/s",
                "min_value": 0.0,
                "max_value": 95.5
            }
        }
    }


class SignalData(BaseModel):
    """Raw signal data with timestamps and values."""

    channel: str = Field(..., description="Channel/signal name")
    timestamps: list[float] = Field(
        default_factory=list, description="Time values in seconds (session time)"
    )
    values: list[float] = Field(default_factory=list, description="Signal values")
    unit: str | None = Field(None, description="Unit of measurement")
    total_samples: int = Field(0, description="Original sample count before downsampling")


class SignalSlice(BaseModel):
    """A slice of signal data for a specific lap."""

    channel: str = Field(..., description="Channel/signal name")
    lap_number: int = Field(..., description="Lap number this slice belongs to")
    session_id: str = Field(..., description="Session identifier")

    # Time-based data
    timestamps: list[float] = Field(
        default_factory=list, description="Session timestamps (seconds)"
    )
    normalized_time: list[float] = Field(
        default_factory=list, description="Time normalized to lap start (0 = lap start)"
    )
    values: list[float] = Field(default_factory=list, description="Signal values")

    # Distance-based data (if available)
    distance: list[float] | None = Field(
        None, description="Distance traveled in meters (if available)"
    )

    unit: str | None = Field(None, description="Unit of measurement")
    sampling_rate: int = Field(0, description="Actual sampling rate of this slice")
    total_samples: int = Field(0, description="Original sample count before downsampling")


class SignalList(BaseModel):
    """Response model for listing available signals."""

    session_id: str
    signals: list[SignalMetadata]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_2026-02-07_22-56-50",
                "signals": [
                    {
                        "name": "Speed",
                        "frequency": 60,
                        "unit": "m/s",
                        "min_value": 0.0,
                        "max_value": 95.5
                    },
                    {
                        "name": "Throttle",
                        "frequency": 60,
                        "unit": "%",
                        "min_value": 0.0,
                        "max_value": 1.0
                    }
                ],
                "total": 2
            }
        }
    }


class SignalRequest(BaseModel):
    """Request model for fetching signal data."""

    channels: list[str] = Field(..., description="List of channel names to fetch")
    normalize_time: bool = Field(
        True, description="Whether to normalize time to lap start"
    )
    use_distance: bool = Field(
        False, description="Whether to use distance instead of time for X-axis"
    )
    max_points: int | None = Field(
        None, description="Maximum number of points to return (for downsampling)"
    )


class LapComparisonRequest(BaseModel):
    """Request model for comparing laps."""

    target_lap: int = Field(..., description="Target lap number to analyze")
    reference_lap: int = Field(..., description="Reference lap number for comparison")
    channels: list[str] = Field(..., description="List of channel names to compare")
    normalize_time: bool = Field(
        True, description="Whether to normalize time to lap start"
    )
    use_distance: bool = Field(
        False, description="Whether to use distance instead of time for X-axis"
    )
    sampling_percent: int = Field(
        20, ge=1, le=100, description="Sampling percentage (1-100%) for downsampling"
    )


class LapComparison(BaseModel):
    """Comparison data for a single channel across two laps."""

    channel: str = Field(..., description="Channel name")
    unit: str | None = Field(None, description="Unit of measurement")

    # Target lap data
    target_lap: int = Field(..., description="Target lap number")
    target_timestamps: list[float] = Field(default_factory=list)
    target_values: list[float] = Field(default_factory=list)
    target_distance: list[float] | None = None

    # Reference lap data
    reference_lap: int = Field(..., description="Reference lap number")
    reference_timestamps: list[float] = Field(default_factory=list)
    reference_values: list[float] = Field(default_factory=list)
    reference_distance: list[float] | None = None

    # Normalized X-axis values
    normalized_x: list[float] = Field(
        default_factory=list, description="Normalized time or distance"
    )


class ComparisonResponse(BaseModel):
    """Response model for lap comparison."""

    session_id: str
    target_lap: int
    reference_lap: int
    comparisons: list[LapComparison]
