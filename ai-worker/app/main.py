from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware

from app.config import ai_settings
from app.datasets.catalog import get_recommended_datasets
from app.datasets.local_registry import (
    initialize_recommended_registry,
    list_local_dataset_registry,
    register_local_dataset,
    validate_local_dataset,
)
from app.datasets.template_builder import (
    create_custom_dataset_template,
)
from app.faces.face_cropper import (
    crop_uploaded_image,
    export_dataset_face_crops,
    get_face_crop_export_summary,
    list_face_crop_exports,
)
from app.faces.face_detector import (
    DETECTOR_NAME,
    DETECTOR_VERSION,
    detect_faces_from_image_bytes,
)
from app.pipeline.model_registry import (
    get_active_model_names,
    get_model_registry_payload,
)
from app.pipeline.orchestrator import analyze_media_bytes
from app.schemas.datasets import (
    DatasetValidationRequest,
    LocalDatasetRegistrationRequest,
)
from app.schemas.faces import DatasetFaceCropExportRequest


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title=ai_settings.service_name,
    version=ai_settings.service_version,
    description=(
        "Production-oriented AI pipeline for image, video, "
        "face detection, and deepfake analysis."
    ),
)


# ============================================================
# CORS configuration
# ============================================================

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


# ============================================================
# Root and health endpoints
# ============================================================

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
        "engine": "production-pipeline-v0.39.0",
        "version": ai_settings.service_version,
        "supported_media": [
            "image",
            "video",
        ],
        "active_models": get_active_model_names(),
        "gpu_enabled": ai_settings.enable_gpu,
        "device": ai_settings.default_device,
        "face_detector": DETECTOR_NAME,
        "face_detector_version": DETECTOR_VERSION,
    }


# ============================================================
# Model endpoints
# ============================================================

@app.get("/models")
async def list_models():
    return {
        "active_models": get_active_model_names(),
        "registered_models": get_model_registry_payload(),
    }


# ============================================================
# Dataset endpoints
# ============================================================

@app.get("/datasets/recommended")
async def list_recommended_datasets():
    return {
        "message": (
            "Recommended real-world and benchmark datasets "
            "for production deepfake training."
        ),
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
async def register_dataset(
    request: LocalDatasetRegistrationRequest,
):
    try:
        dataset = register_local_dataset(request)

        return {
            "message": "Dataset registered successfully.",
            "dataset": dataset,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset registration failed: {exc}",
        ) from exc


@app.post("/datasets/validate")
async def validate_dataset(
    request: DatasetValidationRequest,
):
    try:
        validation = validate_local_dataset(request)

        return {
            "message": "Dataset validation completed.",
            "validation": validation,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset validation failed: {exc}",
        ) from exc


@app.post("/datasets/custom-template")
async def create_custom_template():
    try:
        paths = create_custom_dataset_template()

        return {
            "message": (
                "Custom real-life dataset template "
                "created successfully."
            ),
            "paths": paths,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Custom dataset template creation failed: {exc}",
        ) from exc


# ============================================================
# Face detection endpoints
# ============================================================

@app.get("/faces/health")
async def face_detection_health():
    return {
        "status": "ok",
        "detector": DETECTOR_NAME,
        "detector_version": DETECTOR_VERSION,
        "supported_media": ["image"],
        "features": [
            "face_detection",
            "single_image_face_crop",
            "dataset_face_crop_export",
        ],
    }


@app.post("/faces/detect/image")
async def detect_faces_image(
    file: UploadFile = File(...),
):
    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only image files are supported "
                "in this endpoint."
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return detect_faces_from_image_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-image",
            mime_type=file.content_type,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face detection failed: {exc}",
        ) from exc


# ============================================================
# Face crop endpoints
# ============================================================

@app.post("/faces/crop/image")
async def crop_faces_image(
    file: UploadFile = File(...),
    padding_ratio: float = 0.25,
    min_quality_score: float = 0.0,
):
    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only image files are supported "
                "in this endpoint."
            ),
        )

    if padding_ratio < 0 or padding_ratio > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "padding_ratio must be between 0 and 2."
            ),
        )

    if (
        min_quality_score < 0
        or min_quality_score > 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "min_quality_score must be between 0 and 1."
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    try:
        return crop_uploaded_image(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-image",
            mime_type=file.content_type,
            padding_ratio=padding_ratio,
            min_quality_score=min_quality_score,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Face crop failed: {exc}",
        ) from exc


@app.post("/faces/export-dataset-crops")
async def export_faces_from_dataset(
    request: DatasetFaceCropExportRequest,
):
    if request.padding_ratio < 0 or request.padding_ratio > 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="padding_ratio must be between 0 and 2.",
        )

    if (
        request.min_quality_score < 0
        or request.min_quality_score > 1
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "min_quality_score must be between 0 and 1."
            ),
        )

    if request.max_files is not None and request.max_files < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="max_files must be at least 1 or null.",
        )

    try:
        summary = export_dataset_face_crops(request)

        return {
            "message": "Dataset face crop export completed.",
            "export": summary,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Dataset face crop export failed: {exc}",
        ) from exc


@app.get("/faces/dataset-crop-exports")
async def get_dataset_crop_exports():
    try:
        return {
            "crop_export_root": str(
                ai_settings.dataset_root
                / "processed"
                / "face_crops"
            ),
            "exports": list_face_crop_exports(),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not list face crop exports: {exc}",
        ) from exc


@app.get("/faces/dataset-crop-exports/{output_name}")
async def get_dataset_crop_export(
    output_name: str,
):
    if not output_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="output_name is required.",
        )

    try:
        summary = get_face_crop_export_summary(
            output_name.strip()
        )

        return {
            "export": summary,
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not read face crop export: {exc}",
        ) from exc


# ============================================================
# General analysis endpoints
# ============================================================

@app.post("/analyze/image")
async def analyze_image(
    file: UploadFile = File(...),
):
    if (
        not file.content_type
        or not file.content_type.startswith("image/")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only image files are supported "
                "in this endpoint."
            ),
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

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Image analysis failed: {exc}",
        ) from exc


@app.post("/analyze/video")
async def analyze_video(
    file: UploadFile = File(...),
):
    if (
        not file.content_type
        or not file.content_type.startswith("video/")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only video files are supported "
                "in this endpoint."
            ),
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

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Video analysis failed: {exc}",
        ) from exc


@app.post("/analyze/media")
async def analyze_media(
    file: UploadFile = File(...),
):
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
            mime_type=(
                file.content_type
                or "application/octet-stream"
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media analysis failed: {exc}",
        ) from exc