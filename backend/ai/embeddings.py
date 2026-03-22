"""
Local sentence embeddings using sentence-transformers (all-MiniLM-L6-v2).
Model is ~80MB, downloaded once on first use.
"""

import numpy as np
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.embedding_model}")
            _model = SentenceTransformer(settings.embedding_model)
            logger.info("Embedding model loaded.")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. RAG retrieval will be disabled. "
                "Install with: pip install sentence-transformers"
            )
    return _model


def embed(text: str) -> np.ndarray | None:
    model = _get_model()
    if model is None:
        return None
    return model.encode(text, convert_to_numpy=True).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)
