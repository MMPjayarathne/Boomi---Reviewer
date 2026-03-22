from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    db_path: str = str(BASE_DIR / "data" / "boomi_reviewer.db")

    # Ollama — any chat model works (phi3, llama3.2, etc.). Must match `ollama list`.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3"
    ollama_timeout: int = 120

    # Embeddings
    embedding_model: str = "all-MiniLM-L6-v2"
    rag_top_k: int = 3

    # App
    app_title: str = "Boomi Process Reviewer"
    app_version: str = "1.0.0"
    cors_origins: list[str] = ["*"]
    # Bump when parser/rules change so /api/analyze cache misses old sessions (same XML).
    analysis_cache_version: int = 3


settings = Settings()
