import json
import uuid
from datetime import datetime
from backend.db.database import get_db


async def create_session(name: str, filename: str, xml_hash: str, summary: dict) -> str:
    sid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            """INSERT INTO analysis_sessions (id, name, filename, xml_hash, summary)
               VALUES (?, ?, ?, ?, ?)""",
            (sid, name, filename, xml_hash, json.dumps(summary)),
        )
        await db.commit()
    return sid


async def get_session_by_hash(xml_hash: str) -> dict | None:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM analysis_sessions WHERE xml_hash = ? ORDER BY created_at DESC LIMIT 1",
            (xml_hash,),
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def get_session(session_id: str) -> dict | None:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM analysis_sessions WHERE id = ?", (session_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_sessions(limit: int = 50) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM analysis_sessions ORDER BY created_at DESC LIMIT ?", (limit,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]


async def delete_session(session_id: str) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            "DELETE FROM analysis_sessions WHERE id = ?", (session_id,)
        )
        await db.commit()
        return cursor.rowcount > 0
