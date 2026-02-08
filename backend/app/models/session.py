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

    model_config = {
        "json_schema_extra": {
            "example": {
                "lap_number": 3,
                "start_time": 125.5,
                "end_time": 229.3,
                "lap_time": 103.8,
                "valid": True
            }
        }
    }


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

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "session_2026-02-07_22-56-50",
                "file_path": "/path/to/session.duckdb",
                "recording_time": "2026-02-07T22:56:50Z",
                "session_time": "22:56",
                "session_type": "Practice",
                "track_name": "Le Mans",
                "track_layout": "24h",
                "driver_name": "DriverName",
                "car_name": "Toyota GR010 Hybrid",
                "car_class": "Hypercar",
                "weather_conditions": "Clear",
                "lap_count": 12
            }
        }
    }


class SessionList(BaseModel):
    """Response model for listing sessions."""

    sessions: list[Session]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "sessions": [
                    {
                        "id": "session_2026-02-07_22-56-50",
                        "file_path": "/path/to/session.duckdb",
                        "recording_time": "2026-02-07T22:56:50Z",
                        "session_time": "22:56",
                        "session_type": "Practice",
                        "track_name": "Le Mans",
                        "track_layout": "24h",
                        "driver_name": "DriverName",
                        "car_name": "Toyota GR010 Hybrid",
                        "car_class": "Hypercar",
                        "weather_conditions": "Clear",
                        "lap_count": 12
                    }
                ],
                "total": 1
            }
        }
    }


class LapList(BaseModel):
    """Response model for listing laps in a session."""

    session_id: str
    laps: list[Lap]
    total: int

    model_config = {
        "json_schema_extra": {
            "example": {
                "session_id": "session_2026-02-07_22-56-50",
                "laps": [
                    {
                        "lap_number": 1,
                        "start_time": 45.2,
                        "end_time": 148.5,
                        "lap_time": 103.3,
                        "valid": True
                    },
                    {
                        "lap_number": 2,
                        "start_time": 148.5,
                        "end_time": 251.0,
                        "lap_time": 102.5,
                        "valid": True
                    }
                ],
                "total": 2
            }
        }
    }


class SessionDetail(Session):
    """Extended session information including available signals."""

    channels: list[dict[str, Any]] = Field(
        default_factory=list, description="Available telemetry channels"
    )
    events: list[dict[str, Any]] = Field(
        default_factory=list, description="Available telemetry events"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "session_2026-02-07_22-56-50",
                "file_path": "/path/to/session.duckdb",
                "recording_time": "2026-02-07T22:56:50Z",
                "session_time": "22:56",
                "session_type": "Practice",
                "track_name": "Le Mans",
                "track_layout": "24h",
                "driver_name": "DriverName",
                "car_name": "Toyota GR010 Hybrid",
                "car_class": "Hypercar",
                "weather_conditions": "Clear",
                "lap_count": 12,
                "channels": [
                    {"name": "Speed", "frequency": 60, "unit": "m/s"},
                    {"name": "Throttle", "frequency": 60, "unit": "%"},
                    {"name": "Brake", "frequency": 60, "unit": "%"},
                    {"name": "Steering", "frequency": 60, "unit": "rad"}
                ],
                "events": [
                    {"name": "Lap", "unit": ""},
                    {"name": "Sector", "unit": ""}
                ]
            }
        }
    }
