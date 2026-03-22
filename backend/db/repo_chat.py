import uuid
from backend.db.database import get_db


async def save_message(session_id: str, role: str, content: str) -> str:
    mid = str(uuid.uuid4())
    async with get_db() as db:
        await db.execute(
            "INSERT INTO chat_messages (id, session_id, role, content) VALUES (?, ?, ?, ?)",
            (mid, session_id, role, content),
        )
        await db.commit()
    return mid


async def get_history(session_id: str) -> list[dict]:
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
