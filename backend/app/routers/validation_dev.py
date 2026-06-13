from fastapi import APIRouter, File, UploadFile

from app.validators.file_validator import validate_upload_file


router = APIRouter(prefix="/dev/validation", tags=["Dev Validation"])


@router.post("/file")
async def validate_file(file: UploadFile = File(...)):
    validated_file = await validate_upload_file(file)

    return {
        "status": "valid",
        "original_filename": validated_file.original_filename,
        "safe_filename": validated_file.safe_filename,
        "file_type": validated_file.file_type,
        "mime_type": validated_file.mime_type,
        "file_size_bytes": validated_file.file_size_bytes,
        "file_size_mb": round(validated_file.file_size_bytes / (1024 * 1024), 4),
    }