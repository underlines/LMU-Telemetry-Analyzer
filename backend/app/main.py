"""Main FastAPI application."""

from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, segments, sessions, signals

# API Metadata
API_TITLE = "LMU Telemetry Analyzer"
API_DESCRIPTION = """
Local-first telemetry analysis tool for Le Mans Ultimate racing game.

## Features

- **Session Discovery**: Browse and search telemetry recordings
- **Signal Visualization**: Interactive plots with lap overlay and time/distance alignment
- **Track Segmentation**: Automatic corner/straight detection with per-segment metrics
- **Lap Comparison**: Compare laps with time deltas and technique analysis

## Data Flow

1. Telemetry files (`.duckdb`) are discovered from configured directory
2. Track layouts are auto-detected and cached (Tier 1)
3. Lap metrics are computed on-demand and cached (Tier 2)
4. All source data is read-only; derived data is cached separately

## Health & Monitoring

- `GET /health` - Liveness probe with service health checks
- `GET /ready` - Readiness probe with dependency status
- `GET /metrics` - Telemetry statistics and cache info
"""
API_VERSION = "0.1.0"

# OpenAPI Tags Metadata
tags_metadata: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": "Health checks and monitoring endpoints for service status",
    },
    {
        "name": "sessions",
        "description": "Session and lap discovery operations",
        "externalDocs": {
            "description": "Session data structure",
            "url": "https://github.com/anomalyco/lmu_telemetry",
        },
    },
    {
        "name": "signals",
        "description": "Signal retrieval and lap comparison",
    },
    {
        "name": "segments",
        "description": "Track segmentation, layout detection, and derived metrics",
    },
]

app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Common dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(signals.router)
app.include_router(segments.router)


@app.get("/", tags=["root"])
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "message": "LMU Telemetry Analyzer API",
        "version": API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
