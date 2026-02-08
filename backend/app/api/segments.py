"""API routes for track segmentation and derived metrics (Step 3)."""

from fastapi import APIRouter, HTTPException, Query

from app.core.segments import SegmentService
from app.models.segment import (
    LapSegmentMetrics,
    SegmentComparisonRequest,
    SegmentComparisonResponse,
    TrackLayout,
)

router = APIRouter(prefix="/api/v1/segments", tags=["segments"])

# Singleton instance
segment_service = SegmentService()


@router.get("/sessions/{session_id}/layout", response_model=TrackLayout)
async def get_track_layout(
    session_id: str,
    force_regenerate: bool = Query(False, description="Force new layout detection"),
) -> TrackLayout:
    """Get track layout with segment definitions for a session."""
    try:
        layout = segment_service.get_or_create_layout(
            session_id=session_id,
            force_regenerate=force_regenerate,
        )
        return layout
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting track layout: {e}",
        ) from e


@router.post("/sessions/{session_id}/layout/regenerate", response_model=TrackLayout)
async def regenerate_layout(
    session_id: str,
    reference_lap: int | None = Query(None, description="Override reference lap number"),
) -> TrackLayout:
    """Regenerate track layout with optional reference lap override."""
    try:
        layout = segment_service.get_or_create_layout(
            session_id=session_id,
            preferred_lap=reference_lap,
            force_regenerate=True,
        )
        return layout
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error regenerating layout: {e}",
        ) from e


@router.get("/sessions/{session_id}/laps/{lap_number}/segments", response_model=LapSegmentMetrics)
async def get_lap_segments(
    session_id: str,
    lap_number: int,
    force_recompute: bool = Query(False, description="Force recalculation of metrics"),
) -> LapSegmentMetrics:
    """Get segment metrics for a specific lap."""
    try:
        metrics = segment_service.get_lap_metrics(
            session_id=session_id,
            lap_number=lap_number,
            force_recompute=force_recompute,
        )
        return metrics
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating lap metrics: {e}",
        ) from e


@router.post("/sessions/{session_id}/compare", response_model=SegmentComparisonResponse)
async def compare_lap_segments(
    session_id: str,
    request: SegmentComparisonRequest,
) -> SegmentComparisonResponse:
    """Compare segment metrics between two laps."""
    try:
        comparison = segment_service.compare_laps(
            session_id=session_id,
            request=request,
        )
        return comparison
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error comparing laps: {e}",
        ) from e
