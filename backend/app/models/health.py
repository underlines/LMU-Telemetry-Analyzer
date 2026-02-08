"""Health check and monitoring models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ServiceCheck(BaseModel):
    """Individual service health check."""

    name: str = Field(..., description="Name of the service/check")
    status: str = Field(..., description="Health status: healthy, unhealthy, unknown")
    response_time_ms: float | None = Field(
        None, description="Response time in milliseconds"
    )
    message: str | None = Field(None, description="Additional details or error message")


class HealthStatus(BaseModel):
    """Overall health status response."""

    status: str = Field(..., description="Overall health: healthy, degraded, unhealthy")
    timestamp: datetime = Field(..., description="UTC timestamp of the health check")
    version: str = Field(..., description="API version")
    checks: list[ServiceCheck] = Field(
        default_factory=list, description="Individual health checks"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2026-02-08T10:30:00Z",
                "version": "0.1.0",
                "checks": [
                    {
                        "name": "duckdb",
                        "status": "healthy",
                        "response_time_ms": 15.2,
                        "message": "DuckDB connectivity OK"
                    },
                    {
                        "name": "cache_directory",
                        "status": "healthy",
                        "response_time_ms": 0.5,
                        "message": "Cache directory accessible"
                    }
                ]
            }
        }
    }


class DependencyStatus(BaseModel):
    """Status of a required dependency."""

    name: str = Field(..., description="Dependency name")
    required: bool = Field(..., description="Whether this is a required dependency")
    available: bool = Field(..., description="Whether the dependency is available")
    message: str | None = Field(None, description="Status message or error")


class ReadinessStatus(BaseModel):
    """Readiness status response."""

    ready: bool = Field(..., description="Whether the service is ready to accept traffic")
    timestamp: datetime = Field(..., description="UTC timestamp of the readiness check")
    dependencies: list[DependencyStatus] = Field(
        default_factory=list, description="Required dependencies status"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "ready": True,
                "timestamp": "2026-02-08T10:30:00Z",
                "dependencies": [
                    {
                        "name": "telemetry_path",
                        "required": True,
                        "available": True,
                        "message": "Telemetry path exists and is readable"
                    },
                    {
                        "name": "cache_path",
                        "required": False,
                        "available": True,
                        "message": "Cache path exists and is writable"
                    }
                ]
            }
        }
    }


class TelemetryStats(BaseModel):
    """Telemetry data statistics."""

    total_sessions: int = Field(..., description="Total number of discovered sessions")
    total_files: int = Field(..., description="Total number of telemetry files")
    total_laps: int = Field(..., description="Total number of laps across all sessions")
    cached_layouts: int = Field(..., description="Number of cached track layouts")
    cache_size_mb: float = Field(..., description="Cache directory size in MB")


class TelemetryMetrics(BaseModel):
    """Telemetry metrics response."""

    timestamp: datetime = Field(..., description="UTC timestamp of metrics collection")
    stats: TelemetryStats = Field(..., description="Telemetry statistics")

    model_config = {
        "json_schema_extra": {
            "example": {
                "timestamp": "2026-02-08T10:30:00Z",
                "stats": {
                    "total_sessions": 5,
                    "total_files": 5,
                    "total_laps": 47,
                    "cached_layouts": 2,
                    "cache_size_mb": 1.25
                }
            }
        }
    }
