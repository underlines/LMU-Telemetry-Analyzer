"""API routes for session and lap discovery."""

from fastapi import APIRouter, HTTPException

from app.core.telemetry import telemetry_manager
from app.models.session import LapList, SessionDetail, SessionList

router = APIRouter(prefix="/api/v1/sessions", tags=["sessions"])


@router.get("", response_model=SessionList)
async def list_sessions() -> SessionList:
    """List all available telemetry sessions."""
    sessions = telemetry_manager.list_sessions()
    return SessionList(
        sessions=sessions,
        total=len(sessions)
    )


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(session_id: str) -> SessionDetail:
    """Get detailed information about a specific session."""
    session = telemetry_manager.get_session_detail(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found"
        )
    return session


@router.get("/{session_id}/laps", response_model=LapList)
async def get_session_laps(session_id: str) -> LapList:
    """Get all laps for a specific session."""
    # Verify session exists
    session = telemetry_manager.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found"
        )

    # Get laps
    laps = telemetry_manager.get_session_laps(session_id)
    if laps is None:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading laps for session '{session_id}'"
        )

    return LapList(
        session_id=session_id,
        laps=laps,
        total=len(laps)
    )
