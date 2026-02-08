"""API routes for health checks and monitoring."""

import logging
import time
from datetime import UTC, datetime

import duckdb
from fastapi import APIRouter, HTTPException

from app.core.config import get_cache_dir, get_telemetry_path
from app.core.telemetry import telemetry_manager
from app.models.health import (
    DependencyStatus,
    HealthStatus,
    ReadinessStatus,
    ServiceCheck,
    TelemetryMetrics,
    TelemetryStats,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Version constant - should match app version
API_VERSION = "0.1.0"


async def _check_duckdb_connectivity() -> ServiceCheck:
    """Check if DuckDB is functional."""
    start_time = time.perf_counter()
    try:
        # Try to create an in-memory database to verify DuckDB works
        conn = duckdb.connect(database=":memory:")
        conn.execute("SELECT 1")
        conn.close()
        response_time = (time.perf_counter() - start_time) * 1000
        return ServiceCheck(
            name="duckdb",
            status="healthy",
            response_time_ms=round(response_time, 2),
            message="DuckDB connectivity OK",
        )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        return ServiceCheck(
            name="duckdb",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"DuckDB error: {e}",
        )


async def _check_cache_directory() -> ServiceCheck:
    """Check if cache directory is accessible."""
    start_time = time.perf_counter()
    try:
        cache_path = get_cache_dir()
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = cache_path / ".health_check"
        test_file.write_text("ok")
        test_file.unlink()

        response_time = (time.perf_counter() - start_time) * 1000
        return ServiceCheck(
            name="cache_directory",
            status="healthy",
            response_time_ms=round(response_time, 2),
            message="Cache directory accessible",
        )
    except Exception as e:
        response_time = (time.perf_counter() - start_time) * 1000
        return ServiceCheck(
            name="cache_directory",
            status="unhealthy",
            response_time_ms=round(response_time, 2),
            message=f"Cache directory error: {e}",
        )


@router.get("/health", response_model=HealthStatus)
async def health_check() -> HealthStatus:
    """Health check endpoint for liveness probing.

    Performs basic checks to verify the service is running:
    - DuckDB connectivity
    - Cache directory accessibility

    Returns:
        HealthStatus with overall status and individual checks
    """
    checks = await _perform_health_checks()

    # Determine overall status
    unhealthy_count = sum(1 for c in checks if c.status == "unhealthy")
    degraded_count = sum(1 for c in checks if c.status == "degraded")

    if unhealthy_count > 0:
        status = "unhealthy"
    elif degraded_count > 0:
        status = "degraded"
    else:
        status = "healthy"

    return HealthStatus(
        status=status,
        timestamp=datetime.now(UTC),
        version=API_VERSION,
        checks=checks,
    )


async def _perform_health_checks() -> list[ServiceCheck]:
    """Run all health checks."""
    return [
        await _check_duckdb_connectivity(),
        await _check_cache_directory(),
    ]


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check() -> ReadinessStatus:
    """Readiness check endpoint for readiness probing.

    Checks if the service is ready to accept traffic by verifying:
    - Telemetry directory exists and is readable
    - Cache directory exists and is writable (optional)

    Returns:
        ReadinessStatus indicating if service is ready
    """
    dependencies = await _check_dependencies()

    # Service is ready if all required dependencies are available
    ready = all(
        dep.available or not dep.required for dep in dependencies
    )

    return ReadinessStatus(
        ready=ready,
        timestamp=datetime.now(UTC),
        dependencies=dependencies,
    )


async def _check_dependencies() -> list[DependencyStatus]:
    """Check all dependencies."""
    dependencies: list[DependencyStatus] = []

    # Check telemetry path (required)
    try:
        telemetry_path = get_telemetry_path()
        if telemetry_path.exists() and telemetry_path.is_dir():
            # Check if readable by listing contents
            list(telemetry_path.iterdir())
            dependencies.append(
                DependencyStatus(
                    name="telemetry_path",
                    required=True,
                    available=True,
                    message="Telemetry path exists and is readable",
                )
            )
        else:
            dependencies.append(
                DependencyStatus(
                    name="telemetry_path",
                    required=True,
                    available=False,
                    message=f"Telemetry path does not exist: {telemetry_path}",
                )
            )
    except Exception as e:
        dependencies.append(
            DependencyStatus(
                name="telemetry_path",
                required=True,
                available=False,
                message=f"Error accessing telemetry path: {e}",
            )
        )

    # Check cache path (optional)
    try:
        cache_path = get_cache_dir()
        if not cache_path.exists():
            cache_path.mkdir(parents=True, exist_ok=True)

        # Test write access
        test_file = cache_path / ".ready_check"
        test_file.write_text("ok")
        test_file.unlink()

        dependencies.append(
            DependencyStatus(
                name="cache_path",
                required=False,
                available=True,
                message="Cache path exists and is writable",
            )
        )
    except Exception as e:
        dependencies.append(
            DependencyStatus(
                name="cache_path",
                required=False,
                available=False,
                message=f"Cache path error: {e}",
            )
        )

    return dependencies


@router.get("/metrics", response_model=TelemetryMetrics)
async def telemetry_metrics() -> TelemetryMetrics:
    """Telemetry metrics endpoint.

    Returns statistics about telemetry data including:
    - Total sessions and files discovered
    - Total laps across all sessions
    - Cache statistics (layouts, size)

    Returns:
        TelemetryMetrics with current statistics
    """
    try:
        stats = await _collect_telemetry_stats()
        return TelemetryMetrics(
timestamp=datetime.now(UTC),
            stats=stats,
        )
    except Exception as e:
        logger.error(f"Error collecting telemetry metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to collect metrics: {e}",
        ) from e


async def _collect_telemetry_stats() -> TelemetryStats:
    """Collect telemetry statistics."""
    # Get session information
    sessions = telemetry_manager.list_sessions()
    total_laps = 0

    for session in sessions:
        laps = telemetry_manager.get_session_laps(session.id)
        if laps:
            total_laps += len(laps)

    # Count cached layouts
    cache_path = get_cache_dir()
    cached_layouts = 0
    if cache_path.exists():
        # Look for track layout files (track_name_v{version}.parquet)
        cached_layouts = len(list(cache_path.glob("*_v*.parquet")))

    # Calculate cache size
    cache_size_mb = 0.0
    if cache_path.exists():
        try:
            total_size = sum(
                f.stat().st_size for f in cache_path.rglob("*") if f.is_file()
            )
            cache_size_mb = round(total_size / (1024 * 1024), 2)
        except Exception:
            pass

    return TelemetryStats(
        total_sessions=len(sessions),
        total_files=len(sessions),  # 1 file per session currently
        total_laps=total_laps,
        cached_layouts=cached_layouts,
        cache_size_mb=cache_size_mb,
    )
