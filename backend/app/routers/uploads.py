import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.dependencies import get_current_user, get_db
from app.models.core import AnalysisJob, MediaUpload, User
from app.schemas.upload import UploadDetailResponse, UploadListResponse, UploadResponse
from app.services.queue import enqueue_analysis_job
from app.services.storage import delete_object, upload_bytes
from app.validators.file_validator import validate_upload_file


router = APIRouter(prefix="/uploads", tags=["Uploads"])
settings = get_settings()


def build_object_name(*, safe_filename: str, file_type: str) -> str:
    extension = Path(safe_filename).suffix.lower()
    file_uuid = uuid.uuid4()

    return f"{file_type}s/{file_uuid}{extension}"


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    validated_file = await validate_upload_file(file)

    object_name = build_object_name(
        safe_filename=validated_file.safe_filename,
        file_type=validated_file.file_type,
    )

    try:
        upload_bytes(
            bucket_name=settings.minio_bucket_raw,
            object_name=object_name,
            data=validated_file.content,
            content_type=validated_file.mime_type,
        )

        media_upload = MediaUpload(
            user_id=current_user.id,
            original_filename=validated_file.original_filename,
            stored_path=object_name,
            file_type=validated_file.file_type,
            mime_type=validated_file.mime_type,
            file_size_bytes=validated_file.file_size_bytes,
            upload_status="stored",
            is_deleted=False,
        )

        db.add(media_upload)
        await db.flush()

        analysis_job = AnalysisJob(
            media_upload_id=media_upload.id,
            status="queued",
            job_metadata={
                "source": "user_upload",
                "file_type": validated_file.file_type,
                "mime_type": validated_file.mime_type,
            },
        )

        db.add(analysis_job)
        await db.commit()

        await db.refresh(media_upload)
        await db.refresh(analysis_job)

        await enqueue_analysis_job(
            job_id=analysis_job.id,
            upload_id=media_upload.id,
            user_id=current_user.id,
            file_type=media_upload.file_type,
            stored_path=media_upload.stored_path,
            mime_type=media_upload.mime_type,
        )

        return UploadResponse(
            upload_id=media_upload.id,
            job_id=analysis_job.id,
            original_filename=media_upload.original_filename,
            file_type=media_upload.file_type,
            mime_type=media_upload.mime_type,
            file_size_bytes=media_upload.file_size_bytes,
            upload_status=media_upload.upload_status,
            analysis_status=analysis_job.status,
        )

    except Exception as exc:
        await db.rollback()

        try:
            delete_object(
                bucket_name=settings.minio_bucket_raw,
                object_name=object_name,
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed. Please try again.",
        ) from exc


@router.get("", response_model=UploadListResponse)
async def list_my_uploads(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MediaUpload)
        .where(
            MediaUpload.user_id == current_user.id,
            MediaUpload.is_deleted.is_(False),
        )
        .order_by(desc(MediaUpload.created_at))
    )

    uploads = result.scalars().all()

    return UploadListResponse(
        uploads=[
            UploadDetailResponse.model_validate(upload)
            for upload in uploads
        ]
    )


@router.get("/{upload_id}", response_model=UploadDetailResponse)
async def get_upload(
    upload_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MediaUpload).where(
            MediaUpload.id == upload_id,
            MediaUpload.user_id == current_user.id,
            MediaUpload.is_deleted.is_(False),
        )
    )

    upload = result.scalar_one_or_none()

    if upload is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found.",
        )

    return UploadDetailResponse.model_validate(upload)

