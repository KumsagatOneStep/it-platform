from fastapi import FastAPI

from app.core.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="IT-платформа",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.include_router(health_router)
    return app


app = create_app()
