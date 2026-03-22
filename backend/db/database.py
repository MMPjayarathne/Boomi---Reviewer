from pathlib import Path
import aiosqlite
from backend.config import settings
from backend.utils.logger import get_logger
from contextlib import asynccontextmanager

logger = get_logger(__name__)

_SCHEMA_FILE = Path(__file__).parent / "schema.sql"


@asynccontextmanager
async def get_db():
    db = await aiosqlite.connect(settings.db_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db() -> None:
    """Create tables if they don't exist yet."""
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    schema = _SCHEMA_FILE.read_text()
    async with get_db() as db:
        await db.executescript(schema)
        await db.commit()
    logger.info(f"Database initialized at {settings.db_path}")
