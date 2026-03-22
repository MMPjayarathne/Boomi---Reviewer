from fastapi import APIRouter, HTTPException
from backend.db.repo_sessions import list_sessions, delete_session

router = APIRouter(prefix="/api", tags=["sessions"])


@router.get("/sessions")
async def list_all_sessions():
    return await list_sessions()


@router.delete("/sessions/{session_id}")
async def remove_session(session_id: str):
    deleted = await delete_session(session_id)
    if not deleted:
        raise HTTPException(404, "Session not found.")
    return {"deleted": True, "session_id": session_id}
