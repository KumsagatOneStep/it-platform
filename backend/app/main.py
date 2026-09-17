from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.errors import register_error_handlers
from app.core.health import router as health_router
from app.core.logging import configure_logging
from app.core.middleware import RequestIdMiddleware
from app.modules.directories.router import routers as directories_routers
from app.modules.users_auth.router import admin_users_router, auth_router, users_router
from app.wiring import register_event_handlers


def create_app() -> FastAPI:
    register_event_handlers()
    settings = get_settings()
    if settings.app_env != "test":
        configure_logging()
    app = FastAPI(
        title="IT-платформа",
        version="0.1.0",
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(RequestIdMiddleware)
    if settings.cors_origins:
        # Только local: в staging/production Settings запрещает CORS_ORIGINS (п. 7.3)
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    register_error_handlers(app)
    app.include_router(health_router)
    app.include_router(auth_router, prefix="/api")
    app.include_router(admin_users_router, prefix="/api")
    app.include_router(users_router, prefix="/api")
    for router in directories_routers:
        app.include_router(router, prefix="/api")
    return app


app = create_app()
