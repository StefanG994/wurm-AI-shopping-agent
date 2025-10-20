# graphiti/config.py
from __future__ import annotations
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # ---------- Neo4j / Graph DB ----------
    NEO4J_URI: str = Field(default="bolt://localhost:7687")
    NEO4J_USER: str = Field(default="neo4j")
    NEO4J_PASSWORD: str = Field(default="password")

    # ---------- LLM backends (OpenAI default) ----------
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL_LARGE: str = "gpt-5"
    OPENAI_MODEL_SMALL: str = "gpt-5-nano"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Concurrency / telemetry for Graphiti
    GRAPHITI_SEMAPHORE_LIMIT: int = 10
    GRAPHITI_TELEMETRY_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
