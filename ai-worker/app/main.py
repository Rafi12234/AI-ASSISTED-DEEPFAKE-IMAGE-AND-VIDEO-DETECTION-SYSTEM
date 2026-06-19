from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware

from app.services.image_analyzer import analyze_image_bytes


app = FastAPI(
    title="Deepfake Detection AI Service",
    version="0.1.0",
    description="Local AI service foundation for image/video analysis.",
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
        "service": "Deepfake Detection AI Service",
        "status": "running",
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "ai-worker",
        "engine": "ai-service-foundation-v1",
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
        return analyze_image_bytes(
            file_bytes=file_bytes,
            filename=file.filename or "uploaded-image",
            mime_type=file.content_type,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image analysis failed: {exc}",
        ) from exc