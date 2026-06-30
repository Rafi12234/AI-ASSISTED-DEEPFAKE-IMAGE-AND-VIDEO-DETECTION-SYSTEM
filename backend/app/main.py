from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import admin, ai_models, auth, dashboard, face_crops, health, queue_dev, reports, results, storage_dev, system, uploads, validation_dev
settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="AI-assisted deepfake image and video detection backend.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Deepfake Detection API is running",
        "docs": "/docs",
        "health": "/api/health",
    }
app.include_router(
    health.router,
    prefix="/api",
    tags=["Health"],
)
app.include_router(
    auth.router,
    prefix="/api",
)
app.include_router(
    storage_dev.router,
    prefix="/api",
)
app.include_router(
    validation_dev.router,
    prefix="/api",
)
app.include_router(
    uploads.router,
    prefix="/api",
)
app.include_router(
    queue_dev.router,
    prefix="/api",
)
app.include_router(
    results.router,
    prefix="/api",
)
app.include_router(
    admin.router,
    prefix="/api",
)
app.include_router(
    admin.router,
    prefix="/api",
)

app.include_router(
    reports.router,
    prefix="/api",
)
app.include_router(
    system.router,
    prefix="/api",
)
app.include_router(
    dashboard.router,
    prefix="/api",
)
app.include_router(
    ai_models.router,
    prefix="/api",
)
app.include_router(
    face_crops.router,
    prefix="/api",
)