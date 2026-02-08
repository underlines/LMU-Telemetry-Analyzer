"""API routes for signal retrieval and lap comparison."""

from fastapi import APIRouter, HTTPException, Query

from app.core.signals import SignalService
from app.models.signal import (
    ComparisonResponse,
    LapComparisonRequest,
    SignalList,
    SignalSlice,
)

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])

# Singleton instance
signal_service = SignalService()


@router.get("/sessions/{session_id}", response_model=SignalList)
async def list_signals(session_id: str) -> SignalList:
    """List all available signals/channels for a session."""
    try:
        signals = signal_service.get_available_signals(session_id)
        return SignalList(
            session_id=session_id,
            signals=signals,
            total=len(signals),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing signals: {e}",
        ) from e


@router.get("/sessions/{session_id}/laps/{lap_number}", response_model=list[SignalSlice])
async def get_lap_signals(
    session_id: str,
    lap_number: int,
    channels: list[str] = Query(..., description="Channel names to retrieve"),
    normalize_time: bool = Query(True, description="Normalize time to lap start"),
    use_distance: bool = Query(False, description="Use distance for X-axis"),
    max_points: int | None = Query(None, ge=1, description="Maximum points (downsampling)"),
) -> list[SignalSlice]:
    """Get signal data for specific channels within a lap."""
    try:
        slices = signal_service.get_lap_signals(
            session_id=session_id,
            lap_number=lap_number,
            channels=channels,
            normalize_time=normalize_time,
            use_distance=use_distance,
            max_points=max_points,
        )
        return slices
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving signals: {e}",
        ) from e


@router.post("/sessions/{session_id}/compare", response_model=ComparisonResponse)
async def compare_laps(
    session_id: str,
    request: LapComparisonRequest,
) -> ComparisonResponse:
    """Compare signals between two laps."""
    try:
        comparisons = signal_service.compare_laps(
            session_id=session_id,
            request=request,
        )
        return ComparisonResponse(
            session_id=session_id,
            target_lap=request.target_lap,
            reference_lap=request.reference_lap,
            comparisons=comparisons,
        )
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
