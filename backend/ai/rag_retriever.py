"""
RAG retrieval: find the most semantically similar past chat messages.
Uses cosine similarity over stored numpy embeddings (no external vector DB needed).
"""

import numpy as np
from backend.ai.embeddings import embed, cosine_similarity
from backend.db.repo_embeddings import get_all_embeddings
from backend.db.repo_chat import get_history
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)


async def retrieve_similar_context(query: str, top_k: int | None = None) -> list[dict]:
    """
    Returns top_k most similar past assistant messages as context.
    Each result: {"role": ..., "content": ..., "similarity": float}
    """
    k = top_k or settings.rag_top_k
    query_emb = embed(query)
    if query_emb is None:
        return []

    stored = await get_all_embeddings()
    if not stored:
        return []

    scores: list[tuple[float, str]] = []
    for msg_id, emb in stored:
        sim = cosine_similarity(query_emb, emb)
        scores.append((sim, msg_id))

    scores.sort(reverse=True)
    top_ids = [msg_id for _, msg_id in scores[:k]]

    # Fetch the actual messages
    # We do a simple approach: get all messages and filter
    # (scale: university project, hundreds of messages max)
    async with __import__("aiosqlite").connect(__import__("backend.config", fromlist=["settings"]).settings.db_path) as db:
        db.row_factory = __import__("aiosqlite").Row
        placeholders = ",".join("?" * len(top_ids))
        async with db.execute(
            f"SELECT id, role, content FROM chat_messages WHERE id IN ({placeholders})",
            top_ids,
        ) as cursor:
            rows = await cursor.fetchall()

    msg_map = {row["id"]: dict(row) for row in rows}
    results = []
    for sim, msg_id in scores[:k]:
        if msg_id in msg_map:
            msg = msg_map[msg_id]
            msg["similarity"] = round(sim, 4)
            results.append(msg)
    return results
