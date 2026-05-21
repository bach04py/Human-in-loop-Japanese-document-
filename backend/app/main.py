from fastapi import FastAPI

from app.api.routes import router
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Base API for the Human-in-the-Loop Multi-Agent Japanese "
            "Document Processing System."
        ),
    )
    app.include_router(router, prefix=settings.api_prefix)
    return app


app = create_app()
