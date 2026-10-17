from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import get_settings
from routes import screening, health_score, ml_inference, pdf_export, history, devices, third_party, webhooks, cron
from db.connection import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(screening.router, prefix="/api/v1", tags=["screening"])
    app.include_router(health_score.router, prefix="/api/v1", tags=["health-score"])
    app.include_router(ml_inference.router, prefix="/api/v1", tags=["ml"])
    app.include_router(pdf_export.router, prefix="/api/v1", tags=["export"])
    app.include_router(history.router, prefix="/api/v1", tags=["history"])
    app.include_router(devices.router, prefix="/api/v1", tags=["devices"])
    app.include_router(third_party.router, prefix="/api/v1", tags=["third-party"])
    app.include_router(webhooks.router, prefix="/api/v1", tags=["webhooks"])
    app.include_router(cron.router, prefix="/api/v1", tags=["cron"])

    # Health check
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "version": settings.VERSION}

    # Global exception handler
    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": type(exc).__name__},
        )

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)