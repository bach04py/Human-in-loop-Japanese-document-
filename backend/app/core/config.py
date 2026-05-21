import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv(
        "APP_NAME", "HITL Japanese Document Processing API"
    )
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    api_prefix: str = os.getenv("API_PREFIX", "/api/v1")
    environment: str = os.getenv("ENVIRONMENT", "development")
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/hitl"
    )
    upload_dir: Path = Path(os.getenv("UPLOAD_DIR", "/app/data/uploads"))
    max_upload_mb: int = int(os.getenv("MAX_UPLOAD_MB", "25"))


settings = Settings()
