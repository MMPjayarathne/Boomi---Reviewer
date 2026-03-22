import pickle
import numpy as np
from backend.db.database import get_db


async def save_embedding(message_id: str, embedding: np.ndarray) -> None:
    blob = pickle.dumps(embedding.astype(np.float32))
    async with get_db() as db:
        await db.execute(
            "INSERT OR REPLACE INTO message_embeddings (id, embedding) VALUES (?, ?)",
            (message_id, blob),
        )
        await db.commit()


async def get_all_embeddings() -> list[tuple[str, np.ndarray]]:
    """Return list of (message_id, embedding_array)."""
    async with get_db() as db:
        async with db.execute("SELECT id, embedding FROM message_embeddings") as cursor:
            rows = await cursor.fetchall()
    return [(row["id"], pickle.loads(row["embedding"])) for row in rows]
