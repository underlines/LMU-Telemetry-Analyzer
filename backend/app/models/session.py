from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Lap(BaseModel):
    """Represents a single lap within a telemetry session."""

    lap_number: int = Field(..., description="Lap number (0 is typically out/in lap)")
    start_time: float = Field(..., description="Session time when lap started (seconds)")
    end_time: float | None = Field(None, description="Session time when lap ended (seconds)")
    lap_time: float | None = Field(None, description="Lap time in seconds")
    valid: bool = Field(True, description="Whether the lap was valid (no off-track/cuts)")


class Session(BaseModel):
    """Represents a telemetry recording session from a single DuckDB file."""

    id: str = Field(..., description="Unique session identifier (filename without extension)")
    file_path: Path = Field(..., description="Path to the DuckDB file")
    recording_time: datetime | None = Field(
        None, description="When the telemetry was recorded (from metadata)"
    )
    session_time: str | None = Field(None, description="In-game session time")
    session_type: str | None = Field(
        None, description="Type of session (Practice, Qualifying, Race, etc.)"
    )
    track_name: str | None = Field(None, description="Track name")
    track_layout: str | None = Field(None, description="Track layout variant")
    driver_name: str | None = Field(None, description="Driver name from Steam")
    car_name: str | None = Field(None, description="Car/vehicle name")
    car_class: str | None = Field(None, description="Car class (GT3, LMP2, etc.)")
    weather_conditions: str | None = Field(None, description="Weather conditions")
    lap_count: int = Field(0, description="Number of laps recorded")

    @field_validator("file_path", mode="before")
    @classmethod
    def validate_path(cls, v: Any) -> Any:
        if isinstance(v, str):
            return Path(v)
        return v


class SessionList(BaseModel):
    """Response model for listing sessions."""

    sessions: list[Session]
    total: int


class LapList(BaseModel):
    """Response model for listing laps in a session."""

    session_id: str
    laps: list[Lap]
    total: int


class SessionDetail(Session):
    """Extended session information including available signals."""

    channels: list[dict[str, Any]] = Field(
        default_factory=list, description="Available telemetry channels"
    )
    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Available telemetry events"
    )
