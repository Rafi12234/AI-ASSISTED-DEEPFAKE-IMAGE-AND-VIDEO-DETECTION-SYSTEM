from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.config import ai_settings
from app.datasets.catalog import get_recommended_datasets
from app.datasets.local_registry import (
    initialize_recommended_registry,
    list_local_dataset_registry,
    register_local_dataset,
    validate_local_dataset,
)
from app.datasets.template_builder import create_custom_dataset_template
from app.datasets.manifest_builder import (
    build_manifest,
    list_manifests,
    read_manifest_preview,
)
from app.pipeline.model_registry import (
    get_active_model_names,
    get_model_registry_payload,
)
from app.pipeline.orchestrator import analyze_media_bytes
from app.schemas.datasets import (
    DatasetManifestBuildRequest,
    DatasetValidationRequest,
    LocalDatasetRegistrationRequest,
)


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


@app.get("/datasets/recommended")
async def list_recommended_datasets():
    return {
        "message": "Recommended real-world and benchmark datasets for production deepfake training.",
        "recommended_order": [
            "faceforensics_pp",
            "celeb_df_v2",
            "dfdc",
            "deeperforensics_1",
            "wilddeepfake",
            "fakeavceleb",
            "asvspoof_2021",
            "av_deepfake1m",
            "av_deepfake1m_pp",
            "custom_real_life",
        ],
        "datasets": get_recommended_datasets(),
    }


@app.get("/datasets/registry")
async def get_local_dataset_registry():
    return {
        "dataset_root": str(ai_settings.dataset_root),
        "registry": list_local_dataset_registry(),
    }


@app.post("/datasets/initialize")
async def initialize_dataset_registry():
    return {
        "message": "Dataset registry initialized successfully.",
        "dataset_root": str(ai_settings.dataset_root),
        "registry": initialize_recommended_registry(),
    }


@app.post("/datasets/register")
async def register_dataset(request: LocalDatasetRegistrationRequest):
    try:
        dataset = register_local_dataset(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "message": "Dataset registered successfully.",
        "dataset": dataset,
    }


@app.post("/datasets/validate")
async def validate_dataset(request: DatasetValidationRequest):
    return {
        "message": "Dataset validation completed.",
        "validation": validate_local_dataset(request),
    }


@app.post("/datasets/custom-template")
async def create_custom_template():
    return {
        "message": "Custom real-life dataset template created successfully.",
        "paths": create_custom_dataset_template(),
    }
@app.post("/datasets/build-manifest")
async def build_dataset_manifest(request: DatasetManifestBuildRequest):
    try:
        summary = build_manifest(request)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return {
        "message": "Dataset manifest built successfully.",
        "summary": summary,
    }


@app.get("/datasets/manifests")
async def get_dataset_manifests():
    return {
        "manifest_root": str(ai_settings.dataset_root / "manifests"),
        "manifests": list_manifests(),
    }


@app.get("/datasets/manifests/{slug}")
async def get_dataset_manifest_preview(slug: str, limit: int = 20):
    try:
        preview = read_manifest_preview(
            slug=slug,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return preview


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