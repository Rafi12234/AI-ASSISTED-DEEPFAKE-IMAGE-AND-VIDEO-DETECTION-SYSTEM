from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import ai_settings
from app.pipeline.model_registry import (
    get_active_model_names,
    get_model_registry_payload,
)
from app.pipeline.orchestrator import analyze_media_bytes


app = FastAPI(
    title=ai_settings.service_name,
    version=ai_settings.service_version,
    description="Production-oriented AI pipeline for image/video deepfake analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": ai_settings.service_name,
        "status": "running",
        "version": ai_settings.service_version,
        "mode": "production-pipeline-foundation",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-worker",
        "engine": "production-pipeline-v0.31.0",
        "version": ai_settings.service_version,
        "supported_media": ["image", "video"],
        "active_models": get_active_model_names(),
        "gpu_enabled": ai_settings.enable_gpu,
        "device": ai_settings.default_device,
    }


@app.get("/models")
async def list_models():
    return {
        "active_models": get_active_model_names(),
        "registered_models": get_model_registry_payload(),
    }


@app.post("/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only image files are supported in this endpoint.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return analyze_media_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-image",
            mime_type=file.content_type,
            forced_media_type="image",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image analysis failed: {exc}",
        ) from exc


@app.post("/analyze/video")
async def analyze_video(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("video/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only video files are supported in this endpoint.",
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return analyze_media_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-video",
            mime_type=file.content_type,
            forced_media_type="video",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video analysis failed: {exc}",
        ) from exc


@app.post("/analyze/media")
async def analyze_media(file: UploadFile = File(...)):
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return analyze_media_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-media",
            mime_type=file.content_type or "application/octet-stream",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Media analysis failed: {exc}",
        ) from exc